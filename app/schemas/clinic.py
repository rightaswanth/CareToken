from pydantic import BaseModel
from typing import List, Optional
from uuid import UUID
from app.schemas.appointment import AppointmentResponse

class ClinicCreate(BaseModel):
    name: str
    city: str
    address: Optional[str] = None
    phone: Optional[str] = None

class ClinicCreatedResponse(BaseModel):
    id: UUID
    name: str
    city: str
    admin_email: str
    admin_password: str

class AdminCreatedResponse(BaseModel):
    id: UUID
    email: str
    password: str

class ClinicResponse(BaseModel):
    id: UUID
    name: str
    city: str
    address: Optional[str] = None
    phone: Optional[str] = None
    
    class Config:
        from_attributes = True

class DashboardStatsResponse(BaseModel):
    total_patients: int
    appointments_today: int
    active_doctors: int
    completed_appointments_count: int
    completed_appointments: List[AppointmentResponse]
