from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select, func, and_
from uuid import UUID
from datetime import datetime, date, timezone
from fastapi import HTTPException

from app.db.models.appointment import Appointment
from app.db.models.patient import Patient
from app.db.models.doctor import Doctor
from app.schemas.appointment import AppointmentCreatePatient, AppointmentCreateAdmin, PatientCreate

class AppointmentService:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_patient_by_phone(self, phone: str, tenant_id: UUID) -> Patient | None:
        stmt = select(Patient).where(
            Patient.phone == phone,
            Patient.tenant_id == tenant_id
        )
        result = await self.session.execute(stmt)
        return result.scalars().first()

    async def create_or_get_patient(self, patient_data: PatientCreate, tenant_id: UUID) -> Patient:
        patient = await self.get_patient_by_phone(patient_data.phone, tenant_id)
        if not patient:
            patient = Patient(
                tenant_id=tenant_id,
                name=patient_data.name,
                phone=patient_data.phone,
                age=patient_data.age,
                gender=patient_data.gender,
                phone_verified=False
            )
            self.session.add(patient)
            await self.session.commit()
            await self.session.refresh(patient)
        return patient

    async def get_next_token(self, doctor_id: UUID, appt_date: date, is_emergency: bool) -> int:
        stmt = select(func.max(Appointment.token_number)).where(
            Appointment.doctor_id == doctor_id,
            func.date(Appointment.scheduled_start) == appt_date,
            Appointment.is_emergency == is_emergency
        )
        result = await self.session.execute(stmt)
        max_token = result.scalar() or 0
        return max_token + 1

    async def calculate_wait_time(self, doctor: Doctor, appt_date: date, token_number: int, is_emergency: bool) -> int:
        # Count uncompleted normal tokens < this token (if normal)
        # Count all uncompleted emergency tokens (if normal)
        # If emergency, count uncompleted emergency < this token
        
        # This is a simplified estimation
        # Ideally we check state != 'completed' and state != 'cancelled'
        
        active_states = ["created", "waiting", "consulting"]
        
        if is_emergency:
            # Count emergency tokens ahead
            stmt = select(func.count(Appointment.id)).where(
                Appointment.doctor_id == doctor.id,
                func.date(Appointment.scheduled_start) == appt_date,
                Appointment.is_emergency == True,
                Appointment.token_number < token_number,
                Appointment.state.in_(active_states)
            )
            result = await self.session.execute(stmt)
            ahead_count = result.scalar() or 0
        else:
            # Count normal tokens ahead
            stmt_normal = select(func.count(Appointment.id)).where(
                Appointment.doctor_id == doctor.id,
                func.date(Appointment.scheduled_start) == appt_date,
                Appointment.is_emergency == False,
                Appointment.token_number < token_number,
                Appointment.state.in_(active_states)
            )
            
            # Count all emergency tokens (assuming they take priority)
            stmt_emergency = select(func.count(Appointment.id)).where(
                Appointment.doctor_id == doctor.id,
                func.date(Appointment.scheduled_start) == appt_date,
                Appointment.is_emergency == True,
                Appointment.state.in_(active_states)
            )
            
            result_normal = await self.session.execute(stmt_normal)
            result_emergency = await self.session.execute(stmt_emergency)
            
            ahead_count = (result_normal.scalar() or 0) + (result_emergency.scalar() or 0)

        # Assuming consult_duration_minutes is on Doctor model
        # Check doctor model for correct field name, assuming 'consult_duration_minutes' from previous file view
        duration = getattr(doctor, 'consult_duration_minutes', 15) # Default 15 if missing
        return ahead_count * duration * 60

    async def create_appointment_patient(self, data: AppointmentCreatePatient) -> Appointment:
        # 1. Validate Doctor
        doctor = await self.session.get(Doctor, data.doctor_id)
        if not doctor:
            raise HTTPException(status_code=404, detail="Doctor not found")

        # 2. Get or Create Patient
        patient = await self.create_or_get_patient(data.patient, data.tenant_id)

        # 3. Assign Token
        appt_date = data.preferred_slot.date()
        next_token = await self.get_next_token(data.doctor_id, appt_date, is_emergency=False)

        # Ensure scheduled_start is naive UTC
        scheduled_start = data.preferred_slot
        if scheduled_start.tzinfo is not None:
            scheduled_start = scheduled_start.astimezone(timezone.utc).replace(tzinfo=None)

        # 4. Create Appointment
        appointment = Appointment(
            tenant_id=data.tenant_id,
            doctor_id=data.doctor_id,
            patient_id=patient.id,
            token_number=next_token,
            state="created",
            scheduled_start=scheduled_start,
            is_phone_booking=False,
            is_emergency=False,
            is_late=False
        )
        self.session.add(appointment)
        await self.session.commit()
        await self.session.refresh(appointment)
        
        return appointment

    async def create_appointment_admin(self, data: AppointmentCreateAdmin) -> Appointment:
        # 1. Validate Doctor
        doctor = await self.session.get(Doctor, data.doctor_id)
        if not doctor:
            raise HTTPException(status_code=404, detail="Doctor not found")

        # 2. Get or Create Patient
        patient = await self.create_or_get_patient(data.patient, data.tenant_id)

        # 3. Assign Token
        appt_date = data.preferred_slot.date()
        next_token = await self.get_next_token(data.doctor_id, appt_date, is_emergency=data.is_emergency)

        # Ensure scheduled_start is naive UTC
        scheduled_start = data.preferred_slot
        if scheduled_start.tzinfo is not None:
            scheduled_start = scheduled_start.astimezone(timezone.utc).replace(tzinfo=None)

        # 4. Create Appointment
        appointment = Appointment(
            tenant_id=data.tenant_id,
            doctor_id=data.doctor_id,
            patient_id=patient.id,
            token_number=next_token,
            state="created",
            scheduled_start=scheduled_start,
            is_phone_booking=data.is_phone_booking,
            is_emergency=data.is_emergency,
            is_late=data.is_late
        )
        self.session.add(appointment)
        await self.session.commit()
        await self.session.refresh(appointment)

        return appointment

    async def get_doctor_appointments(self, doctor_id: UUID, date: date, status: list[str] | None = None) -> list[Appointment]:
        stmt = select(Appointment).where(
            Appointment.doctor_id == doctor_id,
            func.date(Appointment.scheduled_start) == date
        )
        
        if status:
            stmt = stmt.where(Appointment.state.in_(status))
            
        stmt = stmt.order_by(Appointment.token_number)
        
        result = await self.session.execute(stmt)
        return result.scalars().all()
