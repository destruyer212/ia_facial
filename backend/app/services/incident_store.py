from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path

from app.core.config import settings
from app.schemas.attendance import AttendanceIncident
from app.services.supabase_db import get_conn, resolve_org_id


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


class SupabaseIncidentStore:
    def save(self, incident: AttendanceIncident) -> AttendanceIncident:
        with get_conn() as conn:
            org_id = resolve_org_id(conn)
            with conn.cursor() as cur:
                cur.execute(
                    """
                    insert into public.attendance_incidents (
                      incident_id, org_id, person_id, employee_name, violation_type,
                      attempted_at, scheduled_exit_time, tolerance_minutes, minutes_early,
                      reason, analysis, severity, status, evidence_ref,
                      supervisor_notified, created_at
                    )
                    values (
                      %s, %s, %s, %s, %s,
                      %s, %s, %s, %s,
                      %s, %s::jsonb, %s, %s, %s,
                      %s, %s
                    )
                    on conflict (incident_id) do nothing
                    """,
                    (
                        incident.incident_id,
                        org_id,
                        incident.person_id,
                        incident.employee_name,
                        incident.violation_type,
                        incident.attempted_at,
                        incident.scheduled_exit_time,
                        incident.tolerance_minutes,
                        incident.minutes_early,
                        incident.reason,
                        incident.analysis.model_dump_json() if incident.analysis else None,
                        incident.severity,
                        incident.status,
                        incident.evidence_ref,
                        incident.supervisor_notified,
                        incident.created_at,
                    ),
                )
        return incident

    def list(self, person_id: str | None = None, limit: int = 50) -> list[AttendanceIncident]:
        query = """
            select incident_id, person_id, employee_name, violation_type, attempted_at,
                   scheduled_exit_time, tolerance_minutes, minutes_early, reason,
                   analysis, severity, status, evidence_ref, supervisor_notified, created_at
            from public.attendance_incidents
            where org_id = %s
        """
        params: list[object] = []
        with get_conn() as conn:
            org_id = resolve_org_id(conn)
            params.append(org_id)
            if person_id:
                query += " and person_id = %s"
                params.append(person_id)
            query += " order by created_at desc limit %s"
            params.append(limit)
            with conn.cursor() as cur:
                cur.execute(query, tuple(params))
                rows = cur.fetchall()
        return [
            AttendanceIncident(
                incident_id=row[0],
                person_id=row[1],
                employee_name=row[2],
                violation_type=row[3],
                attempted_at=row[4],
                scheduled_exit_time=row[5],
                tolerance_minutes=row[6],
                minutes_early=row[7],
                reason=row[8],
                analysis=row[9],
                severity=row[10],
                status=row[11],
                evidence_ref=row[12],
                supervisor_notified=row[13],
                created_at=row[14],
            )
            for row in rows
        ]


def get_incident_store():
    if settings.storage_backend.lower() == "supabase":
        return SupabaseIncidentStore()
    return LocalIncidentStore()
