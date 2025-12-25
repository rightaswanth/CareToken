from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import select
from sqlalchemy.ext.asyncio import AsyncSession
from uuid import UUID
from datetime import datetime

from app.db.session import get_session
from app.db.models import Appointment, Doctor, Patient, Tenant

router = APIRouter()

from pydantic import BaseModel
from typing import Optional
from sqlmodel import func

class PatientCreate(BaseModel):
    name: str
    phone: str
    age: Optional[int] = None

class AppointmentCreateRequest(BaseModel):
    doctor_id: UUID
    tenant_id: UUID
    patient: PatientCreate
    preferred_slot: datetime

class AppointmentResponse(BaseModel):
    token_number: int
    estimated_wait_seconds: int
    appointment_id: UUID

@router.post("/", response_model=AppointmentResponse)
async def create_appointment(
    request: AppointmentCreateRequest,
    session: AsyncSession = Depends(get_session)
):
    # 1. Validate Doctor
    doctor = await session.get(Doctor, request.doctor_id)
    if not doctor:
        raise HTTPException(status_code=404, detail="Doctor not found")
    
    # 2. Check or Create Patient
    # Check if patient exists by phone within the same tenant
    stmt = select(Patient).where(
        Patient.phone == request.patient.phone,
        Patient.tenant_id == request.tenant_id
    )
    result = await session.execute(stmt)
    patient = result.scalars().first()
    
    if not patient:
        patient = Patient(
            tenant_id=request.tenant_id,
            name=request.patient.name,
            phone=request.patient.phone,
            age=request.patient.age,
            phone_verified=False # Assuming not verified for now
        )
        session.add(patient)
        await session.commit()
        await session.refresh(patient)
    
    # 3. Assign Token Number
    # Get max token for this doctor on the preferred date
    # Assuming preferred_slot is a datetime
    appt_date = request.preferred_slot.date()
    
    # We need to query appointments for this doctor on this day to find max token
    # Note: This is a simple implementation. In high concurrency, use a sequence or locked counter.
    stmt = select(func.max(Appointment.token_number)).where(
        Appointment.doctor_id == request.doctor_id,
        func.date(Appointment.scheduled_start) == appt_date
    )
    result = await session.execute(stmt)
    max_token = result.scalar() or 0
    next_token = max_token + 1
    
    # 4. Create Appointment
    appointment = Appointment(
        tenant_id=request.tenant_id,
        doctor_id=request.doctor_id,
        patient_id=patient.id,
        token_number=next_token,
        state="created",
        scheduled_start=request.preferred_slot,
        is_phone_booking=False, # API booking
        is_emergency=False,
        is_late=False
    )
    session.add(appointment)
    await session.commit()
    await session.refresh(appointment)
    
    # 5. Calculate estimated wait time
    # Simple estimate: (Token Number - 1) * Consult Duration (if starting from 0 wait)
    # Or better: (Token Number - Current Serving Token) * Duration
    # For now, let's use simple estimate assuming all previous tokens need to be served
    estimated_wait_seconds = (next_token - 1) * doctor.consult_duration_minutes * 60
    
    return AppointmentResponse(
        token_number=next_token,
        estimated_wait_seconds=estimated_wait_seconds,
        appointment_id=appointment.id
    )

@router.get("/{appointment_id}", response_model=Appointment)
async def read_appointment(
    appointment_id: UUID, 
    session: AsyncSession = Depends(get_session)
):
    appointment = await session.get(Appointment, appointment_id)
    if not appointment:
        raise HTTPException(status_code=404, detail="Appointment not found")
    return appointment
