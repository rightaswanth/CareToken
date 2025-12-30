from pydantic import BaseModel
from typing import Optional
from uuid import UUID

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
