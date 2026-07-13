import base64
from email import policy
from email.parser import BytesParser

from app.services.gmail_service import (
    GmailService,
    _build_registration_html_body,
    _format_expiry_for_email,
)


def _decode_raw_message(raw: str):
    padded = raw + ("=" * (-len(raw) % 4))
    payload = base64.urlsafe_b64decode(padded.encode("utf-8"))
    return BytesParser(policy=policy.default).parsebytes(payload)


def test_gmail_message_includes_html_alternative() -> None:
    raw = GmailService._build_message(
        sender="me",
        to_email="trabajador@example.com",
        subject="Empresa: token de registro facial",
        body="Texto plano",
        html_body="<strong>Correo bonito</strong>",
    )

    message = _decode_raw_message(raw)

    assert message["Subject"] == "Empresa: token de registro facial"
    assert message.get_body(preferencelist=("plain",)).get_content().strip() == "Texto plano"
    assert "Correo bonito" in message.get_body(preferencelist=("html",)).get_content()


def test_registration_email_uses_brand_and_friendly_expiry() -> None:
    brand = {
        "name": "Talento Inversiones",
        "timezone": "America/Lima",
        "logo_url": "",
        "address": "Av. Principal 123",
        "ruc": "12345678901",
        "primary": "#0d9488",
        "accent": "#2563eb",
        "sidebar": "#101827",
    }

    html = _build_registration_html_body(
        employee_name="Piero Movil",
        employee_code="GG-SG-0001",
        token="abc123TOKEN",
        expires_text=_format_expiry_for_email("2026-07-15T06:13:29+00:00", "America/Lima"),
        brand=brand,
    )

    assert "Talento Inversiones" in html
    assert "GG-SG-0001" in html
    assert "abc123TOKEN" in html
    assert "15/07/2026 01:13 (America/Lima)" in html
    assert "#0d9488" in html
