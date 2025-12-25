from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import select
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel

from app.db.session import get_session
from app.db.models import Patient

router = APIRouter()

class OTPRequest(BaseModel):
    phone: str

class OTPVerify(BaseModel):
    phone: str
    otp: str

@router.post("/request-otp")
async def request_otp(payload: OTPRequest):
    # Logic to generate and send OTP via Twilio would go here
    return {"message": "OTP sent successfully", "phone": payload.phone}

@router.post("/verify-otp")
async def verify_otp(payload: OTPVerify, session: AsyncSession = Depends(get_session)):
    # Logic to verify OTP
    # If verified, find or create patient
    # Return JWT token
    return {"message": "OTP verified", "token": "fake-jwt-token"}
