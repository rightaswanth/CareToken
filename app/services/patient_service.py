from datetime import datetime, timedelta
from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select, func, or_
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
        otp = "1423"
        
        # Save OTP to app_user
        app_user.otp = otp
        app_user.otp_sent_at = datetime.utcnow()
        self.session.add(app_user)
        await self.session.commit()
        
        # Send OTP (Mocking it here)
        # print(f"OTP for {data.phone}: {otp}")
        
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

    async def get_recent_patients(self, limit: int = 10, offset: int = 0) -> dict:
        stmt = select(Patient).order_by(Patient.created_at.desc()).offset(offset).limit(limit)
        result = await self.session.execute(stmt)
        patients = result.scalars().all()
        
        # Get total count
        count_stmt = select(func.count()).select_from(Patient)
        count_result = await self.session.execute(count_stmt)
        total = count_result.scalar()
        
        return {
            "items": patients,
            "total": total,
            "page": offset // limit + 1 if limit > 0 else 1,
            "size": limit
        }

    async def get_all_patients(self, search: str = None, limit: int = 10, offset: int = 0) -> dict:
        stmt = select(Patient)
        
        if search:
            stmt = stmt.where(
                or_(
                    Patient.name.ilike(f"%{search}%"),
                    Patient.phone.ilike(f"%{search}%")
                )
            )
            
        # Get total count before pagination
        count_stmt = select(func.count()).select_from(stmt.subquery())
        count_result = await self.session.execute(count_stmt)
        total = count_result.scalar()
            
        stmt = stmt.order_by(Patient.name.asc()).offset(offset).limit(limit)
        result = await self.session.execute(stmt)
        patients = result.scalars().all()
        
        return {
            "items": patients,
            "total": total,
            "page": offset // limit + 1 if limit > 0 else 1,
            "size": limit
        }

    async def get_active_appointments(self, app_user: AppUser) -> list[dict]:
        from app.db.models.appointment import Appointment
        from app.db.models.doctor import Doctor
        from app.schemas.appointment import AppointmentResponse
        from sqlalchemy.orm import selectinload
        
        # 1. Find Patient(s) linked to this AppUser
        # Assuming AppUser.phone links to Patient.phone
        stmt_patient = select(Patient).where(Patient.phone == app_user.phone)
        result_patient = await self.session.execute(stmt_patient)
        patients = result_patient.scalars().all()
        
        if not patients:
            return []
            
        patient_ids = [p.id for p in patients]
        
        # 2. Find active appointments
        active_states = ["created", "waiting", "consulting", "hold"]
        stmt = select(Appointment).options(
            selectinload(Appointment.doctor),
            selectinload(Appointment.patient)
        ).where(
            Appointment.patient_id.in_(patient_ids),
            Appointment.state.in_(active_states)
        ).order_by(Appointment.scheduled_start.asc())
        
        result = await self.session.execute(stmt)
        appointments = result.scalars().all()
        
        # 3. Format response
        response = []
        for appt in appointments:
            # Calculate wait time (simplified)
            # For now, just return 0 or a placeholder if we don't want to duplicate logic
            # Or we can instantiate AppointmentService if needed, but let's keep it simple
            estimated_wait = 0 
            
            # Token display
            token_display = str(appt.token_number)
            if appt.is_emergency:
                token_display = f"E{appt.token_number}"
                
            response.append({
                "id": appt.id,
                "token_number": appt.token_number,
                "token_display": token_display,
                "estimated_wait_seconds": estimated_wait,
                "state": appt.state,
                "scheduled_start": appt.scheduled_start,
                "is_emergency": appt.is_emergency,
                "is_late": appt.is_late,
                "patient_name": appt.patient.name,
                "patient_age": appt.patient.age,
                "doctor_name": appt.doctor.name,
                "doctor_specialization": appt.doctor.specialty,
                "clinic_name": "Clinic" # Placeholder or fetch from Tenant
            })
            
        return response

    async def get_previous_appointments(self, app_user: AppUser) -> list[dict]:
        from app.db.models.appointment import Appointment
        from sqlalchemy.orm import selectinload
        
        # 1. Find Patient(s) linked to this AppUser
        stmt_patient = select(Patient).where(Patient.phone == app_user.phone)
        result_patient = await self.session.execute(stmt_patient)
        patients = result_patient.scalars().all()
        
        if not patients:
            return []
            
        patient_ids = [p.id for p in patients]
        
        # 2. Find previous appointments
        previous_states = ["completed", "cancelled"]
        stmt = select(Appointment).options(
            selectinload(Appointment.doctor),
            selectinload(Appointment.patient)
        ).where(
            Appointment.patient_id.in_(patient_ids),
            Appointment.state.in_(previous_states)
        ).order_by(Appointment.scheduled_start.desc())
        
        result = await self.session.execute(stmt)
        appointments = result.scalars().all()
        
        # 3. Format response
        response = []
        for appt in appointments:
            token_display = str(appt.token_number)
            if appt.is_emergency:
                token_display = f"E{appt.token_number}"
                
            response.append({
                "id": appt.id,
                "token_number": appt.token_number,
                "token_display": token_display,
                "estimated_wait_seconds": 0,
                "state": appt.state,
                "scheduled_start": appt.scheduled_start,
                "is_emergency": appt.is_emergency,
                "is_late": appt.is_late,
                "patient_name": appt.patient.name,
                "patient_age": appt.patient.age,
                "doctor_name": appt.doctor.name,
                "doctor_specialization": appt.doctor.specialty,
                "clinic_name": "Clinic" 
            })
            
        return response
