from sqlmodel import SQLModel, Field, Relationship
from typing import Optional, List, TYPE_CHECKING
from datetime import datetime
from uuid import UUID, uuid4
from sqlalchemy import Column
from sqlalchemy.dialects.postgresql import JSONB

if TYPE_CHECKING:
    from .tenant import Tenant
    from .appointment import Appointment

class Patient(SQLModel, table=True):
    __tablename__ = "patients"
    id: UUID = Field(default_factory=uuid4, primary_key=True)
    tenant_id: Optional[UUID] = Field(default=None, foreign_key="tenants.id")
    name: str
    phone: str
    phone_verified: bool = Field(default=False)
    last_otp_code: Optional[str] = None
    last_otp_sent_at: Optional[datetime] = None
    age: Optional[int] = None
    gender: Optional[str] = None
    meta: Optional[dict] = Field(default=None, sa_column=Column(JSONB))
    created_at: datetime = Field(default_factory=datetime.utcnow)

    tenant: Optional["Tenant"] = Relationship(back_populates="patients")
    appointments: List["Appointment"] = Relationship(back_populates="patient")
