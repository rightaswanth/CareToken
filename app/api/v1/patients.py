from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from typing import Optional
from app.db.session import get_session
from app.db.models import User
from app.api.deps import get_current_user, get_current_patient
from app.schemas.patient import PatientOTPRequest, PatientOTPVerify, PatientLoginResponse, PatientListResponse
from app.services.patient_service import PatientService

router = APIRouter()

async def get_patient_service(session: AsyncSession = Depends(get_session)) -> PatientService:
    return PatientService(session)

@router.post("/request-otp")
async def request_otp(
    payload: PatientOTPRequest,
    service: PatientService = Depends(get_patient_service)
):
    return await service.request_otp(payload)

@router.post("/verify-otp", response_model=PatientLoginResponse)
async def verify_otp(
    payload: PatientOTPVerify,
    service: PatientService = Depends(get_patient_service)
):
    return await service.verify_otp(payload)

@router.get("/recent", response_model=PatientListResponse)
async def get_recent_patients(
    limit: int = 10,
    offset: int = 0,
    current_user: User = Depends(get_current_user),
    service: PatientService = Depends(get_patient_service)
):
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Not authorized")
    return await service.get_recent_patients(limit, offset)

@router.get("/", response_model=PatientListResponse)
async def get_all_patients(
    search: Optional[str] = None,
    limit: int = 10,
    offset: int = 0,
    current_user: User = Depends(get_current_user),
    service: PatientService = Depends(get_patient_service)
):
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Not authorized")
    return await service.get_all_patients(search, limit, offset)

@router.get("/appointments/active", response_model=list[dict])
async def get_active_appointments(
    current_user: User = Depends(get_current_patient),
    service: PatientService = Depends(get_patient_service)
):
    return await service.get_active_appointments(current_user)

@router.get("/appointments/previous", response_model=list[dict])
async def get_previous_appointments(
    current_user: User = Depends(get_current_patient),
    service: PatientService = Depends(get_patient_service)
):
    return await service.get_previous_appointments(current_user)
