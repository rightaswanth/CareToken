from pydantic import BaseModel
from datetime import time
from typing import Optional

class ScheduleCreate(BaseModel):
    day_of_week: int
    start_time: time
    end_time: time

class ScheduleUpdate(BaseModel):
    day_of_week: Optional[int] = None
    start_time: Optional[time] = None
    end_time: Optional[time] = None
    is_active: Optional[bool] = None
