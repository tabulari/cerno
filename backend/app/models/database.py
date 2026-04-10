from datetime import datetime, timezone
from sqlalchemy import (
    Column, Integer, String, Text, Float, Boolean,
    DateTime, Enum, ForeignKey, JSON,
)
from sqlalchemy.orm import DeclarativeBase, relationship

from app.models.schemas import Severity, IncidentState


class Base(DeclarativeBase):
    pass


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, autoincrement=True)
    username = Column(String(50), unique=True, nullable=False, index=True)
    hashed_password = Column(String(255), nullable=False)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    incidents = relationship("Incident", back_populates="reporter")


class Incident(Base):
    __tablename__ = "incidents"

    id = Column(Integer, primary_key=True, autoincrement=True)
    title = Column(String(200), nullable=False)
    description = Column(Text, nullable=False)
    service = Column(String(100), default="unknown")
    state = Column(Enum(IncidentState), default=IncidentState.SUBMITTED, nullable=False, index=True)

    reporter_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    reporter_severity = Column(Enum(Severity), nullable=True)

    triage_severity = Column(Enum(Severity), nullable=True)
    triage_summary = Column(Text, nullable=True)
    triage_runbook = Column(Text, nullable=True)
    confidence = Column(Float, nullable=True)
    needs_human_review = Column(Boolean, default=False)
    reasoning_steps = Column(JSON, nullable=True)

    evidence_paths = Column(JSON, default=list)

    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    reporter = relationship("User", back_populates="incidents")
    ticket = relationship("Ticket", back_populates="incident", uselist=False)


class Ticket(Base):
    __tablename__ = "tickets"

    id = Column(Integer, primary_key=True, autoincrement=True)
    incident_id = Column(Integer, ForeignKey("incidents.id"), unique=True, nullable=False)
    external_id = Column(String(100), nullable=True)
    external_url = Column(String(500), nullable=True)
    provider = Column(String(50), default="mock")
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    incident = relationship("Incident", back_populates="ticket")
