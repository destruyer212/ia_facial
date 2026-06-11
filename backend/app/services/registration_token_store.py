from __future__ import annotations

import json
from abc import ABC, abstractmethod
from datetime import UTC, datetime
from pathlib import Path
from uuid import UUID, uuid4

import psycopg

from app.core.config import settings
from app.services.schedule_service import get_schedule_service, schedule_label
from app.services.supabase_db import get_conn, resolve_org_id


class RegistrationTokenStore(ABC):
    @abstractmethod
    def list_workers(self) -> list[dict]:
        raise NotImplementedError

    @abstractmethod
    def get_worker(self, employee_id: str) -> dict:
        raise NotImplementedError

    @abstractmethod
    def add_worker(self, worker: dict) -> None:
        raise NotImplementedError

    @abstractmethod
    def update_worker(self, worker: dict) -> None:
        raise NotImplementedError

    @abstractmethod
    def find_worker_token_by_hash(self, token_hash: str) -> tuple[dict, dict] | None:
        raise NotImplementedError

    @abstractmethod
    def expire_old_tokens(self) -> None:
        raise NotImplementedError

    @abstractmethod
    def list_preregistered_codes(self) -> list[str]:
        raise NotImplementedError

    @abstractmethod
    def audit(
        self,
        *,
        action: str,
        success: bool,
        employee_id: str | None = None,
        token_id: str | None = None,
        source: str = "api",
        metadata: dict | None = None,
    ) -> None:
        raise NotImplementedError


class JsonRegistrationTokenStore(RegistrationTokenStore):
    def __init__(self, path: Path | None = None, audit_path: Path | None = None) -> None:
        data_dir = settings.resolved_data_dir
        data_dir.mkdir(parents=True, exist_ok=True)
        self.path = path or data_dir / "employee_registration_tokens.json"
        self.audit_path = audit_path or data_dir / "employee_registration_token_audit.json"

    def list_workers(self) -> list[dict]:
        return self._load_state()["workers"]

    def get_worker(self, employee_id: str) -> dict:
        return self._find_worker(self._load_state(), employee_id)

    def add_worker(self, worker: dict) -> None:
        state = self._load_state()
        state["workers"].append(worker)
        self._save_state(state)

    def update_worker(self, worker: dict) -> None:
        state = self._load_state()
        for index, current in enumerate(state["workers"]):
            if current["employee_id"] == worker["employee_id"]:
                state["workers"][index] = worker
                self._save_state(state)
                return
        raise LookupError(f"No existe trabajador '{worker['employee_id']}'.")

    def find_worker_token_by_hash(self, token_hash: str) -> tuple[dict, dict] | None:
        for worker in self.list_workers():
            for token_record in worker.get("tokens", []):
                if token_record.get("token_hash") == token_hash:
                    return worker, token_record
        return None

    def expire_old_tokens(self) -> None:
        state = self._load_state()
        changed = False
        now = datetime.now(UTC)
        for worker in state["workers"]:
            for token_record in worker.get("tokens", []):
                if token_record.get("status") != "TOKEN_SENT":
                    continue
                if _parse_dt(token_record["expires_at"]) <= now:
                    token_record["status"] = "TOKEN_EXPIRED"
                    if worker.get("registration_status") != "FACE_REGISTERED":
                        worker["registration_status"] = "TOKEN_EXPIRED"
                    worker["updated_at"] = now.isoformat()
                    changed = True
        if changed:
            self._save_state(state)

    def list_preregistered_codes(self) -> list[str]:
        return [worker.get("employee_code", "") for worker in self.list_workers()]

    def audit(
        self,
        *,
        action: str,
        success: bool,
        employee_id: str | None = None,
        token_id: str | None = None,
        source: str = "api",
        metadata: dict | None = None,
    ) -> None:
        audit = self._load_audit()
        audit["entries"].append(
            {
                "id": str(uuid4()),
                "employee_id": employee_id,
                "token_id": token_id,
                "action": action,
                "success": success,
                "source": source,
                "created_at": datetime.now(UTC).isoformat(),
                "metadata": metadata or {},
            }
        )
        if len(audit["entries"]) > 5000:
            audit["entries"] = audit["entries"][-5000:]
        self._save_audit(audit)

    def _find_worker(self, state: dict, employee_id: str) -> dict:
        for worker in state["workers"]:
            if worker["employee_id"] == employee_id or worker["employee_code"] == employee_id:
                return worker
        raise LookupError(f"No existe trabajador '{employee_id}'.")

    def _load_state(self) -> dict:
        if not self.path.exists():
            state = {"workers": []}
            self._save_state(state)
            return state
        try:
            state = json.loads(self.path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            state = {"workers": []}
        state.setdefault("workers", [])
        return state

    def _save_state(self, state: dict) -> None:
        self.path.write_text(json.dumps(state, indent=2, ensure_ascii=False), encoding="utf-8")

    def _load_audit(self) -> dict:
        if not self.audit_path.exists():
            audit = {"entries": []}
            self._save_audit(audit)
            return audit
        try:
            audit = json.loads(self.audit_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            audit = {"entries": []}
        audit.setdefault("entries", [])
        return audit

    def _save_audit(self, audit: dict) -> None:
        self.audit_path.write_text(json.dumps(audit, indent=2, ensure_ascii=False), encoding="utf-8")


class SupabaseRegistrationTokenStore(RegistrationTokenStore):
    def list_workers(self) -> list[dict]:
        with get_conn() as conn:
            org_id = resolve_org_id(conn)
            with conn.cursor() as cur:
                cur.execute(
                    """
                    select distinct p.person_id, p.employee_code, p.full_name, p.email, p.dni,
                           p.area_code, oa.name, p.position_code, op.name,
                           p.shift_id, ws.name, ws.start_time, ws.end_time,
                           p.registration_status, p.face_registered_at,
                           p.created_at, p.updated_at
                    from public.persons p
                    inner join public.employee_registration_tokens t
                      on t.employee_id = p.person_id and t.org_id = p.org_id
                    left join public.org_areas oa
                      on oa.org_id = p.org_id and oa.area_code = p.area_code
                    left join public.org_positions op
                      on op.org_id = p.org_id
                      and op.area_code = p.area_code
                      and op.position_code = p.position_code
                    left join public.work_shifts ws
                      on ws.org_id = p.org_id and ws.shift_code = p.shift_id
                    where p.org_id = %s
                    order by p.created_at desc
                    """,
                    (org_id,),
                )
                rows = cur.fetchall()
                workers = [_row_to_worker(row) for row in rows]
                for worker in workers:
                    worker["tokens"] = self._fetch_tokens(cur, org_id, worker["employee_id"])
                return workers

    def get_worker(self, employee_id: str) -> dict:
        with get_conn() as conn:
            org_id = resolve_org_id(conn)
            with conn.cursor() as cur:
                worker = self._fetch_worker_row(cur, org_id, employee_id)
                if worker is None:
                    raise LookupError(f"No existe trabajador '{employee_id}'.")
                worker["tokens"] = self._fetch_tokens(cur, org_id, worker["employee_id"])
                return worker

    def add_worker(self, worker: dict) -> None:
        with get_conn() as conn:
            org_id = resolve_org_id(conn)
            with conn.cursor() as cur:
                try:
                    cur.execute(
                        """
                        insert into public.persons (
                          person_id, org_id, full_name, email, employee_code,
                          area_code, position_code, dni, shift_id,
                          registration_status, is_active
                        )
                        values (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, true)
                        """,
                        (
                            worker["employee_id"],
                            org_id,
                            worker["name"],
                            worker["email"],
                            worker["employee_code"],
                            worker["area_code"],
                            worker["position_code"],
                            worker["dni"],
                            worker["shift_code"],
                            worker["registration_status"],
                        ),
                    )
                except psycopg.errors.UniqueViolation as exc:
                    if "persons_org_dni_uq" in str(exc):
                        raise ValueError("Ya existe un trabajador con ese DNI.") from exc
                    if "persons_org_employee_code_uq" in str(exc):
                        raise ValueError("Ya existe ese codigo de empleado.") from exc
                    raise
                for token_record in worker.get("tokens", []):
                    self._insert_token(cur, org_id, worker["employee_id"], token_record)

    def update_worker(self, worker: dict) -> None:
        with get_conn() as conn:
            org_id = resolve_org_id(conn)
            with conn.cursor() as cur:
                cur.execute(
                    """
                    update public.persons
                    set full_name = %s,
                        email = %s,
                        dni = %s,
                        area_code = %s,
                        position_code = %s,
                        shift_id = %s,
                        registration_status = %s,
                        face_registered_at = %s,
                        updated_at = now()
                    where org_id = %s and person_id = %s
                    """,
                    (
                        worker["name"],
                        worker["email"],
                        worker["dni"],
                        worker["area_code"],
                        worker["position_code"],
                        worker["shift_code"],
                        worker["registration_status"],
                        _parse_optional_dt(worker.get("face_registered_at")),
                        org_id,
                        worker["employee_id"],
                    ),
                )
                if cur.rowcount == 0:
                    raise LookupError(f"No existe trabajador '{worker['employee_id']}'.")
                for token_record in worker.get("tokens", []):
                    self._upsert_token(cur, org_id, worker["employee_id"], token_record)

    def find_worker_token_by_hash(self, token_hash: str) -> tuple[dict, dict] | None:
        with get_conn() as conn:
            org_id = resolve_org_id(conn)
            with conn.cursor() as cur:
                cur.execute(
                    """
                    select t.id, t.employee_id, t.token_hash, t.status, t.expires_at,
                           t.used_at, t.created_at, t.created_by, t.sent_to_email, t.sent_at
                    from public.employee_registration_tokens t
                    where t.org_id = %s and t.token_hash = %s
                    limit 1
                    """,
                    (org_id, token_hash),
                )
                token_row = cur.fetchone()
                if token_row is None:
                    return None
                token_record = _token_lookup_row_to_dict(token_row)
                worker = self._fetch_worker_row(cur, org_id, token_row[1])
                if worker is None:
                    return None
                worker["tokens"] = self._fetch_tokens(cur, org_id, worker["employee_id"])
                return worker, token_record

    def expire_old_tokens(self) -> None:
        now = datetime.now(UTC)
        with get_conn() as conn:
            org_id = resolve_org_id(conn)
            with conn.cursor() as cur:
                cur.execute(
                    """
                    update public.employee_registration_tokens t
                    set status = 'TOKEN_EXPIRED'
                    from public.persons p
                    where t.org_id = %s
                      and t.org_id = p.org_id
                      and t.employee_id = p.person_id
                      and t.status = 'TOKEN_SENT'
                      and t.expires_at <= %s
                      and p.registration_status <> 'FACE_REGISTERED'
                    """,
                    (org_id, now),
                )
                cur.execute(
                    """
                    update public.persons p
                    set registration_status = 'TOKEN_EXPIRED',
                        updated_at = now()
                    where p.org_id = %s
                      and p.registration_status not in ('FACE_REGISTERED', 'TOKEN_CANCELLED')
                      and exists (
                        select 1
                        from public.employee_registration_tokens t
                        where t.org_id = p.org_id
                          and t.employee_id = p.person_id
                          and t.status = 'TOKEN_EXPIRED'
                      )
                      and not exists (
                        select 1
                        from public.employee_registration_tokens t
                        where t.org_id = p.org_id
                          and t.employee_id = p.person_id
                          and t.status = 'TOKEN_SENT'
                      )
                    """,
                    (org_id,),
                )

    def list_preregistered_codes(self) -> list[str]:
        with get_conn() as conn:
            org_id = resolve_org_id(conn)
            with conn.cursor() as cur:
                cur.execute(
                    """
                    select employee_code
                    from public.persons
                    where org_id = %s
                      and employee_code is not null
                      and exists (
                        select 1
                        from public.employee_registration_tokens t
                        where t.org_id = persons.org_id
                          and t.employee_id = persons.person_id
                      )
                    """,
                    (org_id,),
                )
                return [row[0] for row in cur.fetchall() if row[0]]

    def audit(
        self,
        *,
        action: str,
        success: bool,
        employee_id: str | None = None,
        token_id: str | None = None,
        source: str = "api",
        metadata: dict | None = None,
    ) -> None:
        with get_conn() as conn:
            org_id = resolve_org_id(conn)
            with conn.cursor() as cur:
                cur.execute(
                    """
                    insert into public.employee_registration_token_audit (
                      org_id, employee_id, token_id, action, success, source, metadata
                    )
                    values (%s, %s, %s, %s, %s, %s, %s::jsonb)
                    """,
                    (
                        org_id,
                        employee_id,
                        token_id,
                        action,
                        success,
                        source,
                        json.dumps(metadata or {}),
                    ),
                )

    def _fetch_worker_row(self, cur, org_id: UUID, employee_id: str) -> dict | None:
        cur.execute(
            """
            select p.person_id, p.employee_code, p.full_name, p.email, p.dni,
                   p.area_code, oa.name, p.position_code, op.name,
                   p.shift_id, ws.name, ws.start_time, ws.end_time,
                   p.registration_status, p.face_registered_at,
                   p.created_at, p.updated_at
            from public.persons p
            left join public.org_areas oa
              on oa.org_id = p.org_id and oa.area_code = p.area_code
            left join public.org_positions op
              on op.org_id = p.org_id
              and op.area_code = p.area_code
              and op.position_code = p.position_code
            left join public.work_shifts ws
              on ws.org_id = p.org_id and ws.shift_code = p.shift_id
            where p.org_id = %s
              and (p.person_id = %s or p.employee_code = %s)
            limit 1
            """,
            (org_id, employee_id, employee_id),
        )
        row = cur.fetchone()
        if row is None:
            return None
        return _row_to_worker(row)

    def _fetch_tokens(self, cur, org_id: UUID, employee_id: str) -> list[dict]:
        cur.execute(
            """
            select id, token_hash, status, expires_at, used_at, created_at,
                   created_by, sent_to_email, sent_at
            from public.employee_registration_tokens
            where org_id = %s and employee_id = %s
            order by created_at asc
            """,
            (org_id, employee_id),
        )
        return [_token_list_row_to_dict(row) for row in cur.fetchall()]

    def _insert_token(self, cur, org_id: UUID, employee_id: str, token_record: dict) -> None:
        cur.execute(
            """
            insert into public.employee_registration_tokens (
              id, org_id, employee_id, token_hash, status, expires_at, used_at,
              created_at, created_by, sent_to_email, sent_at
            )
            values (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """,
            (
                token_record["id"],
                org_id,
                employee_id,
                token_record["token_hash"],
                token_record["status"],
                _parse_dt(token_record["expires_at"]),
                _parse_optional_dt(token_record.get("used_at")),
                _parse_dt(token_record["created_at"]),
                token_record.get("created_by"),
                token_record["sent_to_email"],
                _parse_optional_dt(token_record.get("sent_at")),
            ),
        )

    def _upsert_token(self, cur, org_id: UUID, employee_id: str, token_record: dict) -> None:
        cur.execute(
            """
            insert into public.employee_registration_tokens (
              id, org_id, employee_id, token_hash, status, expires_at, used_at,
              created_at, created_by, sent_to_email, sent_at
            )
            values (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            on conflict (id) do update set
              token_hash = excluded.token_hash,
              status = excluded.status,
              expires_at = excluded.expires_at,
              used_at = excluded.used_at,
              sent_to_email = excluded.sent_to_email,
              sent_at = excluded.sent_at
            """,
            (
                token_record["id"],
                org_id,
                employee_id,
                token_record["token_hash"],
                token_record["status"],
                _parse_dt(token_record["expires_at"]),
                _parse_optional_dt(token_record.get("used_at")),
                _parse_dt(token_record["created_at"]),
                token_record.get("created_by"),
                token_record["sent_to_email"],
                _parse_optional_dt(token_record.get("sent_at")),
            ),
        )


def get_registration_token_store(
    *,
    path: Path | None = None,
    audit_path: Path | None = None,
) -> RegistrationTokenStore:
    if settings.storage_backend.lower() == "supabase":
        return SupabaseRegistrationTokenStore()
    return JsonRegistrationTokenStore(path=path, audit_path=audit_path)


def _row_to_worker(row: tuple) -> dict:
    shift_code = row[9] or ""
    shift_name = row[10] or ""
    schedule = ""
    if shift_code:
        shift = get_schedule_service().get_shift(shift_code)
        if shift is not None:
            schedule = schedule_label(shift)
        elif row[11] and row[12]:
            schedule = f"{row[11]} - {row[12]}"
    created_at = row[15]
    updated_at = row[16]
    return {
        "employee_id": row[0],
        "employee_code": row[1] or row[0],
        "name": row[2],
        "email": row[3] or "",
        "dni": row[4] or "",
        "area_code": row[5] or "",
        "area_name": row[6] or "",
        "position_code": row[7] or "",
        "position_name": row[8] or "",
        "shift_code": shift_code,
        "shift_name": shift_name,
        "schedule_label": schedule,
        "registration_status": row[13],
        "face_registered_at": _format_dt(row[14]),
        "created_at": _format_dt(created_at),
        "updated_at": _format_dt(updated_at),
        "created_by": "dashboard",
        "tokens": [],
    }


def _token_list_row_to_dict(row: tuple) -> dict:
    return {
        "id": str(row[0]),
        "token_hash": row[1],
        "status": row[2],
        "expires_at": _format_dt(row[3]),
        "used_at": _format_dt(row[4]),
        "created_at": _format_dt(row[5]),
        "created_by": row[6],
        "sent_to_email": row[7],
        "sent_at": _format_dt(row[8]),
    }


def _token_lookup_row_to_dict(row: tuple) -> dict:
    return {
        "id": str(row[0]),
        "employee_id": row[1],
        "token_hash": row[2],
        "status": row[3],
        "expires_at": _format_dt(row[4]),
        "used_at": _format_dt(row[5]),
        "created_at": _format_dt(row[6]),
        "created_by": row[7],
        "sent_to_email": row[8],
        "sent_at": _format_dt(row[9]),
    }


def _parse_dt(value: str | datetime) -> datetime:
    if isinstance(value, datetime):
        if value.tzinfo is None:
            return value.replace(tzinfo=UTC)
        return value.astimezone(UTC)
    parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=UTC)
    return parsed.astimezone(UTC)


def _parse_optional_dt(value: str | datetime | None) -> datetime | None:
    if value is None:
        return None
    if isinstance(value, str) and not value.strip():
        return None
    return _parse_dt(value)


def _format_dt(value: datetime | str | None) -> str | None:
    if value is None:
        return None
    if isinstance(value, datetime):
        parsed = value
    else:
        parsed = _parse_dt(value)
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=UTC)
    return parsed.astimezone(UTC).isoformat()
