from sqlmodel import SQLModel, Field
from typing import Optional
from datetime import datetime
from uuid import UUID, uuid4

class AppUser(SQLModel, table=True):
    __tablename__ = "app_users"
    id: UUID = Field(default_factory=uuid4, primary_key=True)
    phone: str = Field(index=True, unique=True)
    otp: Optional[str] = None
    otp_sent_at: Optional[datetime] = None
    is_active: bool = Field(default=True)
    created_at: datetime = Field(default_factory=datetime.utcnow)
