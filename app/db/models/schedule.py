from sqlmodel import SQLModel, Field, Relationship
from typing import TYPE_CHECKING
from datetime import time
from uuid import UUID, uuid4

if TYPE_CHECKING:
    from .doctor import Doctor

class Schedule(SQLModel, table=True):
    __tablename__ = "schedules"
    id: UUID = Field(default_factory=uuid4, primary_key=True)
    doctor_id: UUID = Field(foreign_key="doctors.id")
    start_time: time
    end_time: time
    day_of_week: int # 0=Sunday..6=Saturday
    is_active: bool = Field(default=True)

    doctor: "Doctor" = Relationship(back_populates="schedules")
