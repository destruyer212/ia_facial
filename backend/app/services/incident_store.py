from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path

from app.core.config import settings
from app.schemas.attendance import AttendanceIncident


class LocalIncidentStore:
    """JSON storage for attendance incidents in the desktop MVP."""

    def __init__(self, path: Path | None = None) -> None:
        data_dir = settings.resolved_data_dir
        data_dir.mkdir(parents=True, exist_ok=True)
        self.path = path or data_dir / "attendance_incidents.json"

    def save(self, incident: AttendanceIncident) -> AttendanceIncident:
        incidents = self._load()
        incidents.append(incident)
        self._save(incidents)
        return incident

    def list(self, person_id: str | None = None, limit: int = 50) -> list[AttendanceIncident]:
        incidents = self._load()
        if person_id:
            incidents = [incident for incident in incidents if incident.person_id == person_id]
        return incidents[-limit:]

    def _load(self) -> list[AttendanceIncident]:
        if not self.path.exists():
            return []
        payload = json.loads(self.path.read_text(encoding="utf-8"))
        return [AttendanceIncident(**item) for item in payload]

    def _save(self, incidents: list[AttendanceIncident]) -> None:
        payload = [incident.model_dump(mode="json") for incident in incidents]
        self.path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def new_incident_id() -> str:
    timestamp = datetime.now(UTC).strftime("%Y%m%d%H%M%S%f")
    return f"INC-{timestamp}"
