# app/crud.py
from sqlalchemy.orm import Session
from sqlalchemy import select, func
import random
from typing import Optional, List

from . import models, schemas


class DistributionService:
    @staticmethod
    def find_or_create_lead(db: Session, lead_data: schemas.LeadCreate) -> models.Lead:
        lead = None
        if lead_data.external_id:
            lead = db.execute(
                select(models.Lead).where(models.Lead.external_id == lead_data.external_id)).scalar_one_or_none()
        if not lead and lead_data.phone:
            lead = db.execute(select(models.Lead).where(models.Lead.phone == lead_data.phone)).scalar_one_or_none()
        if not lead and lead_data.email:
            lead = db.execute(select(models.Lead).where(models.Lead.email == lead_data.email)).scalar_one_or_none()

        if lead:
            return lead

        # create
        new_lead = models.Lead(
            external_id=lead_data.external_id,
            phone=lead_data.phone,
            email=lead_data.email,
            name=lead_data.name
        )
        db.add(new_lead)
        db.flush()  # чтобы new_lead.id появился до commit
        return new_lead

    @staticmethod
    def _get_active_count(db: Session, operator_id: int) -> int:
        q = select(func.count()).select_from(models.Contact).where(
            models.Contact.operator_id == operator_id,
            models.Contact.status.in_(["new", "in_progress"])
        )
        return db.execute(q).scalar_one() + sum(
            1 for obj in db.new
            if isinstance(obj, models.Contact) and obj.operator_id == operator_id
            and obj.status in ["new", "in_progress"]
        )

    @staticmethod
    def assign_operator(db: Session, source_id: int) -> Optional[models.Operator]:
        weights_rows = db.execute(
            select(models.OperatorSourceWeight)
            .join(models.Operator)
            .where(
                models.OperatorSourceWeight.source_id == source_id,
                models.Operator.is_active == True
            )
        ).scalars().all()

        if not weights_rows:
            return None

        op_ids = [w.operator_id for w in weights_rows]

        counts = dict(
            db.execute(
                select(models.Contact.operator_id, func.count())
                .where(
                    models.Contact.operator_id.in_(op_ids),
                    models.Contact.status.in_(["new", "in_progress"])
                )
                .group_by(models.Contact.operator_id)
            ).all()
        )

        for obj in db.new:
            if isinstance(obj, models.Contact) and obj.operator_id in op_ids:
                if obj.status in ["new", "in_progress"]:
                    counts[obj.operator_id] = counts.get(obj.operator_id, 0) + 1

        candidates = []
        weight_values = []

        for w in weights_rows:
            op = w.operator
            active_count = counts.get(op.id, 0)
            available_capacity = max(op.max_active_leads - active_count, 0)
            if available_capacity <= 0:
                continue
            effective_weight = w.weight * available_capacity
            if effective_weight <= 0:
                continue
            candidates.append(op)
            weight_values.append(effective_weight)

        if not candidates:
            return None

        selected = random.choices(candidates, weights=weight_values, k=1)[0]
        return selected

    @staticmethod
    def get_operators(db: Session, skip: int = 0, limit: int = 100) -> List[schemas.Operator]:
        ops = db.execute(select(models.Operator).offset(skip).limit(limit)).scalars().all()
        if not ops:
            return []

        operator_ids = [op.id for op in ops]

        counts = db.execute(
            select(models.Contact.operator_id, func.count())
            .where(
                models.Contact.operator_id.in_(operator_ids),
                models.Contact.status.in_(["new", "in_progress"])
            )
            .group_by(models.Contact.operator_id)
        ).all()
        active_map = dict(counts)  # {operator_id: active_count}

        result = []
        for op in ops:
            active_count = active_map.get(op.id, 0)
            op_schema = schemas.Operator.from_orm(op)
            op_schema.active_contacts = active_count
            result.append(op_schema)
        return result


# CRUD wrapper functions
def create_operator(db: Session, operator: schemas.OperatorCreate) -> models.Operator:
    db_op = models.Operator(**operator.dict())
    db.add(db_op)
    db.commit()
    db.refresh(db_op)
    return db_op


def get_operators(db: Session, skip: int = 0, limit: int = 100):
    rows = db.execute(select(models.Operator).offset(skip).limit(limit)).scalars().all()
    result = []
    for op in rows:
        active_count = DistributionService._get_active_count(db, op.id)
        op_schema = schemas.Operator.from_orm(op)
        op_schema.active_contacts = active_count
        result.append(op_schema)
    return result


def create_source(db: Session, source: schemas.SourceCreate) -> models.Source:
    db_src = models.Source(**source.dict())
    db.add(db_src)
    db.commit()
    db.refresh(db_src)
    return db_src


def get_sources(db: Session, skip: int = 0, limit: int = 100):
    return db.execute(select(models.Source).offset(skip).limit(limit)).scalars().all()


def create_operator_source_weight(db: Session, w: schemas.OperatorSourceWeightCreate) -> models.OperatorSourceWeight:
    db_w = models.OperatorSourceWeight(**w.dict())
    db.add(db_w)
    db.commit()
    db.refresh(db_w)
    return db_w


def get_operator_source_weights(db: Session, skip: int = 0, limit: int = 100):
    return db.execute(select(models.OperatorSourceWeight).offset(skip).limit(limit)).scalars().all()


def create_contact(db: Session, contact_in: schemas.ContactCreate) -> models.Contact:
    lead_data = schemas.LeadCreate(
        external_id=contact_in.external_id,
        phone=contact_in.phone,
        email=contact_in.email,
        name=contact_in.name
    )
    lead = DistributionService.find_or_create_lead(db, lead_data)
    operator = DistributionService.assign_operator(db, contact_in.source_id)

    db_contact = models.Contact(
        lead_id=lead.id,
        source_id=contact_in.source_id,
        operator_id=operator.id if operator else None,
        message=contact_in.message,
        status="new"
    )
    db.add(db_contact)
    db.flush()
    db.refresh(db_contact)
    return db_contact


def get_contacts(db: Session, skip: int = 0, limit: int = 100):
    return db.execute(select(models.Contact).offset(skip).limit(limit)).scalars().all()


def get_leads(db: Session, skip: int = 0, limit: int = 100):
    return db.execute(select(models.Lead).offset(skip).limit(limit)).scalars().all()


def update_contact_status(db: Session, contact_id: int, new_status: str) -> Optional[models.Contact]:
    contact = db.get(models.Contact, contact_id)
    if not contact:
        return None
    contact.status = new_status
    db.add(contact)
    db.flush()
    db.refresh(contact)
    return contact
