from datetime import timedelta
from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from app.core.config import settings
from app.core.security import verify_password, create_access_token
from app.db.models import User, Tenant
from app.schemas.auth import LoginRequest, LoginResponse, UserInfo

class AuthService:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def login(self, login_data: LoginRequest) -> LoginResponse:
        # 1. Find Clinic by Slug
        stmt = select(Tenant).where(Tenant.slug == login_data.clinic_slug)
        result = await self.session.execute(stmt)
        clinic = result.scalars().first()
        
        if not clinic:
            raise HTTPException(status_code=404, detail="Clinic not found")

        # 2. Find User in that Clinic
        stmt = select(User).where(
            User.tenant_id == clinic.id,
            User.username == login_data.username
        )
        result = await self.session.execute(stmt)
        user = result.scalars().first()

        if not user:
            raise HTTPException(status_code=401, detail="Invalid username or password")

        # 3. Verify Password
        if not verify_password(login_data.password, user.password_hash):
            raise HTTPException(status_code=401, detail="Invalid username or password")

        # 4. Generate Token
        access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
        access_token = create_access_token(
            data={"sub": str(user.id)}, expires_delta=access_token_expires
        )
        
        # Store in Redis
        import json
        from app.core.redis import redis_client
        
        token_data = {
            "user_id": str(user.id),
            "role": user.role,
            "type": "admin"
        }
        await redis_client.set_token(
            access_token, 
            json.dumps(token_data), 
            settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60
        )

        return LoginResponse(
            access_token=access_token,
            token_type="bearer",
            user=UserInfo(
                id=user.id,
                name=user.name,
                role=user.role,
                clinic_id=clinic.id,
                clinic_name=clinic.name
            )
        )
