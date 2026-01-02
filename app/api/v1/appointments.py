from fastapi import APIRouter, Depends, HTTPException, Query
from typing import List, Optional
from datetime import date
from sqlalchemy.ext.asyncio import AsyncSession
from uuid import UUID

from app.db.session import get_session
from app.db.models import Appointment, Doctor, User
from app.api.deps import get_current_user
from app.schemas.appointment import (
    AppointmentCreatePatient, 
    AppointmentCreateAdmin, 
    AppointmentResponse,
    AppointmentStatusUpdate
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
    
    # Ensure patient is loaded
    if appointment.patient_id and "patient" not in appointment.__dict__:
        from app.db.models import Patient
        appointment.patient = await service.session.get(Patient, appointment.patient_id)

    return AppointmentResponse(
        id=appointment.id,
        token_number=appointment.token_number,
        token_display=token_display,
        estimated_wait_seconds=wait_seconds,
        state=appointment.state,
        scheduled_start=appointment.scheduled_start,
        is_emergency=appointment.is_emergency,
        is_late=appointment.is_late,
        patient_name=appointment.patient.name if appointment.patient else "Unknown",
        patient_age=appointment.patient.age if appointment.patient else None
    )

@router.post("/patient", response_model=AppointmentResponse)
async def create_appointment_patient(
    request: AppointmentCreatePatient,
    service: AppointmentService = Depends(get_appointment_service)
):
    appointment = await service.create_appointment_patient(request)
    return await construct_response(appointment, service)

@router.patch("/{appointment_id}/status", response_model=AppointmentResponse)
async def update_appointment_status(
    appointment_id: UUID,
    data: AppointmentStatusUpdate,
    current_user: User = Depends(get_current_user), # Admin only
    service: AppointmentService = Depends(get_appointment_service)
):
    # TODO: Add role check if needed, assuming get_current_user ensures auth
    appointment = await service.update_appointment_status(appointment_id, data.status, data.next_appointment_id)
    return await construct_response(appointment, service)

@router.post("/admin", response_model=AppointmentResponse)
async def create_appointment_admin(
    request: AppointmentCreateAdmin,
    service: AppointmentService = Depends(get_appointment_service)
):
    appointment = await service.create_appointment_admin(request)
    return await construct_response(appointment, service)

@router.get("/queue", response_model=List[AppointmentResponse])
async def get_queue(
    doctor_id: UUID,
    date: date,
    status: Optional[List[str]] = Query(None),
    current_user: User = Depends(get_current_user),
    service: AppointmentService = Depends(get_appointment_service)
):
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Not authorized")
        
    appointments = await service.get_doctor_appointments(doctor_id, date, status)
    
    doctor = await service.session.get(Doctor, doctor_id)
    if not doctor:
        raise HTTPException(status_code=404, detail="Doctor not found")
        
    responses = []
    for appt in appointments:
        wait_seconds = await service.calculate_wait_time(
            doctor, 
            appt.scheduled_start.date(), 
            appt.token_number, 
            appt.is_emergency
        )
        
        token_display = f"E{appt.token_number}" if appt.is_emergency else str(appt.token_number)
        
        responses.append(AppointmentResponse(
            id=appt.id,
            token_number=appt.token_number,
            token_display=token_display,
            estimated_wait_seconds=wait_seconds,
            state=appt.state,
            scheduled_start=appt.scheduled_start,
            is_emergency=appt.is_emergency,
            is_late=appt.is_late,
            patient_name=appt.patient.name if appt.patient else "Unknown",
            patient_age=appt.patient.age if appt.patient else None
        ))
        
    return responses

@router.get("/{appointment_id}", response_model=AppointmentResponse)
async def read_appointment(
    appointment_id: UUID, 
    service: AppointmentService = Depends(get_appointment_service)
):
    appointment = await service.session.get(Appointment, appointment_id)
    if not appointment:
        raise HTTPException(status_code=404, detail="Appointment not found")
    return await construct_response(appointment, service)
