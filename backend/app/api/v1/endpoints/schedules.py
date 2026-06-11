from fastapi import APIRouter, HTTPException

from app.schemas.schedule import (
    ScheduleOverviewResponse,
    ShiftAssignmentRequest,
    ShiftAssignmentResponse,
    ShiftResponse,
    WorkShiftUpdate,
)
from app.services.schedule_service import get_schedule_service

router = APIRouter()
schedule_service = get_schedule_service()


@router.get("/overview", response_model=ScheduleOverviewResponse)
def get_schedule_overview() -> ScheduleOverviewResponse:
    return schedule_service.overview()


@router.patch("/shifts/{shift_code}", response_model=ShiftResponse)
def update_shift(shift_code: str, payload: WorkShiftUpdate) -> ShiftResponse:
    try:
        shift = schedule_service.update_shift(shift_code, payload)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return ShiftResponse(shift=shift, message=f"Turno {shift.code} actualizado.")


@router.put("/assignments/{person_id}", response_model=ShiftAssignmentResponse)
def assign_shift(
    person_id: str,
    payload: ShiftAssignmentRequest,
) -> ShiftAssignmentResponse:
    try:
        assignment = schedule_service.assign_shift(person_id, payload.shift_code)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return ShiftAssignmentResponse(
        assignment=assignment,
        message=f"Turno {assignment.shift_code} asignado.",
    )
