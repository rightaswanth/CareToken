from sqlmodel import SQLModel, Field, Relationship
from typing import Optional, List, TYPE_CHECKING
from datetime import datetime
from uuid import UUID, uuid4

if TYPE_CHECKING:
    from .tenant import Tenant
    from .user import User
    from .schedule import Schedule
    from .appointment import Appointment

class Doctor(SQLModel, table=True):
    __tablename__ = "doctors"
    id: UUID = Field(default_factory=uuid4, primary_key=True)
    tenant_id: UUID = Field(foreign_key="tenants.id")
    user_id: UUID = Field(foreign_key="users.id")
    specialty: Optional[str] = None
    consult_duration_minutes: int = Field(default=10)
    created_at: datetime = Field(default_factory=datetime.utcnow)

    tenant: "Tenant" = Relationship(back_populates="doctors")
    user: "User" = Relationship(back_populates="doctor_profile")
    schedules: List["Schedule"] = Relationship(back_populates="doctor")
    appointments: List["Appointment"] = Relationship(back_populates="doctor")
