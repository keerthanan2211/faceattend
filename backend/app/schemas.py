from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class TechnicianIn(BaseModel):
    employee_code: str = Field(min_length=2, max_length=20, pattern=r"^[A-Za-z0-9-]+$")
    name: str = Field(min_length=2, max_length=100)
    trade: str = Field(min_length=2, max_length=50)
    phone: str = Field(pattern=r"^[6-9]\d{9}$")


class TechnicianUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=2, max_length=100)
    trade: str | None = Field(default=None, min_length=2, max_length=50)
    phone: str | None = Field(default=None, pattern=r"^[6-9]\d{9}$")
    active: bool | None = None


class TechnicianOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    employee_code: str
    name: str
    trade: str
    phone: str
    active: bool
    face_count: int = 0
    created_at: datetime


class ChallengeOut(BaseModel):
    token: str
    direction: str  # "left" | "right", from the technician's point of view
    expires_at: datetime


class CheckInOut(BaseModel):
    status: str  # "checked-in" | "checked-out" | "already-recorded"
    technician: TechnicianOut
    time: datetime
    score: float


class AttendanceOut(BaseModel):
    id: int
    kind: str
    site: str
    score: float
    created_at: datetime
    technician_id: int
    technician_name: str
    employee_code: str
