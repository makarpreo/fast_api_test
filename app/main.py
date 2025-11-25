# app/main.py
from fastapi import FastAPI, Depends, HTTPException, Path
from sqlalchemy.orm import Session
from typing import List
from enum import Enum

from . import models, schemas, crud
from .database import SessionLocal, engine

models.Base.metadata.create_all(bind=engine)

app = FastAPI(title="Lead Distribution CRM")

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

class ContactStatus(str, Enum):
    new = "new"
    in_progress = "in_progress"
    completed = "completed"

@app.post("/operators/", response_model=schemas.Operator)
def create_operator(operator: schemas.OperatorCreate, db: Session = Depends(get_db)):
    op = crud.create_operator(db, operator)
    # Используем оптимизированный подсчёт активных контактов
    operators = crud.DistributionService.get_operators(db, skip=0, limit=1000)  # Получаем всех для поиска нужного
    op_schema = next((o for o in operators if o.id == op.id), schemas.Operator.from_orm(op))
    return op_schema

@app.get("/operators/", response_model=List[schemas.Operator])
def read_operators(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    return crud.DistributionService.get_operators(db, skip=skip, limit=limit)

# --- Sources ---
@app.post("/sources/", response_model=schemas.Source)
def create_source(source: schemas.SourceCreate, db: Session = Depends(get_db)):
    return crud.create_source(db, source)

@app.get("/sources/", response_model=List[schemas.Source])
def read_sources(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    return crud.get_sources(db, skip=skip, limit=limit)

@app.post("/operator-weights/", response_model=schemas.OperatorSourceWeight)
def create_operator_weight(weight: schemas.OperatorSourceWeightCreate, db: Session = Depends(get_db)):
    return crud.create_operator_source_weight(db, weight)

@app.get("/operator-weights/", response_model=List[schemas.OperatorSourceWeight])
def read_operator_weights(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    return crud.get_operator_source_weights(db, skip=skip, limit=limit)

# --- Contacts ---
@app.post("/contacts/", response_model=schemas.Contact)
def create_contact(contact: schemas.ContactCreate, db: Session = Depends(get_db)):
    return crud.create_contact(db, contact)

@app.get("/contacts/", response_model=List[schemas.Contact])
def read_contacts(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    return crud.get_contacts(db, skip=skip, limit=limit)

@app.patch("/contacts/{contact_id}/status", response_model=schemas.Contact)
def update_contact_status(
    contact_id: int = Path(..., gt=0),
    status: ContactStatus = ContactStatus.completed,
    db: Session = Depends(get_db)
):
    updated = crud.update_contact_status(db, contact_id, status.value)
    if not updated:
        raise HTTPException(status_code=404, detail="Contact not found")
    return updated

@app.get("/leads/", response_model=List[schemas.Lead])
def read_leads(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    return crud.get_leads(db, skip=skip, limit=limit)

@app.get("/")
def read_root():
    return {"message": "Lead Distribution CRM API"}
