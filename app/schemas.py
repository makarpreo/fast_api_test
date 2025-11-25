# app/schemas.py
from pydantic import BaseModel, EmailStr, Field
from datetime import datetime
from typing import Optional

# Operator schemas
class OperatorBase(BaseModel):
    name: str
    is_active: bool = True
    max_active_leads: int = 5

class OperatorCreate(OperatorBase):
    pass

class Operator(OperatorBase):
    id: int
    active_contacts: int = 0

    class Config:
        from_attributes = True


# Source schemas
class SourceBase(BaseModel):
    name: str
    description: Optional[str] = None

class SourceCreate(SourceBase):
    pass

class Source(SourceBase):
    id: int

    class Config:
        from_attributes = True


# Lead schemas
class LeadBase(BaseModel):
    external_id: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[EmailStr] = None
    name: Optional[str] = None

class LeadCreate(LeadBase):
    pass

class Lead(LeadBase):
    id: int
    created_at: datetime

    class Config:
        from_attributes = True


# Contact schemas
class ContactBase(BaseModel):
    source_id: int
    message: Optional[str] = None

class ContactCreate(ContactBase):
    external_id: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[EmailStr] = None
    name: Optional[str] = None

class Contact(ContactBase):
    id: int
    lead_id: int
    operator_id: Optional[int]
    status: str
    created_at: datetime

    class Config:
        from_attributes = True


# Weight schemas
class OperatorSourceWeightBase(BaseModel):
    operator_id: int
    source_id: int
    weight: int = Field(default=1, ge=1)

class OperatorSourceWeightCreate(OperatorSourceWeightBase):
    pass

class OperatorSourceWeight(OperatorSourceWeightBase):
    id: int

    class Config:
        from_attributes = True

