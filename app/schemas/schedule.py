from pydantic import BaseModel
from datetime import time

class ScheduleCreate(BaseModel):
    day_of_week: int
    start_time: time
    end_time: time
