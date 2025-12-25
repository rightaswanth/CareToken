from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List
from uuid import UUID

from app.db.session import get_session
from app.db.models import Doctor, Schedule, Tenant, User, Appointment

router = APIRouter()

@router.post("/{tenant_id}/doctors", response_model=Doctor)
async def create_doctor(
    tenant_id: UUID,
    doctor: Doctor,
    user_data: User,
    session: AsyncSession = Depends(get_session)
):
    # Verify tenant exists
    tenant = await session.get(Tenant, tenant_id)
    if not tenant:
        raise HTTPException(status_code=404, detail="Clinic not found")

    # Create User for the doctor first
    user_data.tenant_id = tenant_id
    user_data.role = "doctor"
    session.add(user_data)
    await session.commit()
    await session.refresh(user_data)

    # Create Doctor profile
    doctor.tenant_id = tenant_id
    doctor.user_id = user_data.id
    session.add(doctor)
    await session.commit()
    await session.refresh(doctor)
    return doctor

@router.get("/{tenant_id}/doctors", response_model=List[Doctor])
async def read_doctors(
    tenant_id: UUID,
    session: AsyncSession = Depends(get_session)
):
    query = select(Doctor).where(Doctor.tenant_id == tenant_id)
    result = await session.execute(query)
    return result.scalars().all()

from datetime import datetime, timedelta, date

@router.get("/{doctor_id}/slots")
async def get_doctor_slots(
    doctor_id: UUID,
    date: str, # YYYY-MM-DD
    session: AsyncSession = Depends(get_session)
):
    try:
        query_date = datetime.strptime(date, "%Y-%m-%d").date()
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid date format. Use YYYY-MM-DD")

    # Convert Python weekday (0=Mon, 6=Sun) to DB convention (0=Sun, 6=Sat) if needed
    # Assuming DB uses 0=Sunday based on previous comment
    python_day = query_date.weekday()
    db_day = 0 if python_day == 6 else python_day + 1

    # Fetch doctor to get duration
    doctor = await session.get(Doctor, doctor_id)
    if not doctor:
        raise HTTPException(status_code=404, detail="Doctor not found")

    # Fetch schedule
    stmt = select(Schedule).where(
        Schedule.doctor_id == doctor_id, 
        Schedule.day_of_week == db_day,
        Schedule.is_active == True
    )
    result = await session.execute(stmt)
    schedules = result.scalars().all()
    
    slots = []
    for schedule in schedules:
        current_time = datetime.combine(query_date, schedule.start_time)
        end_time = datetime.combine(query_date, schedule.end_time)
        
        while current_time + timedelta(minutes=doctor.consult_duration_minutes) <= end_time:
            slots.append(current_time.isoformat())
            current_time += timedelta(minutes=doctor.consult_duration_minutes)

    # TODO: Filter out booked slots by querying Appointment table

    return {
        "doctor_id": doctor_id,
        "date": date,
        "slots": slots
    }

@router.get("/{doctor_id}/current")
async def get_current_token(
    doctor_id: UUID,
    session: AsyncSession = Depends(get_session)
):
    # Fetch doctor to get duration
    doctor = await session.get(Doctor, doctor_id)
    if not doctor:
        raise HTTPException(status_code=404, detail="Doctor not found")

    # Find the current consulting appointment
    # Assuming 'consulting' state means currently with doctor
    # If no one is consulting, find the last completed one to guess next? 
    # Or find the first 'waiting' one?
    # Let's return the token currently being served (consulting) or the last one served.
    
    # For now, let's just return the latest token number issued for today from Counters if we had it, 
    # or query appointments.
    
    # Let's find the appointment that is currently 'consulting'
    stmt = select(Appointment).where(
        Appointment.doctor_id == doctor_id,
        Appointment.state == "consulting"
    ).order_by(Appointment.started_at.desc()).limit(1)
    
    result = await session.execute(stmt)
    current_appt = result.scalars().first()
    
    current_token = current_appt.token_number if current_appt else 0
    
    # Calculate ETA for the NEXT token (just a rough estimate)
    # ETA = (Number of people waiting) * duration
    
    # Count waiting people
    count_stmt = select(func.count()).where(
        Appointment.doctor_id == doctor_id,
        Appointment.state == "waiting",
        Appointment.scheduled_start >= datetime.combine(date.today(), datetime.min.time())
    )
    # Need to import func
    # For now, simple placeholder return
    
    return {
        "current_token": current_token,
        "doctor_id": doctor_id,
        "estimated_wait_minutes_per_patient": doctor.consult_duration_minutes
    }
