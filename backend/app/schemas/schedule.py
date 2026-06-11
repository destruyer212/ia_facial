from datetime import datetime, time

from pydantic import BaseModel, Field


class WorkShift(BaseModel):
    code: str
    name: str
    start_time: time
    end_time: time
    work_hours: int = 8
    tolerance_minutes: int = Field(default=10, ge=0, le=240)
    is_active: bool = True


class WorkShiftUpdate(BaseModel):
    name: str | None = None
    start_time: time | None = None
    end_time: time | None = None
    work_hours: int | None = Field(default=None, ge=1, le=24)
    tolerance_minutes: int | None = Field(default=None, ge=0, le=240)
    is_active: bool | None = None


class ShiftAssignment(BaseModel):
    person_id: str
    shift_code: str
    assigned_at: datetime


class ShiftAssignmentRequest(BaseModel):
    shift_code: str


class EmployeeShiftPublic(BaseModel):
    person_id: str
    employee_code: str | None = None
    name: str
    area_name: str | None = None
    position_name: str | None = None
    shift_code: str | None = None
    shift_name: str | None = None
    schedule_label: str | None = None
    is_active: bool = True


class ShiftEvaluation(BaseModel):
    person_id: str
    event_type: str
    captured_at: datetime
    shift_code: str | None = None
    shift_name: str | None = None
    scheduled_start_time: time | None = None
    scheduled_exit_time: time | None = None
    tolerance_minutes: int | None = None
    status: str = "unassigned"
    label: str = "Sin turno"
    minutes_late: int = 0
    minutes_early: int = 0


class ScheduleOverviewResponse(BaseModel):
    shifts: list[WorkShift]
    assignments: list[ShiftAssignment]
    employees: list[EmployeeShiftPublic]
    employees_by_shift: dict[str, list[EmployeeShiftPublic]]


class ShiftResponse(BaseModel):
    shift: WorkShift
    message: str


class ShiftAssignmentResponse(BaseModel):
    assignment: ShiftAssignment
    message: str
