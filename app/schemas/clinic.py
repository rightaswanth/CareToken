from pydantic import BaseModel, Field
from typing import Optional, List, Dict
from uuid import UUID
from datetime import datetime

class ClinicBase(BaseModel):
    name: str
    city: str
    address: Optional[str] = None
    phone: Optional[str] = None
    clinic_type: Optional[str] = None
    year_of_establishment: Optional[int] = None
    speciality_offer: List[str] = []
    clinic_registration_number: Optional[str] = None
    issued_authority: Optional[str] = None

class ClinicCreate(ClinicBase):
    pass

class ClinicResponse(ClinicBase):
    id: UUID
    slug: str
    created_at: datetime

    class Config:
        from_attributes = True

class AdminCredentials(BaseModel):
    username: str
    password: str

class ClinicCreatedResponse(BaseModel):
    clinic: ClinicResponse
    admin_credentials: AdminCredentials

class AdminCreate(BaseModel):
    # We might not need many fields here if we auto-generate everything, 
    # but usually we might want to allow setting name or email.
    # For now, based on previous logic, we auto-generate mostly.
    # But let's allow optional fields if needed, or just empty if purely auto.
    # The previous endpoint took a User object.
    name: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None

class UserResponse(BaseModel):
    id: UUID
    tenant_id: Optional[UUID]
    role: str
    name: str
    username: Optional[str]
    email: Optional[str]
    phone: Optional[str]
    created_at: datetime

    class Config:
        from_attributes = True

class AdminCreatedResponse(BaseModel):
    user: UserResponse
    credentials: AdminCredentials
