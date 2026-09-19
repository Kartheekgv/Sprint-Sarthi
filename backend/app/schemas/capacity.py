from datetime import date

from pydantic import BaseModel, ConfigDict, Field


class CapacitySnapshot(BaseModel):
    model_config = ConfigDict(extra="forbid")

    member_id: str
    sprint_id: str
    period_start: date
    period_end: date
    working_days: int = Field(ge=0)
    leave_days: int = Field(ge=0)
    holiday_days: int = Field(ge=0)
    allocation_percent: float = Field(ge=0, le=100)
    available_hours: float = Field(ge=0)
    source: str = "verified planning data"