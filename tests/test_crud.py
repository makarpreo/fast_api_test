# tests/test_crud.py
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app import models, crud, schemas
from app.models import Base
from app.crud import DistributionService

TEST_SQLALCHEMY_DATABASE_URL = "sqlite:///:memory:"

engine = create_engine(
    TEST_SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False}
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


@pytest.fixture(scope="function")
def db():
    Base.metadata.create_all(bind=engine)
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(bind=engine)


def test_create_operator_and_source(db):
    op_data = schemas.OperatorCreate(name="Alice", max_active_leads=3)
    op = crud.create_operator(db, op_data)
    assert op.id is not None
    assert op.name == "Alice"
    assert op.max_active_leads == 3

    src_data = schemas.SourceCreate(name="Website")
    src = crud.create_source(db, src_data)
    assert src.id is not None
    assert src.name == "Website"


def test_create_weight_and_assign_operator(db):
    op = crud.create_operator(db, schemas.OperatorCreate(name="Bob"))
    src = crud.create_source(db, schemas.SourceCreate(name="Landing"))

    weight_data = schemas.OperatorSourceWeightCreate(operator_id=op.id, source_id=src.id, weight=5)
    weight = crud.create_operator_source_weight(db, weight_data)
    assert weight.id is not None
    assert weight.weight == 5

    assigned_op = DistributionService.assign_operator(db, src.id)
    assert assigned_op is not None
    assert assigned_op.id == op.id


def test_create_contact_and_lead(db):
    op = crud.create_operator(db, schemas.OperatorCreate(name="Charlie"))
    src = crud.create_source(db, schemas.SourceCreate(name="Facebook"))
    crud.create_operator_source_weight(db, schemas.OperatorSourceWeightCreate(operator_id=op.id, source_id=src.id, weight=1))

    contact_data = schemas.ContactCreate(
        external_id="123",
        phone="555-1234",
        email="test@example.com",
        name="John Doe",
        source_id=src.id,
        message="Hello"
    )
    contact = crud.create_contact(db, contact_data)
    assert contact.id is not None
    assert contact.operator_id == op.id
    assert contact.status == "new"

    lead = db.get(models.Lead, contact.lead_id)
    assert lead is not None
    assert lead.phone == "555-1234"


def test_get_operators_with_active_contacts(db):
    op = crud.create_operator(db, schemas.OperatorCreate(name="Dana", max_active_leads=5))
    src = crud.create_source(db, schemas.SourceCreate(name="Instagram"))
    crud.create_operator_source_weight(db, schemas.OperatorSourceWeightCreate(operator_id=op.id, source_id=src.id, weight=1))

    for i in range(3):
        contact_data = schemas.ContactCreate(
            external_id=str(i),
            phone=f"555-12{i}",
            name=f"User {i}",
            source_id=src.id
        )
        crud.create_contact(db, contact_data)

    operators = crud.get_operators(db)
    assert len(operators) == 1
    assert operators[0].active_contacts == 3


def test_update_contact_status(db):
    op = crud.create_operator(db, schemas.OperatorCreate(name="Eve"))
    src = crud.create_source(db, schemas.SourceCreate(name="Twitter"))
    crud.create_operator_source_weight(db, schemas.OperatorSourceWeightCreate(operator_id=op.id, source_id=src.id))
    contact_data = schemas.ContactCreate(
        external_id="999",
        phone="555-999",
        name="Test User",
        source_id=src.id
    )
    contact = crud.create_contact(db, contact_data)

    updated = crud.update_contact_status(db, contact.id, "completed")
    assert updated.status == "completed"

    db.refresh(updated)
    assert updated.status == "completed"
