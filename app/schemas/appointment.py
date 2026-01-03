from pydantic import BaseModel, root_validator
from uuid import UUID
from datetime import datetime
from typing import Optional, List

class PatientCreate(BaseModel):
    name: str
    phone: str
    age: Optional[int] = None
    gender: Optional[str] = None

class AppointmentCreateBase(BaseModel):
    doctor_id: UUID
    tenant_id: UUID
    preferred_slot: datetime

class AppointmentCreatePatient(AppointmentCreateBase):
    patient: PatientCreate

class AppointmentCreateAdmin(AppointmentCreateBase):
    patient: PatientCreate
    is_emergency: bool = False
    is_phone_booking: bool = False
    is_late: bool = False

class AppointmentStatusUpdate(BaseModel):
    status: str
    next_appointment_id: Optional[UUID] = None

class AppointmentResponse(BaseModel):
    id: UUID
    token_number: int
    token_display: str 
    estimated_wait_seconds: int
    state: str
    scheduled_start: Optional[datetime]
    is_emergency: bool
    is_late: bool
    patient_name: Optional[str] = None
    patient_age: Optional[int] = None
    patient_phone: Optional[str] = None
    patient_gender: Optional[str] = None
    slot_label: Optional[str] = None
    
    class Config:
        from_attributes = True

class QueueStatusResponse(BaseModel):
    last_completed_token: Optional[str] = None
    current_token: Optional[str] = None
    next_token: Optional[str] = None
    total_waiting: int = 0

class QueueResponse(BaseModel):
    queue: List[AppointmentResponse]
    on_hold: List[AppointmentResponse]
