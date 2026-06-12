from __future__ import annotations

import base64
import json
from datetime import UTC, datetime, timedelta
from email.message import EmailMessage
from pathlib import Path
from urllib import request
from urllib.error import URLError
from urllib.parse import urlencode

from app.core.config import settings


class GmailSendResult:
    def __init__(self, sent: bool, message: str) -> None:
        self.sent = sent
        self.message = message


class GmailService:
    def __init__(self) -> None:
        self.backend_dir = Path(__file__).resolve().parents[2]
        self._token_payload: dict | None = None
        self._token_path = self._resolve_token_path()

    def _resolve_token_path(self) -> Path:
        custom = settings.gmail_token_path.strip()
        if custom:
            return Path(custom)
        return self.backend_dir / "token.json"

    def _load_token_payload(self) -> dict:
        if self._token_payload is not None:
            return self._token_payload

        inline = settings.gmail_token_json.strip()
        if inline:
            self._token_payload = json.loads(inline)
            return self._token_payload

        if not self._token_path.exists():
            raise FileNotFoundError(
                "token.json de Gmail no existe. En local ejecuta generar_token.py; "
                "en Render configura GMAIL_TOKEN_PATH o GMAIL_TOKEN_JSON."
            )

        self._token_payload = json.loads(self._token_path.read_text(encoding="utf-8"))
        return self._token_payload

    def _persist_token_payload(self, payload: dict) -> None:
        self._token_payload = payload
        candidates = [self._token_path, Path("/tmp/ia_facial_gmail_token.json")]
        for path in candidates:
            try:
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
                return
            except OSError:
                continue

    def send_registration_token(
        self,
        *,
        to_email: str,
        employee_name: str,
        employee_code: str,
        token: str,
        expires_label: str,
    ) -> GmailSendResult:
        subject = "Token de registro facial - IA Facial Enterprise"
        body = (
            f"Hola {employee_name},\n\n"
            "RRHH ha creado tu pre-registro en IA Facial Enterprise.\n\n"
            f"Codigo empleado: {employee_code}\n"
            f"Token de registro: {token}\n"
            f"Vence: {expires_label}\n\n"
            "Abre la app movil, ingresa este token y completa las capturas: "
            "frontal, giro izquierda y giro derecha.\n\n"
            "No compartas este token. Solo puede usarse una vez.\n"
        )
        return self._send(to_email=to_email, subject=subject, body=body)

    def _send(self, *, to_email: str, subject: str, body: str) -> GmailSendResult:
        try:
            token_payload = self._load_token_payload()
        except FileNotFoundError as exc:
            return GmailSendResult(False, str(exc))
        except json.JSONDecodeError:
            return GmailSendResult(False, "GMAIL_TOKEN_JSON no es JSON valido.")

        try:
            access_token = self._access_token(token_payload)
            raw_message = self._build_message(
                sender="me",
                to_email=to_email,
                subject=subject,
                body=body,
            )
            req = request.Request(
                "https://gmail.googleapis.com/gmail/v1/users/me/messages/send",
                data=json.dumps({"raw": raw_message}).encode("utf-8"),
                headers={
                    "Authorization": f"Bearer {access_token}",
                    "Content-Type": "application/json",
                },
                method="POST",
            )
            with request.urlopen(req, timeout=20) as response:
                if 200 <= response.status < 300:
                    return GmailSendResult(True, "Correo enviado por Gmail.")
                return GmailSendResult(False, f"Gmail respondio HTTP {response.status}.")
        except Exception as exc:
            return GmailSendResult(False, f"No se pudo enviar Gmail: {exc}")

    def _access_token(self, payload: dict) -> str:
        token = payload.get("token")
        expiry = parse_expiry(payload.get("expiry"))
        if token and expiry and expiry > datetime.now(UTC) + timedelta(minutes=2):
            return token
        refresh_token = payload.get("refresh_token")
        client_id = payload.get("client_id")
        client_secret = payload.get("client_secret")
        token_uri = payload.get("token_uri") or "https://oauth2.googleapis.com/token"
        if not refresh_token or not client_id or not client_secret:
            raise RuntimeError("token.json no contiene credenciales suficientes.")
        data = urlencode(
            {
                "client_id": client_id,
                "client_secret": client_secret,
                "refresh_token": refresh_token,
                "grant_type": "refresh_token",
            }
        ).encode("utf-8")
        req = request.Request(token_uri, data=data, method="POST")
        try:
            with request.urlopen(req, timeout=20) as response:
                refreshed = json.loads(response.read().decode("utf-8"))
        except URLError as exc:
            raise RuntimeError(f"No se pudo refrescar token Gmail: {exc}") from exc
        access_token = refreshed.get("access_token")
        if not access_token:
            raise RuntimeError("Gmail no devolvio access_token.")
        payload["token"] = access_token
        if refreshed.get("expires_in"):
            payload["expiry"] = (
                datetime.now(UTC) + timedelta(seconds=int(refreshed["expires_in"]))
            ).isoformat().replace("+00:00", "Z")
        self._persist_token_payload(payload)
        return access_token

    @staticmethod
    def _build_message(*, sender: str, to_email: str, subject: str, body: str) -> str:
        message = EmailMessage()
        message["From"] = sender
        message["To"] = to_email
        message["Subject"] = subject
        message.set_content(body)
        encoded = base64.urlsafe_b64encode(message.as_bytes()).decode("utf-8")
        return encoded.rstrip("=")


_gmail_service: GmailService | None = None


def get_gmail_service() -> GmailService:
    global _gmail_service
    if _gmail_service is None:
        _gmail_service = GmailService()
    return _gmail_service


def parse_expiry(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=UTC)
    return parsed.astimezone(UTC)
