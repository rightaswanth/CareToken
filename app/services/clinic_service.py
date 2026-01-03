from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select
from uuid import UUID
from typing import List, Optional

from app.db.models import Tenant, User
from app.schemas.clinic import ClinicCreate, ClinicCreatedResponse, AdminCreatedResponse, ClinicResponse, AdminCredentials
from app.core.utils import generate_slug, generate_username, generate_password
from app.core.security import get_password_hash
from fastapi import HTTPException

class ClinicService:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def create_clinic(self, clinic_data: ClinicCreate) -> ClinicCreatedResponse:
        # 1. Generate Slug
        slug = generate_slug(clinic_data.name)
        
        # 2. Create Tenant
        clinic = Tenant(**clinic_data.model_dump())
        clinic.slug = slug
        
        self.session.add(clinic)
        await self.session.commit()
        await self.session.refresh(clinic)

        # 3. Generate Admin Credentials
        username = generate_username(clinic.name)
        password = generate_password()
        hashed_password = get_password_hash(password)

        # 4. Create Admin User
        admin_user = User(
            tenant_id=clinic.id,
            role="admin",
            name=f"Admin - {clinic.name}",
            username=username,
            password_hash=hashed_password
        )
        self.session.add(admin_user)
        await self.session.commit()

        return ClinicCreatedResponse(
            tenant_id=clinic.id,
            clinic=ClinicResponse.model_validate(clinic),
            admin_credentials=AdminCredentials(username=username, password=password)
        )

    async def create_admin(self, tenant_id: UUID, current_user: User) -> AdminCreatedResponse:
        # Verify tenant exists
        tenant = await self.session.get(Tenant, tenant_id)
        if not tenant:
            raise HTTPException(status_code=404, detail="Clinic not found")

        # Verify user has permission (must be admin of this tenant)
        if current_user.tenant_id != tenant_id or current_user.role != "admin":
             raise HTTPException(status_code=403, detail="Not authorized to add admins to this clinic")

        # Generate Credentials
        username = generate_username(tenant.name)
        password = generate_password()
        hashed_password = get_password_hash(password)

        # Create Admin User
        new_admin = User(
            tenant_id=tenant_id,
            role="admin",
            name=f"Admin - {tenant.name}",
            username=username,
            password_hash=hashed_password
        )
        
        self.session.add(new_admin)
        await self.session.commit()
        await self.session.refresh(new_admin)
        
        # Use UserResponse from schemas/user.py if possible, but here we used schemas/clinic.py
        # Let's import UserResponse from user schema to be consistent
        from app.schemas.user import UserResponse
        
        return AdminCreatedResponse(
            user=UserResponse.model_validate(new_admin),
            credentials=AdminCredentials(username=username, password=password)
        )

    async def get_clinics(self, city: Optional[str] = None, skip: int = 0, limit: int = 100) -> List[Tenant]:
        query = select(Tenant)
        if city:
            query = query.where(Tenant.city == city)
        query = query.offset(skip).limit(limit)
        result = await self.session.execute(query)
        return result.scalars().all()

    async def get_clinic(self, clinic_id: UUID) -> Tenant:
        clinic = await self.session.get(Tenant, clinic_id)
        if not clinic:
            raise HTTPException(status_code=404, detail="Clinic not found")
        return clinic

    async def get_dashboard_stats(self, tenant_id: UUID) -> dict:
        from app.db.models import Patient, Appointment, Doctor
        from sqlalchemy import func, select
        from datetime import date
        from sqlalchemy.orm import selectinload
        
        today = date.today()
        
        # 1. Total Patients
        stmt_patients = select(func.count(Patient.id)).where(Patient.tenant_id == tenant_id)
        total_patients = (await self.session.execute(stmt_patients)).scalar() or 0
        
        # 2. Appointments Today
        stmt_appointments_today = select(func.count(Appointment.id)).where(
            Appointment.tenant_id == tenant_id,
            func.date(Appointment.scheduled_start) == today
        )
        appointments_today = (await self.session.execute(stmt_appointments_today)).scalar() or 0
        
        # 3. Active Doctors
        # Assuming all doctors are active for now, or check schedule?
        # Let's just count all doctors for the tenant
        stmt_doctors = select(func.count(Doctor.id)).where(Doctor.tenant_id == tenant_id)
        active_doctors = (await self.session.execute(stmt_doctors)).scalar() or 0
        
        # 4. Completed Appointments (Today)
        stmt_completed = select(Appointment).options(
            selectinload(Appointment.patient)
        ).where(
            Appointment.tenant_id == tenant_id,
            Appointment.state == "completed",
            func.date(Appointment.scheduled_start) == today
        ).order_by(Appointment.ended_at.desc())
        
        result_completed = await self.session.execute(stmt_completed)
        completed_appointments = result_completed.scalars().all()
        
        # Format completed appointments
        formatted_completed = []
        for appt in completed_appointments:
            token_display = str(appt.token_number)
            if appt.is_emergency:
                token_display = f"E{appt.token_number}"
                
            formatted_completed.append({
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
                "patient_phone": appt.patient.phone,
                "patient_gender": appt.patient.gender
            })
            
        return {
            "total_patients": total_patients,
            "appointments_today": appointments_today,
            "active_doctors": active_doctors,
            "completed_appointments_count": len(formatted_completed),
            "completed_appointments": formatted_completed
        }
