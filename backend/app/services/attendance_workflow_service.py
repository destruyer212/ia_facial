from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Protocol

from app.schemas.attendance import AttendanceEvent, ExitPolicyResponse, SuggestEventResponse
from app.services.attendance_event_store import (
    LocalAttendanceEventStore,
    ensure_aware_utc,
    get_attendance_event_store,
)
from app.services.attendance_service import AttendanceService
from app.services.embedding_store import get_embedding_store


class AttendanceEventStore(Protocol):
    def list(
        self,
        person_id: str | None = None,
        device_id: str | None = None,
        limit: int = 100,
    ) -> list[AttendanceEvent]: ...


class AttendanceWorkflowService:
    """Sugiere entrada/salida y evita marcas duplicadas en el mismo turno."""

    def __init__(
        self,
        event_store: AttendanceEventStore | None = None,
        attendance_service: AttendanceService | None = None,
    ) -> None:
        self.event_store = event_store or get_attendance_event_store()
        self.attendance_service = attendance_service or AttendanceService()

    def suggest_next_event(
        self,
        person_id: str,
        at: datetime | None = None,
    ) -> SuggestEventResponse:
        moment = ensure_aware_utc(at or datetime.now(UTC))
        policy = self.attendance_service.get_policy()
        today_events = self._today_accepted_events(person_id, moment)
        employee_name = self._resolve_employee_name(person_id, today_events)
        shift_status = self._shift_status(today_events)
        suggested_type = self._suggest_event_type(shift_status)
        can_register, reason = self._can_register(
            employee_name=employee_name,
            shift_status=shift_status,
            suggested_type=suggested_type,
            today_events=today_events,
            moment=moment,
            policy=policy,
        )
        last_event = today_events[-1] if today_events else None
        return SuggestEventResponse(
            person_id=person_id,
            suggested_event_type=suggested_type,
            can_register=can_register,
            shift_status=shift_status,
            reason=reason,
            policy=policy,
            last_event_today=last_event,
        )

    def _today_accepted_events(self, person_id: str, moment: datetime) -> list[AttendanceEvent]:
        day = moment.date()
        events = self.event_store.list(person_id=person_id, limit=500)
        accepted = [event for event in events if event.accepted]
        today = [
            event
            for event in accepted
            if ensure_aware_utc(event.captured_at).date() == day
        ]
        today.sort(key=lambda event: ensure_aware_utc(event.captured_at))
        return today

    @staticmethod
    def _shift_status(today_events: list[AttendanceEvent]) -> str:
        if not today_events:
            return "outside"
        last = today_events[-1]
        if last.event_type == "check_in":
            return "inside"
        return "outside"

    @staticmethod
    def _suggest_event_type(shift_status: str) -> str:
        if shift_status == "inside":
            return "check_out"
        return "check_in"

    def _resolve_employee_name(
        self,
        person_id: str,
        today_events: list[AttendanceEvent],
    ) -> str:
        for event in reversed(today_events):
            if event.employee_name:
                return event.employee_name.strip()
        for face in get_embedding_store().list_public():
            if face.person_id == person_id and face.name:
                return face.name.strip()
        return person_id

    @staticmethod
    def _message(employee_name: str, text: str) -> str:
        return f"{employee_name}, {text[0].lower()}{text[1:]}" if text else employee_name

    def _can_register(
        self,
        *,
        employee_name: str,
        shift_status: str,
        suggested_type: str,
        today_events: list[AttendanceEvent],
        moment: datetime,
        policy: ExitPolicyResponse,
    ) -> tuple[bool, str]:
        if self._completed_cycle_today(today_events):
            return False, self._message(
                employee_name,
                "Ya registraste entrada y salida hoy. Turno completado.",
            )

        if suggested_type == "check_in":
            if shift_status == "inside":
                return False, self._message(
                    employee_name,
                    "Ya tienes entrada activa. Marca salida primero.",
                )
            return True, self._message(employee_name, "Puedes registrar entrada.")

        if shift_status != "inside":
            return False, self._message(
                employee_name,
                "Debes registrar entrada antes de marcar salida.",
            )

        if self._has_checkout_after_last_checkin(today_events):
            return False, self._message(
                employee_name,
                "La salida de este turno ya fue registrada.",
            )

        exit_cutoff = datetime.combine(
            moment.date(),
            policy.scheduled_exit_time,
            tzinfo=moment.tzinfo,
        )
        if moment < exit_cutoff - timedelta(hours=1):
            return True, self._message(employee_name, "Puedes registrar salida anticipada.")

        return True, self._message(employee_name, "Puedes registrar salida.")

    @staticmethod
    def _completed_cycle_today(today_events: list[AttendanceEvent]) -> bool:
        saw_check_in = False
        for event in today_events:
            if event.event_type == "check_in":
                saw_check_in = True
            if saw_check_in and event.event_type == "check_out":
                return True
        return False

    @staticmethod
    def _has_checkout_after_last_checkin(today_events: list[AttendanceEvent]) -> bool:
        last_check_in_index = -1
        for index, event in enumerate(today_events):
            if event.event_type == "check_in":
                last_check_in_index = index
        if last_check_in_index < 0:
            return False
        for event in today_events[last_check_in_index + 1 :]:
            if event.event_type == "check_out":
                return True
        return False
