from typing import List, Union
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Doctor, Schedule, User, AppUser
from app.db.session import get_session
from app.schemas.schedule import ScheduleCreate, ScheduleUpdate
from app.schemas.doctor import DoctorCreate, WeeklySlotsResponse, CurrentTokenResponse
from app.schemas.doctor import ConsultingStatusUpdate
from app.services.doctor_service import DoctorService
from app.api.deps import get_current_user, get_current_user_or_patient, get_current_user_or_patient_optional
from pydantic import BaseModel



router = APIRouter()

@router.post("/{tenant_id}/doctors", response_model=Doctor)
async def create_doctor(
    tenant_id: UUID,
    doctor_data: DoctorCreate,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session)
):
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Not authorized")
    service = DoctorService(session)
    # Convert schema to model
    doctor_dict = doctor_data.model_dump()
    doctor_dict["tenant_id"] = tenant_id
    doctor = Doctor.model_validate(doctor_dict)
    return await service.create_doctor(tenant_id, doctor)

@router.get("/{tenant_id}/doctors", response_model=List[Doctor])
async def read_doctors(
    tenant_id: UUID,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session)
):
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Not authorized")
    service = DoctorService(session)
    return await service.get_doctors(tenant_id)

@router.get("/{tenant_id}/list", response_model=List[Doctor])
async def read_doctors_public(
    tenant_id: UUID,
    current_user: Union[User, AppUser, None] = Depends(get_current_user_or_patient_optional),
    session: AsyncSession = Depends(get_session)
):
    # Allow any authenticated user (admin or patient/app_user)
    service = DoctorService(session)
    return await service.get_doctors(tenant_id)


@router.post("/{doctor_id}/schedules", response_model=List[Schedule])
async def create_schedule(
    doctor_id: UUID,
    schedules: List[ScheduleCreate],
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session)
):
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Not authorized")
    service = DoctorService(session)
    return await service.create_schedule(doctor_id, schedules)

@router.get("/{doctor_id}/slots", response_model=WeeklySlotsResponse)
async def get_doctor_slots(
    doctor_id: UUID,
    date: str, # YYYY-MM-DD
    current_user: Union[User, AppUser] = Depends(get_current_user_or_patient),
    session: AsyncSession = Depends(get_session)
):
    service = DoctorService(session)
    return await service.get_doctor_slots(doctor_id, date)

@router.delete("/schedules/{schedule_id}")
async def deactivate_schedule(
    schedule_id: UUID,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session)
):
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Not authorized")

    service = DoctorService(session)
    return await service.deactivate_schedule(schedule_id)


@router.put("/schedules/{schedule_id}", response_model=Schedule)
async def update_schedule(
    schedule_id: UUID,
    schedule_update: ScheduleUpdate,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session)
):
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Not authorized")

    service = DoctorService(session)
    return await service.update_schedule(schedule_id, schedule_update)


@router.post("/{doctor_id}/consulting-status", response_model=Doctor)
async def update_consulting_status(
    doctor_id: UUID,
    status_update: ConsultingStatusUpdate,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session)
):
    if current_user.role != "admin":
         raise HTTPException(status_code=403, detail="Not authorized")

    service = DoctorService(session)
    return await service.update_consulting_status(doctor_id, status_update.is_consulting)

@router.get("/{doctor_id}/current", response_model=CurrentTokenResponse)
async def get_current_token(
    doctor_id: UUID,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session)
):
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Not authorized")
    service = DoctorService(session)
    return await service.get_current_token(doctor_id)

from app.schemas.appointment import AppointmentResponse
from app.services.appointment_service import AppointmentService
from datetime import date

@router.get("/{doctor_id}/appointments", response_model=List[AppointmentResponse])
async def get_doctor_appointments(
    doctor_id: UUID,
    date: date,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session)
):
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Not authorized")
        
    service = AppointmentService(session)
    return await service.get_appointments_by_date(doctor_id, date)
