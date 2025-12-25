from sqlmodel import SQLModel, Field
from typing import Optional
from datetime import datetime
from uuid import UUID, uuid4

class Counter(SQLModel, table=True):
    __tablename__ = "counters"
    id: UUID = Field(default_factory=uuid4, primary_key=True)
    tenant_id: Optional[UUID] = None
    doctor_id: Optional[UUID] = None
    date: datetime
    last_token: int = Field(default=0)
