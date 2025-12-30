from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List
from uuid import UUID

from app.db.session import get_session
from app.db.models import Tenant, User
from app.services.clinic_service import ClinicService
from app.schemas.clinic import ClinicCreate, ClinicCreatedResponse, AdminCreatedResponse, ClinicResponse
from app.api.deps import get_current_user

router = APIRouter()

@router.post("/", response_model=ClinicCreatedResponse)
async def create_clinic(
    clinic_data: ClinicCreate, 
    session: AsyncSession = Depends(get_session)
):
    service = ClinicService(session)
    return await service.create_clinic(clinic_data)

@router.post("/{tenant_id}/admins", response_model=AdminCreatedResponse)
async def create_admin(
    tenant_id: UUID,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session)
):
    service = ClinicService(session)
    return await service.create_admin(tenant_id, current_user)

@router.get("/", response_model=List[Tenant])
async def read_clinics(
    city: str = None,
    skip: int = 0,
    limit: int = 100,
    session: AsyncSession = Depends(get_session)
):
    service = ClinicService(session)
    return await service.get_clinics(city, skip, limit)

@router.get("/cities", response_model=List[str])
async def get_cities():
    return ["Kochi", "Bangalore", "Mumbai", "Delhi", "Chennai", "Hyderabad", "Trivandrum", "Calicut"]

@router.get("/{clinic_id}", response_model=Tenant)
async def read_clinic(clinic_id: UUID, session: AsyncSession = Depends(get_session)):
    service = ClinicService(session)
    return await service.get_clinic(clinic_id)
