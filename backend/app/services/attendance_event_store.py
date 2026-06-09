from __future__ import annotations

import json
from datetime import UTC, date, datetime, timedelta
from pathlib import Path

import psycopg.errors

from app.core.config import settings
from app.schemas.attendance import (
    AttendanceEvent,
    AttendanceEventCreate,
    AttendanceEventUpdate,
    AttendanceReportSummary,
)
from app.services.supabase_db import ensure_device, ensure_person, get_conn, resolve_org_id


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
        active_events = active_attendance_events(events)
        duplicate = self._is_duplicate(payload, active_events, duplicate_window_seconds)
        if not duplicate:
            duplicate = self._is_shift_duplicate(payload, active_events)
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

    def get(self, event_id: str) -> AttendanceEvent | None:
        return next((event for event in self._load() if event.event_id == event_id), None)

    def update(self, event_id: str, payload: AttendanceEventUpdate) -> AttendanceEvent:
        events = self._load()
        updates = payload.model_dump(exclude_unset=True)
        if not updates:
            raise ValueError("No se enviaron campos para actualizar.")
        if "event_type" in updates and updates["event_type"] not in {"check_in", "check_out"}:
            raise ValueError("event_type debe ser check_in o check_out.")
        for index, event in enumerate(events):
            if event.event_id != event_id:
                continue
            if "captured_at" in updates and updates["captured_at"] is not None:
                updates["captured_at"] = ensure_aware_utc(updates["captured_at"])
            updated = event.model_copy(update=updates)
            events[index] = updated
            self._save(events)
            return updated
        raise LookupError(f"No existe evento con event_id='{event_id}'.")

    def delete(self, event_id: str) -> str:
        events = self._load()
        target = next((event for event in events if event.event_id == event_id), None)
        if target is None:
            raise LookupError(f"No existe evento con event_id='{event_id}'.")
        target_day = ensure_aware_utc(target.captured_at).date()
        remaining = [
            event
            for event in events
            if event.event_id != event_id
            and not should_remove_orphan_duplicate(event, target, target_day)
        ]
        self._save(remaining)
        return event_id

    def list(
        self,
        person_id: str | None = None,
        device_id: str | None = None,
        event_type: str | None = None,
        date_from: date | None = None,
        date_to: date | None = None,
        limit: int = 100,
    ) -> list[AttendanceEvent]:
        events = self._load()
        events = filter_attendance_events(
            events,
            person_id=person_id,
            device_id=device_id,
            event_type=event_type,
            date_from=date_from,
            date_to=date_to,
        )
        events.sort(key=lambda item: ensure_aware_utc(item.captured_at), reverse=True)
        return events[:limit]

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

    def _is_shift_duplicate(
        self,
        payload: AttendanceEventCreate,
        events: list[AttendanceEvent],
    ) -> bool:
        day = ensure_aware_utc(payload.captured_at).date()
        today = [
            event
            for event in events
            if event.person_id == payload.person_id
            and ensure_aware_utc(event.captured_at).date() == day
        ]
        if payload.event_type == "check_in":
            return any(event.event_type == "check_in" for event in today)

        if payload.event_type == "check_out":
            has_check_in = any(event.event_type == "check_in" for event in today)
            if not has_check_in:
                return True
            return any(event.event_type == "check_out" for event in today)

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


def active_attendance_events(events: list[AttendanceEvent]) -> list[AttendanceEvent]:
    """Solo marcas validas cuentan para duplicados de turno."""
    return [event for event in events if event.accepted and not event.duplicate]


def filter_attendance_events(
    events: list[AttendanceEvent],
    *,
    person_id: str | None = None,
    device_id: str | None = None,
    event_type: str | None = None,
    date_from: date | None = None,
    date_to: date | None = None,
) -> list[AttendanceEvent]:
    filtered = events
    if person_id:
        filtered = [event for event in filtered if event.person_id == person_id]
    if device_id:
        filtered = [event for event in filtered if event.device_id == device_id]
    if event_type:
        filtered = [event for event in filtered if event.event_type == event_type]
    if date_from:
        filtered = [
            event
            for event in filtered
            if ensure_aware_utc(event.captured_at).date() >= date_from
        ]
    if date_to:
        filtered = [
            event
            for event in filtered
            if ensure_aware_utc(event.captured_at).date() <= date_to
        ]
    return filtered


def should_remove_orphan_duplicate(
    event: AttendanceEvent,
    target: AttendanceEvent,
    target_day: date,
) -> bool:
    """Al borrar una marca valida, limpia rechazos/duplicados huerfanos del mismo dia."""
    if event.person_id != target.person_id:
        return False
    if ensure_aware_utc(event.captured_at).date() != target_day:
        return False
    if event.event_type != target.event_type:
        return False
    return not event.accepted or event.duplicate


def build_attendance_summary(events: list[AttendanceEvent]) -> AttendanceReportSummary:
    return AttendanceReportSummary(
        total=len(events),
        check_ins=sum(1 for event in events if event.event_type == "check_in"),
        check_outs=sum(1 for event in events if event.event_type == "check_out"),
        duplicates=sum(1 for event in events if event.duplicate),
        rejected=sum(1 for event in events if not event.accepted),
    )


class SupabaseAttendanceEventStore:
    def create(
        self,
        payload: AttendanceEventCreate,
        duplicate_window_seconds: int = 45,
    ) -> AttendanceEvent:
        payload = payload.model_copy(
            update={"captured_at": ensure_aware_utc(payload.captured_at)}
        )
        event_id = new_event_id()
        with get_conn() as conn:
            org_id = resolve_org_id(conn)
            ensure_person(
                conn,
                org_id=org_id,
                person_id=payload.person_id,
                full_name=payload.employee_name or payload.person_id,
            )
            ensure_device(conn, org_id=org_id, device_id=payload.device_id)
            existing = self._list_person_day(conn, org_id=org_id, payload=payload)
            active_existing = active_attendance_events(existing)
            duplicate = self._is_duplicate(payload, active_existing, duplicate_window_seconds)
            if not duplicate:
                duplicate = self._is_shift_duplicate(payload, active_existing)
            accepted = not duplicate
            try:
                with conn.cursor() as cur:
                    cur.execute(
                        """
                        insert into public.attendance_events (
                          event_id, org_id, person_id, employee_name, device_id, event_type,
                          confidence, captured_at, source, evidence_ref, accepted, duplicate
                        ) values (
                          %s, %s, %s, %s, %s, %s,
                          %s, %s, %s, %s, %s, %s
                        )
                        """,
                        (
                            event_id,
                            org_id,
                            payload.person_id,
                            payload.employee_name,
                            payload.device_id,
                            payload.event_type,
                            payload.confidence,
                            payload.captured_at,
                            payload.source,
                            payload.evidence_ref,
                            accepted,
                            duplicate,
                        ),
                    )
            except psycopg.errors.UniqueViolation:
                conn.rollback()
                duplicate = True
                accepted = False
                event_id = new_event_id()
                with conn.cursor() as cur:
                    cur.execute(
                        """
                        insert into public.attendance_events (
                          event_id, org_id, person_id, employee_name, device_id, event_type,
                          confidence, captured_at, source, evidence_ref, accepted, duplicate
                        ) values (
                          %s, %s, %s, %s, %s, %s,
                          %s, %s, %s, %s, %s, %s
                        )
                        """,
                        (
                            event_id,
                            org_id,
                            payload.person_id,
                            payload.employee_name,
                            payload.device_id,
                            payload.event_type,
                            payload.confidence,
                            payload.captured_at,
                            payload.source,
                            payload.evidence_ref,
                            accepted,
                            duplicate,
                        ),
                    )
        return AttendanceEvent(
            **payload.model_dump(),
            event_id=event_id,
            accepted=accepted,
            duplicate=duplicate,
            created_at=datetime.now(UTC),
        )

    def get(self, event_id: str) -> AttendanceEvent | None:
        with get_conn() as conn:
            org_id = resolve_org_id(conn)
            with conn.cursor() as cur:
                cur.execute(
                    """
                    select event_id, person_id, employee_name, device_id, event_type,
                           confidence, captured_at, source, evidence_ref, accepted, duplicate, created_at
                    from public.attendance_events
                    where org_id = %s and event_id = %s
                    limit 1
                    """,
                    (org_id, event_id),
                )
                row = cur.fetchone()
        return self._row_to_event(row) if row else None

    def update(self, event_id: str, payload: AttendanceEventUpdate) -> AttendanceEvent:
        updates = payload.model_dump(exclude_unset=True)
        if not updates:
            raise ValueError("No se enviaron campos para actualizar.")
        if "event_type" in updates and updates["event_type"] not in {"check_in", "check_out"}:
            raise ValueError("event_type debe ser check_in o check_out.")
        if "captured_at" in updates and updates["captured_at"] is not None:
            updates["captured_at"] = ensure_aware_utc(updates["captured_at"])

        fields: list[str] = []
        values: list[object] = []
        for key, value in updates.items():
            fields.append(f"{key} = %s")
            values.append(value)

        with get_conn() as conn:
            org_id = resolve_org_id(conn)
            values.extend([event_id, org_id])
            with conn.cursor() as cur:
                cur.execute(
                    f"""
                    update public.attendance_events
                    set {", ".join(fields)}
                    where event_id = %s and org_id = %s
                    """,
                    values,
                )
                if cur.rowcount == 0:
                    raise LookupError(f"No existe evento con event_id='{event_id}'.")
                cur.execute(
                    """
                    select event_id, person_id, employee_name, device_id, event_type,
                           confidence, captured_at, source, evidence_ref, accepted, duplicate, created_at
                    from public.attendance_events
                    where event_id = %s and org_id = %s
                    limit 1
                    """,
                    (event_id, org_id),
                )
                row = cur.fetchone()
        return self._row_to_event(row)

    def delete(self, event_id: str, *, target: AttendanceEvent | None = None) -> str:
        with get_conn() as conn:
            org_id = resolve_org_id(conn)
            if target is None:
                with conn.cursor() as cur:
                    cur.execute(
                        """
                        select event_id, person_id, employee_name, device_id, event_type,
                               confidence, captured_at, source, evidence_ref, accepted, duplicate, created_at
                        from public.attendance_events
                        where org_id = %s and event_id = %s
                        limit 1
                        """,
                        (org_id, event_id),
                    )
                    row = cur.fetchone()
                target = self._row_to_event(row) if row else None
            if target is None:
                raise LookupError(f"No existe evento con event_id='{event_id}'.")
            target_day = ensure_aware_utc(target.captured_at).date()
            with conn.cursor() as cur:
                cur.execute(
                    """
                    delete from public.attendance_events
                    where event_id = %s and org_id = %s
                    """,
                    (event_id, org_id),
                )
                cur.execute(
                    """
                    delete from public.attendance_events
                    where org_id = %s
                      and person_id = %s
                      and (captured_at at time zone 'UTC')::date = %s
                      and event_type = %s
                      and (accepted = false or duplicate = true)
                    """,
                    (org_id, target.person_id, target_day, target.event_type),
                )
        return event_id

    def list(
        self,
        person_id: str | None = None,
        device_id: str | None = None,
        event_type: str | None = None,
        date_from: date | None = None,
        date_to: date | None = None,
        limit: int = 100,
    ) -> list[AttendanceEvent]:
        query = """
            select event_id, person_id, employee_name, device_id, event_type,
                   confidence, captured_at, source, evidence_ref, accepted, duplicate, created_at
            from public.attendance_events
            where org_id = %s
        """
        with get_conn() as conn:
            org_id = resolve_org_id(conn)
            params: list[object] = [org_id]
            if person_id:
                query += " and person_id = %s"
                params.append(person_id)
            if device_id:
                query += " and device_id = %s"
                params.append(device_id)
            if event_type:
                query += " and event_type = %s"
                params.append(event_type)
            if date_from:
                query += " and (captured_at at time zone 'UTC')::date >= %s"
                params.append(date_from)
            if date_to:
                query += " and (captured_at at time zone 'UTC')::date <= %s"
                params.append(date_to)
            query += " order by captured_at desc limit %s"
            params.append(limit)
            with conn.cursor() as cur:
                cur.execute(query, tuple(params))
                rows = cur.fetchall()
        return [self._row_to_event(row) for row in rows]

    def _list_person_day(
        self,
        conn,
        *,
        org_id,
        payload: AttendanceEventCreate,
    ) -> list[AttendanceEvent]:
        day = ensure_aware_utc(payload.captured_at).date()
        with conn.cursor() as cur:
            cur.execute(
                """
                select event_id, person_id, employee_name, device_id, event_type,
                       confidence, captured_at, source, evidence_ref, accepted, duplicate, created_at
                from public.attendance_events
                where org_id = %s
                  and person_id = %s
                  and (captured_at at time zone 'UTC')::date = %s
                order by captured_at asc
                """,
                (org_id, payload.person_id, day),
            )
            rows = cur.fetchall()
        return [self._row_to_event(row) for row in rows]

    @staticmethod
    def _row_to_event(row) -> AttendanceEvent:
        return AttendanceEvent(
            event_id=row[0],
            person_id=row[1],
            employee_name=row[2],
            device_id=row[3],
            event_type=row[4],
            confidence=float(row[5]),
            captured_at=row[6],
            source=row[7],
            evidence_ref=row[8],
            accepted=bool(row[9]),
            duplicate=bool(row[10]),
            created_at=row[11],
        )

    @staticmethod
    def _is_duplicate(
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

    @staticmethod
    def _is_shift_duplicate(
        payload: AttendanceEventCreate,
        events: list[AttendanceEvent],
    ) -> bool:
        if payload.event_type == "check_in":
            return any(event.event_type == "check_in" for event in events)
        if payload.event_type == "check_out":
            if not any(event.event_type == "check_in" for event in events):
                return True
            return any(event.event_type == "check_out" for event in events)
        return False


def get_attendance_event_store():
    if settings.storage_backend.lower() == "supabase":
        return SupabaseAttendanceEventStore()
    return LocalAttendanceEventStore()
