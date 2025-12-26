from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from uuid import UUID

from app.db.session import get_session
from app.db.models import Appointment, Doctor
from app.schemas.appointment import (
    AppointmentCreatePatient, 
    AppointmentCreateAdmin, 
    AppointmentResponse
)
from app.services.appointment_service import AppointmentService

router = APIRouter()

async def get_appointment_service(session: AsyncSession = Depends(get_session)) -> AppointmentService:
    return AppointmentService(session)

async def construct_response(appointment: Appointment, service: AppointmentService) -> AppointmentResponse:
    doctor = await service.session.get(Doctor, appointment.doctor_id)
    if not doctor:
        # Should not happen if integrity is maintained
        raise HTTPException(status_code=500, detail="Doctor not found for appointment")
        
    wait_seconds = await service.calculate_wait_time(
        doctor, 
        appointment.scheduled_start.date(), 
        appointment.token_number, 
        appointment.is_emergency
    )
    
    token_display = f"E{appointment.token_number}" if appointment.is_emergency else str(appointment.token_number)
    
    return AppointmentResponse(
        id=appointment.id,
        token_number=appointment.token_number,
        token_display=token_display,
        estimated_wait_seconds=wait_seconds,
        state=appointment.state,
        scheduled_start=appointment.scheduled_start,
        is_emergency=appointment.is_emergency,
        is_late=appointment.is_late
    )

@router.post("/patient", response_model=AppointmentResponse)
async def create_appointment_patient(
    request: AppointmentCreatePatient,
    service: AppointmentService = Depends(get_appointment_service)
):
    appointment = await service.create_appointment_patient(request)
    return await construct_response(appointment, service)

@router.post("/admin", response_model=AppointmentResponse)
async def create_appointment_admin(
    request: AppointmentCreateAdmin,
    service: AppointmentService = Depends(get_appointment_service)
):
    appointment = await service.create_appointment_admin(request)
    return await construct_response(appointment, service)

@router.get("/{appointment_id}", response_model=AppointmentResponse)
async def read_appointment(
    appointment_id: UUID, 
    service: AppointmentService = Depends(get_appointment_service)
):
    appointment = await service.session.get(Appointment, appointment_id)
    if not appointment:
        raise HTTPException(status_code=404, detail="Appointment not found")
    return await construct_response(appointment, service)
