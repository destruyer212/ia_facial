from __future__ import annotations

import hashlib
import hmac
import re
import secrets
from datetime import UTC, datetime, timedelta
from pathlib import Path
from uuid import uuid4

from app.schemas.registration import (
    PreRegisterEmployeeRequest,
    RegistrationWorkerPublic,
    ValidateRegistrationTokenResponse,
)
from app.services.employee_catalog_service import get_employee_catalog_service
from app.services.embedding_store import get_embedding_store
from app.services.gmail_service import get_gmail_service
from app.services.registration_token_store import RegistrationTokenStore, get_registration_token_store
from app.services.schedule_service import get_schedule_service, schedule_label

STATUS_PENDING = "PENDING_FACE_REGISTRATION"
STATUS_TOKEN_SENT = "TOKEN_SENT"
STATUS_FACE_REGISTERED = "FACE_REGISTERED"
STATUS_TOKEN_EXPIRED = "TOKEN_EXPIRED"
STATUS_TOKEN_CANCELLED = "TOKEN_CANCELLED"

TOKEN_ACTIVE = "TOKEN_SENT"
TOKEN_USED = "TOKEN_USED"
TOKEN_EXPIRED = "TOKEN_EXPIRED"
TOKEN_CANCELLED = "TOKEN_CANCELLED"

_CODE_PATTERN = re.compile(r"^([A-Z]{2})-([A-Z]{2})-(\d{4})$")


class RegistrationTokenService:
    def __init__(self, store: RegistrationTokenStore | None = None) -> None:
        self.store = store or get_registration_token_store()

    def list_workers(self) -> list[RegistrationWorkerPublic]:
        self.store.expire_old_tokens()
        return [self._public_worker(worker) for worker in self.store.list_workers()]

    def pre_register(
        self,
        payload: PreRegisterEmployeeRequest,
        *,
        created_by: str = "dashboard",
    ) -> tuple[RegistrationWorkerPublic, bool, str | None, str]:
        self._validate_email(payload.email)
        area_code, position_code, area_name, position_name = (
            get_employee_catalog_service().validate_area_position(
                payload.area_code,
                payload.position_code,
            )
        )
        shift = get_schedule_service().get_shift(payload.shift_code)
        if shift is None or not shift.is_active:
            raise ValueError(f"Turno '{payload.shift_code}' no existe o esta inactivo.")

        employee_code = self._next_employee_code(area_code, position_code)
        now = datetime.now(UTC)
        worker = {
            "employee_id": employee_code,
            "employee_code": employee_code,
            "name": payload.name.strip(),
            "dni": payload.dni.strip(),
            "email": payload.email.strip().lower(),
            "area_code": area_code,
            "area_name": area_name,
            "position_code": position_code,
            "position_name": position_name,
            "shift_code": shift.code,
            "shift_name": shift.name,
            "schedule_label": schedule_label(shift),
            "registration_status": STATUS_PENDING,
            "face_registered_at": None,
            "created_at": now.isoformat(),
            "updated_at": now.isoformat(),
            "created_by": created_by,
            "tokens": [],
        }
        token = self._new_token()
        token_record = self._build_token_record(
            token=token,
            worker=worker,
            expires_hours=payload.token_expires_hours,
            created_by=created_by,
        )
        worker["tokens"].append(token_record)
        worker["updated_at"] = now.isoformat()
        self.store.add_worker(worker)
        email_sent, email_message = self._send_token(worker, token)
        self._apply_email_result(worker, email_sent)
        self.store.audit(
            action="PRE_REGISTER",
            success=True,
            employee_id=worker["employee_id"],
            token_id=token_record["id"],
            metadata={"email_sent": email_sent, "employee_code": worker["employee_code"]},
        )
        return self._public_worker(worker), email_sent, token if not email_sent else None, email_message

    def resend_token(self, employee_id: str) -> tuple[RegistrationWorkerPublic, bool, str | None, str]:
        worker = self.store.get_worker(employee_id)
        token_record = self._active_token(worker)
        token = None
        if token_record is None:
            token = self._new_token()
            token_record = self._build_token_record(
                token=token,
                worker=worker,
                expires_hours=48,
                created_by="dashboard",
            )
            worker["tokens"].append(token_record)
        else:
            token = self._new_token()
            token_record["token_hash"] = self._hash_token(token)
            token_record["expires_at"] = (datetime.now(UTC) + timedelta(hours=48)).isoformat()
            token_record["status"] = TOKEN_ACTIVE
            token_record["used_at"] = None
        worker["updated_at"] = datetime.now(UTC).isoformat()
        self.store.update_worker(worker)
        email_sent, email_message = self._send_token(worker, token)
        self._apply_email_result(worker, email_sent)
        self.store.audit(
            action="RESEND_TOKEN",
            success=email_sent,
            employee_id=worker["employee_id"],
            token_id=token_record["id"],
            metadata={"email_sent": email_sent},
        )
        return self._public_worker(worker), email_sent, token if not email_sent else None, email_message

    def regenerate_token(self, employee_id: str) -> tuple[RegistrationWorkerPublic, bool, str | None, str]:
        worker = self.store.get_worker(employee_id)
        for token_item in worker.get("tokens", []):
            if token_item.get("status") == TOKEN_ACTIVE:
                token_item["status"] = TOKEN_CANCELLED
        token = self._new_token()
        worker["tokens"].append(
            self._build_token_record(
                token=token,
                worker=worker,
                expires_hours=48,
                created_by="dashboard",
            )
        )
        worker["updated_at"] = datetime.now(UTC).isoformat()
        self.store.update_worker(worker)
        email_sent, email_message = self._send_token(worker, token)
        self._apply_email_result(worker, email_sent)
        self.store.audit(
            action="REGENERATE_TOKEN",
            success=email_sent,
            employee_id=worker["employee_id"],
            token_id=worker["tokens"][-1]["id"],
            metadata={"email_sent": email_sent},
        )
        return self._public_worker(worker), email_sent, token if not email_sent else None, email_message

    def cancel_token(self, employee_id: str) -> RegistrationWorkerPublic:
        worker = self.store.get_worker(employee_id)
        for token_record in worker.get("tokens", []):
            if token_record.get("status") == TOKEN_ACTIVE:
                token_record["status"] = TOKEN_CANCELLED
        worker["registration_status"] = STATUS_TOKEN_CANCELLED
        worker["updated_at"] = datetime.now(UTC).isoformat()
        self.store.update_worker(worker)
        self.store.audit(
            action="CANCEL_TOKEN",
            success=True,
            employee_id=worker["employee_id"],
            metadata={"employee_code": worker["employee_code"]},
        )
        return self._public_worker(worker)

    def validate_token(self, token: str, *, source: str = "api") -> ValidateRegistrationTokenResponse:
        self.store.expire_old_tokens()
        token_hash = self._hash_token(token)
        match = self.store.find_worker_token_by_hash(token_hash)
        if match is None:
            self.store.audit(
                action="VALIDATE_TOKEN",
                success=False,
                source=source,
                metadata={"reason": "invalid"},
            )
            return ValidateRegistrationTokenResponse(valid=False, message="Token invalido.")

        worker, token_record = match
        status = token_record.get("status")
        if status == TOKEN_USED:
            self.store.audit(
                action="VALIDATE_TOKEN",
                success=False,
                employee_id=worker["employee_id"],
                token_id=token_record.get("id"),
                source=source,
                metadata={"reason": "used"},
            )
            return ValidateRegistrationTokenResponse(valid=False, message="Token ya usado.")
        if status == TOKEN_CANCELLED:
            self.store.audit(
                action="VALIDATE_TOKEN",
                success=False,
                employee_id=worker["employee_id"],
                token_id=token_record.get("id"),
                source=source,
                metadata={"reason": "cancelled"},
            )
            return ValidateRegistrationTokenResponse(valid=False, message="Token cancelado.")
        expires_at = self._parse_dt(token_record.get("expires_at"))
        if expires_at <= datetime.now(UTC):
            token_record["status"] = TOKEN_EXPIRED
            worker["registration_status"] = STATUS_TOKEN_EXPIRED
            self.store.update_worker(worker)
            self.store.audit(
                action="VALIDATE_TOKEN",
                success=False,
                employee_id=worker["employee_id"],
                token_id=token_record.get("id"),
                source=source,
                metadata={"reason": "expired"},
            )
            return ValidateRegistrationTokenResponse(valid=False, message="Token vencido.")
        self.store.audit(
            action="VALIDATE_TOKEN",
            success=True,
            employee_id=worker["employee_id"],
            token_id=token_record.get("id"),
            source=source,
        )
        return ValidateRegistrationTokenResponse(
            valid=True,
            worker=self._public_worker(worker),
            registration_session=self._session_for_token(token),
            message="Token valido.",
        )

    def worker_for_valid_token(self, token: str) -> dict:
        validation = self.validate_token(token, source="mobile")
        if not validation.valid or validation.worker is None:
            raise ValueError(validation.message)
        return self.store.get_worker(validation.worker.employee_id)

    def complete_token(self, token: str) -> RegistrationWorkerPublic:
        token_hash = self._hash_token(token)
        match = self.store.find_worker_token_by_hash(token_hash)
        if match is None:
            raise ValueError("Token invalido.")
        worker, token_record = match
        if token_record.get("status") != TOKEN_ACTIVE:
            raise ValueError("Token no esta activo.")
        now = datetime.now(UTC)
        token_record["status"] = TOKEN_USED
        token_record["used_at"] = now.isoformat()
        worker["registration_status"] = STATUS_FACE_REGISTERED
        worker["face_registered_at"] = now.isoformat()
        worker["updated_at"] = now.isoformat()
        self.store.update_worker(worker)
        self.store.audit(
            action="COMPLETE_TOKEN",
            success=True,
            employee_id=worker["employee_id"],
            token_id=token_record.get("id"),
            metadata={"employee_code": worker["employee_code"]},
        )
        return self._public_worker(worker)

    def _next_employee_code(self, area_code: str, position_code: str) -> str:
        prefix = f"{area_code}-{position_code}-"
        max_value = 0
        for face in get_embedding_store().list_public():
            for code in (face.person_id, face.employee_code or ""):
                if not code.startswith(prefix):
                    continue
                match = _CODE_PATTERN.match(code)
                if match:
                    max_value = max(max_value, int(match.group(3)))
        for code in self.store.list_preregistered_codes():
            if not code.startswith(prefix):
                continue
            match = _CODE_PATTERN.match(code)
            if match:
                max_value = max(max_value, int(match.group(3)))
        return f"{area_code}-{position_code}-{max_value + 1:04d}"

    def _send_token(self, worker: dict, token: str) -> tuple[bool, str]:
        active = self._active_token(worker)
        result = get_gmail_service().send_registration_token(
            to_email=worker["email"],
            employee_name=worker["name"],
            employee_code=worker["employee_code"],
            token=token,
            expires_label=active.get("expires_at", "") if active else "",
        )
        if active and result.sent:
            active["sent_at"] = datetime.now(UTC).isoformat()
        return result.sent, result.message

    def _apply_email_result(self, worker: dict, email_sent: bool) -> None:
        active = self._active_token(worker)
        worker["registration_status"] = STATUS_TOKEN_SENT if email_sent else STATUS_PENDING
        worker["updated_at"] = datetime.now(UTC).isoformat()
        if active:
            active["sent_at"] = datetime.now(UTC).isoformat() if email_sent else None
        self.store.update_worker(worker)

    def _build_token_record(
        self,
        *,
        token: str,
        worker: dict,
        expires_hours: int,
        created_by: str,
    ) -> dict:
        now = datetime.now(UTC)
        return {
            "id": str(uuid4()),
            "employee_id": worker["employee_id"],
            "token_hash": self._hash_token(token),
            "status": TOKEN_ACTIVE,
            "expires_at": (now + timedelta(hours=expires_hours)).isoformat(),
            "used_at": None,
            "created_at": now.isoformat(),
            "created_by": created_by,
            "sent_to_email": worker["email"],
            "sent_at": None,
        }

    @staticmethod
    def _new_token() -> str:
        return secrets.token_urlsafe(24)

    @staticmethod
    def _hash_token(token: str) -> str:
        return hashlib.sha256(token.strip().encode("utf-8")).hexdigest()

    @staticmethod
    def _session_for_token(token: str) -> str:
        return hashlib.sha256(f"session:{token.strip()}".encode("utf-8")).hexdigest()

    @staticmethod
    def _validate_email(value: str) -> None:
        email = value.strip()
        if "@" not in email or "." not in email.rsplit("@", 1)[-1]:
            raise ValueError("Correo empresarial no valido.")

    def _active_token(self, worker: dict) -> dict | None:
        for token_record in reversed(worker.get("tokens", [])):
            if token_record.get("status") == TOKEN_ACTIVE:
                return token_record
        return None

    def _public_worker(self, worker: dict) -> RegistrationWorkerPublic:
        active = self._active_token(worker)
        latest = active or (worker.get("tokens") or [{}])[-1]
        return RegistrationWorkerPublic(
            employee_id=worker["employee_id"],
            employee_code=worker["employee_code"],
            name=worker["name"],
            dni=worker["dni"],
            email=worker["email"],
            area_code=worker["area_code"],
            area_name=worker["area_name"],
            position_code=worker["position_code"],
            position_name=worker["position_name"],
            shift_code=worker["shift_code"],
            shift_name=worker["shift_name"],
            schedule_label=worker.get("schedule_label"),
            registration_status=worker["registration_status"],
            face_registered_at=self._parse_optional_dt(worker.get("face_registered_at")),
            created_at=self._parse_dt(worker["created_at"]),
            updated_at=self._parse_dt(worker["updated_at"]),
            token_status=latest.get("status"),
            token_expires_at=self._parse_optional_dt(latest.get("expires_at")),
            token_sent_to_email=latest.get("sent_to_email"),
            token_sent_at=self._parse_optional_dt(latest.get("sent_at")),
        )

    @staticmethod
    def _parse_dt(value: str | datetime) -> datetime:
        if isinstance(value, datetime):
            parsed = value
        else:
            parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        if parsed.tzinfo is None:
            return parsed.replace(tzinfo=UTC)
        return parsed.astimezone(UTC)

    def _parse_optional_dt(self, value: str | datetime | None) -> datetime | None:
        if value is None:
            return None
        if isinstance(value, str) and not value.strip():
            return None
        return self._parse_dt(value)


def get_registration_token_service(
    *,
    path: Path | None = None,
    audit_path: Path | None = None,
) -> RegistrationTokenService:
    store = get_registration_token_store(path=path, audit_path=audit_path)
    return RegistrationTokenService(store=store)
