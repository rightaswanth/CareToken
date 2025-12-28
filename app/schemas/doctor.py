from pydantic import BaseModel
from typing import Optional, List
from uuid import UUID
from datetime import datetime

class DoctorBase(BaseModel):
    name: str
    specialty: Optional[str] = None
    consult_duration_minutes: int = 10
    medical_degree: Optional[str] = None
    registration_number: Optional[str] = None
    medical_council: Optional[str] = None
    registration_year: Optional[int] = None

class DoctorCreate(DoctorBase):
    pass

class DoctorResponse(DoctorBase):
    id: UUID
    tenant_id: UUID
    created_at: datetime

    class Config:
        from_attributes = True

class DailySlots(BaseModel):
    date: str
    slots: List[str]

class WeeklySlotsResponse(BaseModel):
    doctor_id: UUID
    start_date: str
    end_date: str
    daily_slots: List[DailySlots]

class CurrentTokenResponse(BaseModel):
    current_token: int
    doctor_id: UUID
    estimated_wait_minutes_per_patient: int

class ConsultingStatusUpdate(BaseModel):
    is_consulting: bool

