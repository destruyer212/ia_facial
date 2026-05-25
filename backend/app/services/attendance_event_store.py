from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta
from pathlib import Path

from app.core.config import settings
from app.schemas.attendance import AttendanceEvent, AttendanceEventCreate


class LocalAttendanceEventStore:
    """JSON storage for edge attendance events in the desktop MVP."""

    def __init__(self, path: Path | None = None) -> None:
        data_dir = settings.resolved_data_dir
        data_dir.mkdir(parents=True, exist_ok=True)
        self.path = path or data_dir / "attendance_events.json"

    def create(
        self,
        payload: AttendanceEventCreate,
        duplicate_window_seconds: int = 45,
    ) -> AttendanceEvent:
        payload = payload.model_copy(
            update={"captured_at": ensure_aware_utc(payload.captured_at)}
        )
        events = self._load()
        duplicate = self._is_duplicate(payload, events, duplicate_window_seconds)
        event = AttendanceEvent(
            **payload.model_dump(),
            event_id=new_event_id(),
            accepted=not duplicate,
            duplicate=duplicate,
            created_at=datetime.now(UTC),
        )
        events.append(event)
        self._save(events)
        return event

    def list(
        self,
        person_id: str | None = None,
        device_id: str | None = None,
        limit: int = 100,
    ) -> list[AttendanceEvent]:
        events = self._load()
        if person_id:
            events = [event for event in events if event.person_id == person_id]
        if device_id:
            events = [event for event in events if event.device_id == device_id]
        return events[-limit:]

    def _is_duplicate(
        self,
        payload: AttendanceEventCreate,
        events: list[AttendanceEvent],
        duplicate_window_seconds: int,
    ) -> bool:
        window = timedelta(seconds=duplicate_window_seconds)
        for event in reversed(events):
            if event.person_id != payload.person_id:
                continue
            if event.event_type != payload.event_type:
                continue
            if abs(payload.captured_at - event.captured_at) <= window:
                return True
        return False

    def _load(self) -> list[AttendanceEvent]:
        if not self.path.exists():
            return []
        payload = json.loads(self.path.read_text(encoding="utf-8"))
        return [AttendanceEvent(**item) for item in payload]

    def _save(self, events: list[AttendanceEvent]) -> None:
        payload = [event.model_dump(mode="json") for event in events]
        self.path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def new_event_id() -> str:
    timestamp = datetime.now(UTC).strftime("%Y%m%d%H%M%S%f")
    return f"ATT-{timestamp}"


def ensure_aware_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)
