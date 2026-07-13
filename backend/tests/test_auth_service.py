import pytest

from app.core.config import settings
from app.services.auth_service import AuthService


def test_json_auth_bootstrap_login_and_token(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr(settings, "storage_backend", "json")
    monkeypatch.setattr(settings, "environment", "development")
    monkeypatch.setattr(settings, "auth_secret_key", "test-secret")
    monkeypatch.setattr(settings, "auth_default_admin_email", "admin@test.local")
    monkeypatch.setattr(settings, "auth_default_admin_password", "Strong123!")
    monkeypatch.setattr(settings, "auth_default_admin_name", "Admin Test")
    monkeypatch.setattr(settings, "default_org_code", "demo")

    service = AuthService(tmp_path / "auth_users.json")
    response = service.login("admin@test.local", "Strong123!", "demo")

    assert response.token_type == "bearer"
    assert response.user.email == "admin@test.local"
    assert response.user.role == "platform_admin"
    assert response.user.org_code == "demo"

    current_user = service.authenticate_token(response.access_token)
    assert current_user.email == "admin@test.local"
    assert current_user.role == "platform_admin"

    with pytest.raises(ValueError):
        service.login("admin@test.local", "wrong", "demo")
