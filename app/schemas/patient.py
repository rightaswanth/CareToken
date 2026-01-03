from pydantic import BaseModel
from typing import Optional, List
from uuid import UUID
from datetime import datetime

class PatientOTPRequest(BaseModel):
    phone: str

class PatientOTPVerify(BaseModel):
    phone: str
    otp: str

class PatientLoginResponse(BaseModel):
    access_token: str
    token_type: str
    patient_id: UUID
    name: str

class PatientResponse(BaseModel):
    id: UUID
    name: str
    phone: str
    age: Optional[int] = None
    gender: Optional[str] = None
    created_at: datetime
    
    class Config:
        from_attributes = True

class PatientListResponse(BaseModel):
    items: List[PatientResponse]
    total: int
    page: int
    size: int
