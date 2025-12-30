from datetime import datetime, timedelta
from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select
import random

from app.db.models import Patient, Tenant, AppUser
from app.schemas.patient import PatientOTPRequest, PatientOTPVerify, PatientLoginResponse
from app.core.security import create_access_token
from app.core.config import settings

class PatientService:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_tenant_by_slug(self, slug: str) -> Tenant:
        stmt = select(Tenant).where(Tenant.slug == slug)
        result = await self.session.execute(stmt)
        tenant = result.scalars().first()
        if not tenant:
            raise HTTPException(status_code=404, detail="Clinic not found")
        return tenant

    async def request_otp(self, data: PatientOTPRequest):
        # Find or create AppUser by phone
        stmt = select(AppUser).where(AppUser.phone == data.phone)
        result = await self.session.execute(stmt)
        app_user = result.scalars().first()
        
        if not app_user:
            app_user = AppUser(phone=data.phone)
            self.session.add(app_user)
            await self.session.commit()
            await self.session.refresh(app_user)

        # Generate OTP
        otp = str(random.randint(100000, 999999))
        
        # Save OTP to app_user
        app_user.otp = otp
        app_user.otp_sent_at = datetime.utcnow()
        self.session.add(app_user)
        await self.session.commit()
        
        # Send OTP (Mocking it here)
        print(f"OTP for {data.phone}: {otp}")
        
        return {"message": "OTP sent successfully", "dev_otp": otp}

    async def verify_otp(self, data: PatientOTPVerify) -> PatientLoginResponse:
        # Find AppUser by phone
        stmt = select(AppUser).where(AppUser.phone == data.phone)
        result = await self.session.execute(stmt)
        app_user = result.scalars().first()
        
        if not app_user:
            raise HTTPException(status_code=404, detail="User not found")
            
        if not app_user.otp or app_user.otp != data.otp:
            raise HTTPException(status_code=400, detail="Invalid OTP")
            
        # Check expiry (e.g., 10 mins)
        if app_user.otp_sent_at and (datetime.utcnow() - app_user.otp_sent_at) > timedelta(minutes=10):
             raise HTTPException(status_code=400, detail="OTP expired")
             
        # Clear OTP after use
        app_user.otp = None 
        self.session.add(app_user)
        await self.session.commit()
        
        # Generate Token
        access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
        token_payload = {
            "sub": str(app_user.id),
            "role": "app_user",
        }
        access_token = create_access_token(
            data=token_payload, expires_delta=access_token_expires
        )
        
        # Store in Redis
        import json
        from app.core.redis import redis_client
        
        token_data = {
            "user_id": str(app_user.id),
            "role": "patient",
            "type": "patient"
        }
        await redis_client.set_token(
            access_token, 
            json.dumps(token_data), 
            settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60
        )
        
        return PatientLoginResponse(
            access_token=access_token,
            token_type="bearer",
            patient_id=app_user.id, # Returning AppUser ID as patient_id for now
            name="App User" # Placeholder
        )
