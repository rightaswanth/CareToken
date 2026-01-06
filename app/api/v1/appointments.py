from fastapi import APIRouter, Depends, HTTPException, Query
from typing import List, Optional
from datetime import date
from sqlalchemy.ext.asyncio import AsyncSession
from uuid import UUID

from app.db.session import get_session
from app.db.models import Appointment, Doctor, User
from app.api.deps import get_current_user, get_current_user_or_patient
from app.schemas.appointment import (
    AppointmentCreatePatient, 
    AppointmentCreateAdmin, 
    AppointmentResponse,
    AppointmentStatusUpdate,
    QueueResponse,
    QueueStatusResponse
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

@router.patch("/{appointment_id}/toggle-hold", response_model=AppointmentResponse)
async def toggle_appointment_hold(
    appointment_id: UUID,
    current_user: User = Depends(get_current_user), # Admin only
    service: AppointmentService = Depends(get_appointment_service)
):
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Not authorized")
        
    appointment = await service.toggle_appointment_hold(appointment_id)
    return await construct_response(appointment, service)

@router.post("/admin", response_model=AppointmentResponse)
async def create_appointment_admin(
    request: AppointmentCreateAdmin,
    service: AppointmentService = Depends(get_appointment_service)
):
    appointment = await service.create_appointment_admin(request)
    return await construct_response(appointment, service)

@router.get("/queue", response_model=QueueResponse)
async def get_queue(
    doctor_id: UUID,
    date: date,
    status: Optional[List[str]] = Query(None),

    current_user: User | object = Depends(get_current_user_or_patient),
    service: AppointmentService = Depends(get_appointment_service)
):
    is_admin = getattr(current_user, "role", None) == "admin"
        
    appointments = await service.get_doctor_appointments(doctor_id, date, status)
    
    doctor = await service.session.get(Doctor, doctor_id)
    if not doctor:
        raise HTTPException(status_code=404, detail="Doctor not found")
        
    queue_list = []
    hold_list = []
    
    for appt in appointments:
        wait_seconds = await service.calculate_wait_time(
            doctor, 
            appt.scheduled_start.date(), 
            appt.token_number, 
            appt.is_emergency
        )
        
        token_display = f"E{appt.token_number}" if appt.is_emergency else str(appt.token_number)
        
        response_item = AppointmentResponse(
            id=appt.id,
            token_number=appt.token_number,
            token_display=token_display,
            estimated_wait_seconds=wait_seconds,
            state=appt.state,
            scheduled_start=appt.scheduled_start,
            is_emergency=appt.is_emergency,
            is_late=appt.is_late,
            patient_name=appt.patient.name if (appt.patient and is_admin) else "Patient" if appt.patient else "Unknown",
            patient_age=appt.patient.age if (appt.patient and is_admin) else None
        )
        
        if appt.state == "hold":
            hold_list.append(response_item)
        else:
            queue_list.append(response_item)
        
    return QueueResponse(queue=queue_list, on_hold=hold_list)

@router.get("/queue-status", response_model=QueueStatusResponse)
async def get_queue_status(
    doctor_id: UUID,
    date: date,
    current_user: User | object = Depends(get_current_user_or_patient),
    service: AppointmentService = Depends(get_appointment_service)
):
        
    status = await service.get_queue_status(doctor_id, date)
    return QueueStatusResponse(**status)

@router.get("/{appointment_id}", response_model=AppointmentResponse)
async def read_appointment(
    appointment_id: UUID, 
    service: AppointmentService = Depends(get_appointment_service)
):
    appointment = await service.session.get(Appointment, appointment_id)
    if not appointment:
        raise HTTPException(status_code=404, detail="Appointment not found")
    return await construct_response(appointment, service)

@router.get("/token/details", response_model=dict)
async def get_token_details(
    doctor_id: UUID,
    date: date,
    token_number: int,
    phone: str,
    service: AppointmentService = Depends(get_appointment_service)
):
    details = await service.get_token_details(doctor_id, date, token_number, phone)
    if not details:
        raise HTTPException(status_code=404, detail="Token not found or details incorrect")
    return details
