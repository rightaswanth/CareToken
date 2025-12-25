from sqlmodel import SQLModel, Field, Relationship
from typing import Optional, TYPE_CHECKING
from datetime import datetime
from uuid import UUID, uuid4
from sqlalchemy import Column
from sqlalchemy.dialects.postgresql import JSONB

if TYPE_CHECKING:
    from .tenant import Tenant
    from .doctor import Doctor
    from .patient import Patient

class Appointment(SQLModel, table=True):
    __tablename__ = "appointments"
    id: UUID = Field(default_factory=uuid4, primary_key=True)
    tenant_id: UUID = Field(foreign_key="tenants.id")
    doctor_id: UUID = Field(foreign_key="doctors.id")
    patient_id: UUID = Field(foreign_key="patients.id")
    token_number: int
    state: str # created, waiting, consulting, completed, cancelled
    scheduled_start: Optional[datetime] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    started_at: Optional[datetime] = None
    ended_at: Optional[datetime] = None
    duration_seconds: Optional[int] = None
    meta: Optional[dict] = Field(default=None, sa_column=Column(JSONB))
    is_emergency: bool = Field(default=False)
    is_phone_booking: bool = Field(default=False)
    is_late: bool = Field(default=False)

    tenant: "Tenant" = Relationship(back_populates="appointments")
    doctor: "Doctor" = Relationship(back_populates="appointments")
    patient: "Patient" = Relationship(back_populates="appointments")
