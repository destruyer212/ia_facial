import hashlib
import json
from pathlib import Path

from app.schemas.registration import PreRegisterEmployeeRequest
from app.services.registration_token_service import (
    STATUS_FACE_REGISTERED,
    TOKEN_USED,
    RegistrationTokenService,
)
from app.services.registration_token_store import JsonRegistrationTokenStore
from app.services.schedule_service import ScheduleService


class _FakeEmbeddingStore:
    def list_public(self) -> list:
        return []


class _FakeGmailService:
    def send_registration_token(self, **kwargs):
        class Result:
            sent = False
            message = "gmail mock"

        return Result()


def test_registration_token_is_hashed_one_use_and_completes_worker(tmp_path, monkeypatch) -> None:
    from app.services import registration_token_service as token_module

    token_path = Path(tmp_path) / "employee_registration_tokens.json"
    audit_path = Path(tmp_path) / "employee_registration_token_audit.json"
    schedule_service = ScheduleService(Path(tmp_path) / "work_schedules.json")
    store = JsonRegistrationTokenStore(path=token_path, audit_path=audit_path)
    service = RegistrationTokenService(store=store)
    monkeypatch.setattr(token_module, "get_embedding_store", lambda: _FakeEmbeddingStore())
    monkeypatch.setattr(token_module, "get_schedule_service", lambda: schedule_service)
    monkeypatch.setattr(token_module, "get_gmail_service", lambda: _FakeGmailService())

    worker, email_sent, token, _ = service.pre_register(
        PreRegisterEmployeeRequest(
            name="Juan Perez",
            dni="12345678",
            email="juan.perez@empresa.com",
            area_code="MS",
            position_code="PL",
            shift_code="TM",
        )
    )

    assert email_sent is False
    assert token is not None
    assert worker.registration_status == "PENDING_FACE_REGISTRATION"
    assert worker.employee_code == "MS-PL-0001"
    assert token not in token_path.read_text(encoding="utf-8")

    state = json.loads(token_path.read_text(encoding="utf-8"))
    token_record = state["workers"][0]["tokens"][0]
    assert token_record["token_hash"] == hashlib.sha256(token.encode("utf-8")).hexdigest()

    validation = service.validate_token(token)
    assert validation.valid is True
    assert validation.worker is not None
    assert validation.worker.employee_code == "MS-PL-0001"
    assert validation.worker.area_name == "Mantenimiento y Servicios"

    completed = service.complete_token(token)
    assert completed.registration_status == STATUS_FACE_REGISTERED
    assert completed.token_status == TOKEN_USED

    reused = service.validate_token(token)
    assert reused.valid is False
    assert "usado" in reused.message
