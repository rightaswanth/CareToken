from datetime import date, datetime, timedelta
from typing import List, Optional
from uuid import UUID

from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import delete, func, select

from app.db.models import Appointment, Doctor, Schedule, Tenant
from app.schemas.schedule import ScheduleCreate, ScheduleUpdate
from app.schemas.doctor import WeeklySlotsResponse, DailySlots, CurrentTokenResponse, Slot

class DoctorService:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def create_doctor(self, tenant_id: UUID, doctor: Doctor) -> Doctor:
        # Verify tenant exists
        tenant = await self.session.get(Tenant, tenant_id)
        if not tenant:
            raise HTTPException(status_code=404, detail="Clinic not found")

        # Create Doctor profile
        doctor.tenant_id = tenant_id
        self.session.add(doctor)
        await self.session.commit()
        await self.session.refresh(doctor)
        return doctor

    async def get_doctors(self, tenant_id: UUID) -> List[Doctor]:
        query = select(Doctor).where(Doctor.tenant_id == tenant_id)
        result = await self.session.execute(query)
        return result.scalars().all()

    async def create_schedule(self, doctor_id: UUID, schedules: List[ScheduleCreate]) -> List[Schedule]:
        # Verify doctor exists
        doctor = await self.session.get(Doctor, doctor_id)
        if not doctor:
            raise HTTPException(status_code=404, detail="Doctor not found")

        # Group input schedules by day
        schedules_by_day = {}
        for s in schedules:
            if s.day_of_week not in schedules_by_day:
                schedules_by_day[s.day_of_week] = []
            schedules_by_day[s.day_of_week].append(s)

        new_schedules = []
        
        for day, day_schedules in schedules_by_day.items():
            # 1. Delete existing schedules for this day
            stmt = delete(Schedule).where(
                Schedule.doctor_id == doctor_id,
                Schedule.day_of_week == day
            )
            await self.session.execute(stmt)
            
            # 2. Add new schedules
            for schedule_data in day_schedules:
                schedule = Schedule(
                    doctor_id=doctor_id,
                    day_of_week=schedule_data.day_of_week,
                    start_time=schedule_data.start_time,
                    end_time=schedule_data.end_time
                )
                self.session.add(schedule)
                new_schedules.append(schedule)
        
        await self.session.commit()
        for schedule in new_schedules:
            await self.session.refresh(schedule)
            
        return new_schedules

    async def get_doctor_slots(self, doctor_id: UUID, start_date_str: str) -> WeeklySlotsResponse:
        try:
            start_date = datetime.strptime(start_date_str, "%Y-%m-%d").date()
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid date format. Use YYYY-MM-DD")

        # Fetch doctor to get duration
        doctor = await self.session.get(Doctor, doctor_id)
        if not doctor:
            raise HTTPException(status_code=404, detail="Doctor not found")

        daily_slots_list = []
        
        # Iterate for 7 days
        for i in range(7):
            current_date = start_date + timedelta(days=i)
            
            # Convert Python weekday (0=Mon, 6=Sun) to DB convention (0=Sun, 6=Sat)
            python_day = current_date.weekday()
            db_day = 0 if python_day == 6 else python_day + 1
            
            # Fetch schedule for this day
            stmt = select(Schedule).where(
                Schedule.doctor_id == doctor_id, 
                Schedule.day_of_week == db_day,
                Schedule.is_active == True
            )
            result = await self.session.execute(stmt)
            schedules = result.scalars().all()
            
            slots = []
            for schedule in schedules:
                current_time = datetime.combine(current_date, schedule.start_time)
                end_time = datetime.combine(current_date, schedule.end_time)
                
                slots.append(Slot(
                    start_time=current_time.isoformat(),
                    end_time=end_time.isoformat(),
                    schedule_id=schedule.id
                ))
            
            daily_slots_list.append(DailySlots(date=current_date.isoformat(), slots=slots))

        return WeeklySlotsResponse(
            doctor_id=doctor_id,
            start_date=start_date_str,
            end_date=(start_date + timedelta(days=6)).isoformat(),
            daily_slots=daily_slots_list
        )

    async def deactivate_schedule(self, schedule_id: UUID) -> dict:
        schedule = await self.session.get(Schedule, schedule_id)
        if not schedule:
            raise HTTPException(status_code=404, detail="Schedule not found")
        
        schedule.is_active = False
        self.session.add(schedule)
        await self.session.commit()
        await self.session.refresh(schedule)
        return {"message": "Schedule deactivated successfully"}

    async def update_schedule(self, schedule_id: UUID, schedule_update: ScheduleUpdate) -> Schedule:
        schedule = await self.session.get(Schedule, schedule_id)
        if not schedule:
            raise HTTPException(status_code=404, detail="Schedule not found")

        update_data = schedule_update.model_dump(exclude_unset=True)
        for key, value in update_data.items():
            setattr(schedule, key, value)

        self.session.add(schedule)
        await self.session.commit()
        await self.session.refresh(schedule)
        return schedule

    async def get_current_token(self, doctor_id: UUID) -> CurrentTokenResponse:
        # Fetch doctor to get duration
        doctor = await self.session.get(Doctor, doctor_id)
        if not doctor:
            raise HTTPException(status_code=404, detail="Doctor not found")

        # Find the current consulting appointment
        stmt = select(Appointment).where(
            Appointment.doctor_id == doctor_id,
            Appointment.state == "consulting"
        ).order_by(Appointment.started_at.desc()).limit(1)
        
        result = await self.session.execute(stmt)
        current_appt = result.scalars().first()
        
        current_token = current_appt.token_number if current_appt else 0
        
        # Count waiting people
        # Note: func.count() usually needs to be selected specifically or used with scalar()
        # But here we can use select(func.count()) and execute it.
        count_stmt = select(func.count()).where(
            Appointment.doctor_id == doctor_id,
            Appointment.state == "waiting",
            Appointment.scheduled_start >= datetime.combine(date.today(), datetime.min.time())
        )
        # We are not using the count yet in the return, but let's keep it if we need it later.
        
        return CurrentTokenResponse(
            current_token=current_token,
            doctor_id=doctor_id,
            estimated_wait_minutes_per_patient=doctor.consult_duration_minutes
        )

    async def update_consulting_status(self, doctor_id: UUID, is_consulting: bool) -> Doctor:
        doctor = await self.session.get(Doctor, doctor_id)
        if not doctor:
            raise HTTPException(status_code=404, detail="Doctor not found")
        
        doctor.is_consulting = is_consulting
        self.session.add(doctor)
        await self.session.commit()
        await self.session.refresh(doctor)
        return doctor
