from sqlmodel import SQLModel, Field, Relationship
from sqlalchemy import JSON, Column
from typing import Optional, List, TYPE_CHECKING
from datetime import datetime
from uuid import UUID, uuid4

if TYPE_CHECKING:
    from .user import User
    from .doctor import Doctor
    from .patient import Patient
    from .appointment import Appointment

class Tenant(SQLModel, table=True):
    __tablename__ = "tenants"
    id: UUID = Field(default_factory=uuid4, primary_key=True)
    name: str
    slug: str = Field(unique=True, index=True)
    city: str
    address: Optional[str] = None
    phone: Optional[str] = None
    clinic_type: Optional[str] = None
    year_of_establishment: Optional[int] = None
    speciality_offer: List[str] = Field(default=[], sa_column=Column(JSON))
    clinic_registration_number: Optional[str] = None
    issued_authority: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)

    users: List["User"] = Relationship(back_populates="tenant")
    doctors: List["Doctor"] = Relationship(back_populates="tenant")
    patients: List["Patient"] = Relationship(back_populates="tenant")
    appointments: List["Appointment"] = Relationship(back_populates="tenant")
