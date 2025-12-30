from sqlmodel import SQLModel, Field, Relationship
from typing import Optional, TYPE_CHECKING
from datetime import datetime
from uuid import UUID, uuid4

if TYPE_CHECKING:
    from .tenant import Tenant

class User(SQLModel, table=True):
    __tablename__ = "users"
    id: UUID = Field(default_factory=uuid4, primary_key=True)
    tenant_id: Optional[UUID] = Field(default=None, foreign_key="tenants.id")
    role: str # admin, doctor, receptionist
    name: str
    username: str = Field(unique=True, index=True)
    email: Optional[str] = None
    phone: Optional[str] = None
    password_hash: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)

    tenant: Optional["Tenant"] = Relationship(back_populates="users")
