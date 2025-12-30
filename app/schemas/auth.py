from pydantic import BaseModel
from uuid import UUID

class LoginRequest(BaseModel):
    clinic_slug: str
    username: str
    password: str

class UserInfo(BaseModel):
    id: UUID
    name: str
    role: str
    clinic_id: UUID
    clinic_name: str

class LoginResponse(BaseModel):
    access_token: str
    token_type: str
    user: UserInfo
