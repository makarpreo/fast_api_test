# app/models.py
from datetime import datetime
from sqlalchemy import Integer, String, Boolean, ForeignKey, DateTime, Text, Column
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship

class Base(DeclarativeBase):
    pass

class Operator(Base):
    __tablename__ = "operators"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    max_active_leads: Mapped[int] = mapped_column(Integer, default=5)

    source_weights = relationship("OperatorSourceWeight", back_populates="operator", cascade="all, delete-orphan")
    contacts = relationship("Contact", back_populates="operator", cascade="all, delete-orphan")

class Lead(Base):
    __tablename__ = "leads"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    external_id: Mapped[str | None] = mapped_column(String, unique=True, index=True, nullable=True)
    phone: Mapped[str | None] = mapped_column(String, index=True, nullable=True)
    email: Mapped[str | None] = mapped_column(String, index=True, nullable=True)
    name: Mapped[str | None] = mapped_column(String, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    contacts = relationship("Contact", back_populates="lead", cascade="all, delete-orphan")

class Source(Base):
    __tablename__ = "sources"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String, unique=True, nullable=False)
    description: Mapped[str | None] = mapped_column(String, nullable=True)

    operator_weights = relationship("OperatorSourceWeight", back_populates="source", cascade="all, delete-orphan")
    contacts = relationship("Contact", back_populates="source", cascade="all, delete-orphan")

class OperatorSourceWeight(Base):
    __tablename__ = "operator_source_weights"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    operator_id: Mapped[int] = mapped_column(ForeignKey("operators.id"))
    source_id: Mapped[int] = mapped_column(ForeignKey("sources.id"))
    weight: Mapped[int] = mapped_column(Integer, default=1)

    operator = relationship("Operator", back_populates="source_weights")
    source = relationship("Source", back_populates="operator_weights")

class Contact(Base):
    __tablename__ = "contacts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    lead_id: Mapped[int] = mapped_column(ForeignKey("leads.id"))
    source_id: Mapped[int] = mapped_column(ForeignKey("sources.id"))
    operator_id: Mapped[int | None] = mapped_column(ForeignKey("operators.id"), nullable=True)
    message: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String, default="new")  # new, in_progress, completed
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    lead = relationship("Lead", back_populates="contacts")
    source = relationship("Source", back_populates="contacts")
    operator = relationship("Operator", back_populates="contacts")
