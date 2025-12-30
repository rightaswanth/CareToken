from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_session
from app.schemas.patient import PatientOTPRequest, PatientOTPVerify, PatientLoginResponse
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
