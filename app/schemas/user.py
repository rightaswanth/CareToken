from pydantic import BaseModel
from typing import Optional
from uuid import UUID
from datetime import datetime

# Reusing UserResponse from clinic.py or defining a common one here.
# It's better to have a common User schema.

class UserBase(BaseModel):
    name: str
    email: Optional[str] = None
    phone: Optional[str] = None

class UserResponse(UserBase):
    id: UUID
    tenant_id: Optional[UUID]
    role: str
    username: Optional[str]
    created_at: datetime
    clinic_id: Optional[UUID] = None # Helper field for login response
    clinic_name: Optional[str] = None # Helper field for login response

    class Config:
        from_attributes = True
