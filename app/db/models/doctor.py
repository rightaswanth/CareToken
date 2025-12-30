from sqlmodel import SQLModel, Field, Relationship
from typing import Optional, List, TYPE_CHECKING
from datetime import datetime
from uuid import UUID, uuid4

if TYPE_CHECKING:
    from .tenant import Tenant
    from .schedule import Schedule
    from .appointment import Appointment

class Doctor(SQLModel, table=True):
    __tablename__ = "doctors"
    id: UUID = Field(default_factory=uuid4, primary_key=True)
    tenant_id: UUID = Field(foreign_key="tenants.id")
    name: str
    specialty: Optional[str] = None
    medical_degree: Optional[str] = None
    registration_number: Optional[str] = None
    medical_council: Optional[str] = None
    registration_year: Optional[int] = None
    consult_duration_minutes: int = Field(default=10)
    is_consulting: bool = Field(default=False)
    created_at: datetime = Field(default_factory=datetime.utcnow)

    tenant: "Tenant" = Relationship(back_populates="doctors")
    schedules: List["Schedule"] = Relationship(back_populates="doctor")
    appointments: List["Appointment"] = Relationship(back_populates="doctor")
