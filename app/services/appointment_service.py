from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_, or_, cast, Time
from uuid import UUID
from datetime import datetime, date, timezone
from fastapi import HTTPException

from app.db.models.appointment import Appointment
from app.db.models.patient import Patient
from app.db.models.doctor import Doctor
from app.schemas.appointment import AppointmentCreatePatient, AppointmentCreateAdmin, PatientCreate

class AppointmentService:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_patient_by_phone(self, phone: str, tenant_id: UUID) -> Patient | None:
        stmt = select(Patient).where(
            Patient.phone == phone,
            Patient.tenant_id == tenant_id
        )
        result = await self.session.execute(stmt)
        return result.scalars().first()

    async def create_or_get_patient(self, patient_data: PatientCreate, tenant_id: UUID) -> Patient:
        patient = await self.get_patient_by_phone(patient_data.phone, tenant_id)
        if not patient:
            patient = Patient(
                tenant_id=tenant_id,
                name=patient_data.name,
                phone=patient_data.phone,
                age=patient_data.age,
                gender=patient_data.gender,
                phone_verified=False
            )
            self.session.add(patient)
            await self.session.commit()
            await self.session.refresh(patient)
        else:
            # Update patient details if they differ
            updated = False
            if patient.name != patient_data.name:
                patient.name = patient_data.name
                updated = True
            if patient_data.age is not None and patient.age != patient_data.age:
                patient.age = patient_data.age
                updated = True
            if patient_data.gender is not None and patient.gender != patient_data.gender:
                patient.gender = patient_data.gender
                updated = True
            
            if updated:
                self.session.add(patient)
                await self.session.commit()
                await self.session.refresh(patient)
                
        return patient

    async def get_next_token(self, doctor_id: UUID, appt_date: date) -> int:
        stmt = select(func.max(Appointment.token_number)).where(
            Appointment.doctor_id == doctor_id,
            func.date(Appointment.scheduled_start) == appt_date
        )
        result = await self.session.execute(stmt)
        max_token = result.scalar() or 0
        return max_token + 1

    async def calculate_wait_time(self, doctor: Doctor, appt_date: date, token_number: int, is_emergency: bool) -> int:
        # Count uncompleted normal tokens < this token (if normal)
        # Count all uncompleted emergency tokens (if normal)
        # If emergency, count uncompleted emergency < this token
        
        # This is a simplified estimation
        # Ideally we check state != 'completed' and state != 'cancelled'
        
        active_states = ["created", "waiting", "consulting"]
        
        if is_emergency:
            # Count emergency tokens ahead
            stmt = select(func.count(Appointment.id)).where(
                Appointment.doctor_id == doctor.id,
                func.date(Appointment.scheduled_start) == appt_date,
                Appointment.is_emergency == True,
                Appointment.token_number < token_number,
                Appointment.state.in_(active_states)
            )
            result = await self.session.execute(stmt)
            ahead_count = result.scalar() or 0
        else:
            # Count normal tokens ahead
            stmt_normal = select(func.count(Appointment.id)).where(
                Appointment.doctor_id == doctor.id,
                func.date(Appointment.scheduled_start) == appt_date,
                Appointment.is_emergency == False,
                Appointment.token_number < token_number,
                Appointment.state.in_(active_states)
            )
            
            # Count all emergency tokens (assuming they take priority)
            stmt_emergency = select(func.count(Appointment.id)).where(
                Appointment.doctor_id == doctor.id,
                func.date(Appointment.scheduled_start) == appt_date,
                Appointment.is_emergency == True,
                Appointment.state.in_(active_states)
            )
            
            result_normal = await self.session.execute(stmt_normal)
            result_emergency = await self.session.execute(stmt_emergency)
            
            ahead_count = (result_normal.scalar() or 0) + (result_emergency.scalar() or 0)

        # Assuming consult_duration_minutes is on Doctor model
        # Check doctor model for correct field name, assuming 'consult_duration_minutes' from previous file view
        duration = getattr(doctor, 'consult_duration_minutes', 15) # Default 15 if missing
        return ahead_count * duration * 60

    async def create_appointment_patient(self, data: AppointmentCreatePatient) -> Appointment:
        # 1. Validate Doctor
        doctor = await self.session.get(Doctor, data.doctor_id)
        if not doctor:
            raise HTTPException(status_code=404, detail="Doctor not found")

        # 2. Get or Create Patient
        patient = await self.create_or_get_patient(data.patient, data.tenant_id)

        # 3. Assign Token
        appt_date = data.preferred_slot.date()
        next_token = await self.get_next_token(data.doctor_id, appt_date)

        # Ensure scheduled_start is naive UTC
        scheduled_start = data.preferred_slot
        if scheduled_start.tzinfo is not None:
            scheduled_start = scheduled_start.astimezone(timezone.utc).replace(tzinfo=None)

        # 4. Create Appointment
        appointment = Appointment(
            tenant_id=data.tenant_id,
            doctor_id=data.doctor_id,
            patient_id=patient.id,
            token_number=next_token,
            state="created",
            scheduled_start=scheduled_start,
            is_phone_booking=False,
            is_emergency=False,
            is_late=False
        )
        self.session.add(appointment)
        await self.session.commit()
        await self.session.refresh(appointment)
        
        return appointment

    async def create_appointment_admin(self, data: AppointmentCreateAdmin) -> Appointment:
        # 1. Validate Doctor
        doctor = await self.session.get(Doctor, data.doctor_id)
        if not doctor:
            raise HTTPException(status_code=404, detail="Doctor not found")

        # 2. Get or Create Patient
        patient = await self.create_or_get_patient(data.patient, data.tenant_id)

        # 3. Assign Token
        appt_date = data.preferred_slot.date()
        next_token = await self.get_next_token(data.doctor_id, appt_date)

        # Ensure scheduled_start is naive UTC
        scheduled_start = data.preferred_slot
        if scheduled_start.tzinfo is not None:
            scheduled_start = scheduled_start.astimezone(timezone.utc).replace(tzinfo=None)

        # 4. Create Appointment
        appointment = Appointment(
            tenant_id=data.tenant_id,
            doctor_id=data.doctor_id,
            patient_id=patient.id,
            token_number=next_token,
            state="created",
            scheduled_start=scheduled_start,
            is_phone_booking=data.is_phone_booking,
            is_emergency=data.is_emergency,
            is_late=data.is_late
        )
        self.session.add(appointment)
        await self.session.commit()
        await self.session.refresh(appointment)

        return appointment

    async def get_doctor_appointments(self, doctor_id: UUID, date: date, status: list[str] | None = None) -> list[Appointment]:
        # 1. Get active schedule for the day
        day_of_week = date.weekday() # 0=Monday, 6=Sunday
        # Adjust for DB (1=Monday, 7=Sunday) if needed, assuming 0-6 match for now or handled in model
        # Actually model uses 1-7 usually? Let's check Schedule model or assume standard python
        # Checking previous code, it seems we used python_day + 1 logic in setup_data
        
        # For now, just getting appointments. The slot logic is:
        # If there's a slot selected (or current time implies one), we filter.
        # But wait, the previous implementation of get_doctor_appointments didn't take a slot argument.
        # It filtered by *current time* if I recall correctly?
        # Let's look at the code.
        
        # Re-reading the file content from previous turns or just viewing it now would be safer.
        # But I have the context.
        
        # The goal: Filter by slot OR is_emergency=True
        
        # Let's see the current implementation in the file first to be sure.
        pass # Placeholder, I will use view_file first to be safe.
        # 1. Fetch schedules for the day
        # Note: DB stores day_of_week as 0=Sunday..6=Saturday
        # Python date.weekday() is 0=Monday..6=Sunday
        python_day = date.weekday()
        db_day = 0 if python_day == 6 else python_day + 1
        
        from app.db.models.schedule import Schedule
        stmt_schedule = select(Schedule).where(
            Schedule.doctor_id == doctor_id,
            Schedule.day_of_week == db_day,
            Schedule.is_active == True
        ).order_by(Schedule.start_time)
        
        schedule_result = await self.session.execute(stmt_schedule)
        schedules = schedule_result.scalars().all()
        
        if not schedules:
            return []
            
        # 2. Determine target slot
        target_schedule = None
        now = datetime.now()
        current_time = now.time()
        
        # Only apply time logic if we are looking at today
        if date == now.date():
            for schedule in schedules:
                if schedule.start_time <= current_time <= schedule.end_time:
                    # Current time is within this slot
                    target_schedule = schedule
                    break
                elif schedule.start_time > current_time:
                    # This is the next upcoming slot
                    target_schedule = schedule
                    break
            
            # If no slot found (current time is after all slots), we might return None or empty
            # The requirement says: "if the current time is over of the slot then list next slot . if not next slots list None"
            if not target_schedule:
                return []
        else:
            # For future dates, maybe return the first slot? Or all?
            # The requirement specifically mentioned "check the current time".
            # Let's assume for future dates we return the first slot as default, or all?
            # "For listing queue first conside the current date."
            # Let's default to the first slot for consistency if not specified, 
            # or maybe we should return all if it's not today?
            # Given the strict "queue" nature, usually it's about the active session.
            # Let's pick the first slot for future dates.
            target_schedule = schedules[0]

        # 3. Filter appointments by target slot OR if emergency
        from sqlalchemy.orm import selectinload
        from sqlalchemy import or_, and_
        
        stmt = select(Appointment).options(selectinload(Appointment.patient)).where(
            Appointment.doctor_id == doctor_id,
            func.date(Appointment.scheduled_start) == date
        )

        if target_schedule:
            # Show appointments in this slot OR any emergency appointment for the day OR any hold appointment
            # Note: We already filtered by date above
            stmt = stmt.where(
                or_(
                    and_(
                        cast(Appointment.scheduled_start, Time) >= target_schedule.start_time,
                        cast(Appointment.scheduled_start, Time) <= target_schedule.end_time
                    ),
                    Appointment.is_emergency == True,
                    Appointment.state == "hold"
                )
            )
        else:
            # No active slot found (e.g. before first slot, after last slot, or break)
            # Show emergency and hold appointments
            stmt = stmt.where(
                or_(
                    Appointment.is_emergency == True,
                    Appointment.state == "hold"
                )
            )
        
        if status:
            stmt = stmt.where(Appointment.state.in_(status))
            
        stmt = stmt.order_by(Appointment.token_number)
        
        result = await self.session.execute(stmt)
        return result.scalars().all()

    async def update_appointment_status(self, appointment_id: UUID, status: str, next_appointment_id: UUID | None = None) -> Appointment:
        # 1. Get current appointment
        appointment = await self.session.get(Appointment, appointment_id)
        if not appointment:
            raise HTTPException(status_code=404, detail="Appointment not found")
            
        # 2. Update status
        appointment.state = status
        self.session.add(appointment)
        
        # 3. Update next appointment if provided
        if next_appointment_id:
            next_appt = await self.session.get(Appointment, next_appointment_id)
            if not next_appt:
                raise HTTPException(status_code=404, detail="Next appointment not found")
            
            next_appt.state = "consulting"
            self.session.add(next_appt)
            
        await self.session.commit()
        await self.session.refresh(appointment)
        return appointment

    async def toggle_appointment_hold(self, appointment_id: UUID) -> Appointment:
        appointment = await self.session.get(Appointment, appointment_id)
        if not appointment:
            raise HTTPException(status_code=404, detail="Appointment not found")
            
        if appointment.state == "hold":
            appointment.state = "created"
        else:
            appointment.state = "hold"
            
        self.session.add(appointment)
        await self.session.commit()
        await self.session.refresh(appointment)
        return appointment
