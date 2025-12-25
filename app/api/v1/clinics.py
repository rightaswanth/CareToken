from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import select
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List
from uuid import UUID

from app.db.session import get_session
from app.db.models import Tenant

router = APIRouter()

@router.post("/", response_model=Tenant)
async def create_clinic(clinic: Tenant, session: AsyncSession = Depends(get_session)):
    session.add(clinic)
    await session.commit()
    await session.refresh(clinic)
    return clinic

@router.get("/", response_model=List[Tenant])
async def read_clinics(
    city: str = None,
    skip: int = 0,
    limit: int = 100,
    session: AsyncSession = Depends(get_session)
):
    query = select(Tenant)
    if city:
        query = query.where(Tenant.city == city)
    query = query.offset(skip).limit(limit)
    result = await session.execute(query)
    return result.scalars().all()

@router.get("/cities", response_model=List[str])
async def get_cities():
    return ["Kochi", "Bangalore", "Mumbai", "Delhi", "Chennai", "Hyderabad", "Trivandrum", "Calicut"]

@router.get("/{clinic_id}", response_model=Tenant)
async def read_clinic(clinic_id: UUID, session: AsyncSession = Depends(get_session)):
    clinic = await session.get(Tenant, clinic_id)
    if not clinic:
        raise HTTPException(status_code=404, detail="Clinic not found")
    return clinic
