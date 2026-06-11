from __future__ import annotations

import json
import math
from datetime import UTC, datetime, time, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from app.core.config import settings
from app.schemas.face import StoredFacePublic
from app.schemas.schedule import (
    EmployeeShiftPublic,
    ScheduleOverviewResponse,
    ShiftAssignment,
    ShiftEvaluation,
    WorkShift,
    WorkShiftUpdate,
)


class ScheduleService:
    def __init__(self, path: Path | None = None) -> None:
        data_dir = settings.resolved_data_dir
        data_dir.mkdir(parents=True, exist_ok=True)
        self.path = path or data_dir / "work_schedules.json"

    def overview(self) -> ScheduleOverviewResponse:
        shifts = self.list_shifts()
        assignments = self.list_assignments()
        employees = self.employees_with_shift()
        grouped: dict[str, list[EmployeeShiftPublic]] = {shift.code: [] for shift in shifts}
        grouped["SIN_TURNO"] = []
        for employee in employees:
            key = employee.shift_code if employee.shift_code in grouped else "SIN_TURNO"
            grouped[key].append(employee)
        return ScheduleOverviewResponse(
            shifts=shifts,
            assignments=assignments,
            employees=employees,
            employees_by_shift=grouped,
        )

    def list_shifts(self, include_inactive: bool = True) -> list[WorkShift]:
        shifts = [WorkShift(**item) for item in self._load_state()["shifts"]]
        if not include_inactive:
            shifts = [shift for shift in shifts if shift.is_active]
        return sorted(shifts, key=lambda item: item.start_time)

    def get_shift(self, shift_code: str) -> WorkShift | None:
        shift_code = shift_code.strip().upper()
        return next((shift for shift in self.list_shifts() if shift.code == shift_code), None)

    def update_shift(self, shift_code: str, payload: WorkShiftUpdate) -> WorkShift:
        shift_code = shift_code.strip().upper()
        state = self._load_state()
        shifts = [WorkShift(**item) for item in state["shifts"]]
        updates = payload.model_dump(exclude_unset=True)
        for index, shift in enumerate(shifts):
            if shift.code != shift_code:
                continue
            updated = shift.model_copy(update=updates)
            shifts[index] = updated
            state["shifts"] = [item.model_dump(mode="json") for item in shifts]
            self._save_state(state)
            return updated
        raise LookupError(f"No existe turno '{shift_code}'.")

    def list_assignments(self) -> list[ShiftAssignment]:
        return [
            ShiftAssignment(**item)
            for item in sorted(self._load_state()["assignments"], key=lambda row: row["person_id"])
        ]

    def assign_shift(self, person_id: str, shift_code: str) -> ShiftAssignment:
        person_id = person_id.strip()
        shift_code = shift_code.strip().upper()
        if not person_id:
            raise ValueError("person_id es obligatorio.")
        shift = self.get_shift(shift_code)
        if shift is None or not shift.is_active:
            raise ValueError(f"Turno '{shift_code}' no existe o esta inactivo.")
        state = self._load_state()
        assignments = [
            item for item in state["assignments"] if item["person_id"] != person_id
        ]
        assignment = ShiftAssignment(
            person_id=person_id,
            shift_code=shift_code,
            assigned_at=datetime.now(UTC),
        )
        assignments.append(assignment.model_dump(mode="json"))
        state["assignments"] = assignments
        self._save_state(state)
        return assignment

    def remove_assignment(self, person_id: str) -> None:
        person_id = person_id.strip()
        state = self._load_state()
        state["assignments"] = [
            item for item in state["assignments"] if item["person_id"] != person_id
        ]
        self._save_state(state)

    def assignment_for(self, person_id: str) -> ShiftAssignment | None:
        person_id = person_id.strip()
        return next(
            (assignment for assignment in self.list_assignments() if assignment.person_id == person_id),
            None,
        )

    def shift_for_person(self, person_id: str) -> WorkShift | None:
        assignment = self.assignment_for(person_id)
        if assignment is None:
            return None
        return self.get_shift(assignment.shift_code)

    def evaluate_event(
        self,
        *,
        person_id: str,
        event_type: str,
        captured_at: datetime,
    ) -> ShiftEvaluation:
        captured_at = ensure_aware_utc(captured_at)
        shift = self.shift_for_person(person_id)
        if shift is None:
            return ShiftEvaluation(
                person_id=person_id,
                event_type=event_type,
                captured_at=captured_at,
            )

        local_dt = captured_at.astimezone(local_zone())
        start_dt = datetime.combine(local_dt.date(), shift.start_time, tzinfo=local_dt.tzinfo)
        exit_dt = datetime.combine(local_dt.date(), shift.end_time, tzinfo=local_dt.tzinfo)
        tolerance_end = start_dt + timedelta(minutes=shift.tolerance_minutes)
        tardy_from = tolerance_end + timedelta(minutes=1)

        status = "normal"
        label = "Normal"
        minutes_late = 0
        minutes_early = 0

        if event_type == "check_in":
            if local_dt >= tardy_from:
                status = "late"
                label = "Tardanza"
                minutes_late = max(1, math.ceil((local_dt - tolerance_end).total_seconds() / 60))
            else:
                status = "on_time"
                label = "Correcto"
        elif event_type == "check_out":
            if local_dt < exit_dt:
                status = "early_exit"
                label = "Salida anticipada"
                minutes_early = max(1, math.ceil((exit_dt - local_dt).total_seconds() / 60))
            else:
                status = "normal"
                label = "Normal"

        return ShiftEvaluation(
            person_id=person_id,
            event_type=event_type,
            captured_at=captured_at,
            shift_code=shift.code,
            shift_name=shift.name,
            scheduled_start_time=shift.start_time,
            scheduled_exit_time=shift.end_time,
            tolerance_minutes=shift.tolerance_minutes,
            status=status,
            label=label,
            minutes_late=minutes_late,
            minutes_early=minutes_early,
        )

    def enrich_event(self, event):
        evaluation = self.evaluate_event(
            person_id=event.person_id,
            event_type=event.event_type,
            captured_at=event.captured_at,
        )
        return event.model_copy(
            update={
                "shift_code": evaluation.shift_code,
                "shift_name": evaluation.shift_name,
                "scheduled_start_time": evaluation.scheduled_start_time,
                "scheduled_exit_time": evaluation.scheduled_exit_time,
                "tolerance_minutes": evaluation.tolerance_minutes,
                "work_status": evaluation.status,
                "work_status_label": evaluation.label,
                "minutes_late": evaluation.minutes_late,
                "minutes_early": evaluation.minutes_early,
            }
        )

    def enrich_faces(self, faces: list[StoredFacePublic]) -> list[StoredFacePublic]:
        assignments = {assignment.person_id: assignment for assignment in self.list_assignments()}
        shifts = {shift.code: shift for shift in self.list_shifts()}
        enriched: list[StoredFacePublic] = []
        for face in faces:
            assignment = assignments.get(face.person_id)
            shift = shifts.get(assignment.shift_code) if assignment else None
            enriched.append(
                face.model_copy(
                    update={
                        "shift_code": shift.code if shift else None,
                        "shift_name": shift.name if shift else None,
                        "schedule_label": schedule_label(shift) if shift else None,
                    }
                )
            )
        return enriched

    def employees_with_shift(self) -> list[EmployeeShiftPublic]:
        from app.services.embedding_store import get_embedding_store

        faces = self.enrich_faces(get_embedding_store().list_public())
        return [
            EmployeeShiftPublic(
                person_id=face.person_id,
                employee_code=face.employee_code or face.person_id,
                name=face.name,
                area_name=face.area_name,
                position_name=face.position_name,
                shift_code=face.shift_code,
                shift_name=face.shift_name,
                schedule_label=face.schedule_label,
                is_active=face.is_active,
            )
            for face in faces
        ]

    def _load_state(self) -> dict:
        defaults = self._default_state()
        if not self.path.exists():
            self._save_state(defaults)
            return defaults
        try:
            state = json.loads(self.path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            state = {}
        return {
            "shifts": state.get("shifts") or defaults["shifts"],
            "assignments": state.get("assignments") or [],
        }

    def _save_state(self, state: dict) -> None:
        self.path.write_text(json.dumps(state, indent=2, ensure_ascii=False), encoding="utf-8")

    @staticmethod
    def _default_state() -> dict:
        return {
            "shifts": [
                WorkShift(
                    code="TM",
                    name="Turno Manana",
                    start_time=time.fromisoformat("08:00"),
                    end_time=time.fromisoformat("16:00"),
                    work_hours=8,
                    tolerance_minutes=10,
                    is_active=True,
                ).model_dump(mode="json"),
                WorkShift(
                    code="TT",
                    name="Turno Tarde",
                    start_time=time.fromisoformat("14:00"),
                    end_time=time.fromisoformat("22:00"),
                    work_hours=8,
                    tolerance_minutes=10,
                    is_active=True,
                ).model_dump(mode="json"),
            ],
            "assignments": [],
        }


def schedule_label(shift: WorkShift | None) -> str | None:
    if shift is None:
        return None
    return f"{format_hhmm(shift.start_time)} - {format_hhmm(shift.end_time)}"


def format_hhmm(value: time) -> str:
    return value.strftime("%H:%M")


def ensure_aware_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)


def local_zone():
    try:
        return ZoneInfo("America/Lima")
    except ZoneInfoNotFoundError:
        return UTC


_schedule_service: ScheduleService | None = None


def get_schedule_service() -> ScheduleService:
    global _schedule_service
    if _schedule_service is None:
        _schedule_service = ScheduleService()
    return _schedule_service
