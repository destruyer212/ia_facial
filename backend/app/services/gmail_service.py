from __future__ import annotations

import base64
import re
from html import escape
import json
from datetime import UTC, datetime, timedelta
from email.message import EmailMessage
from pathlib import Path
from urllib import request
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from app.core.config import settings

_HEX_COLOR_RE = re.compile(r"^#[0-9A-Fa-f]{6}$")


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
        brand = _load_registration_email_brand()
        expires_text = _format_expiry_for_email(expires_label, brand["timezone"])
        subject = f"{brand['name']}: token de registro facial"
        body = _build_registration_text_body(
            employee_name=employee_name,
            employee_code=employee_code,
            token=token,
            expires_text=expires_text,
            company_name=brand["name"],
        )
        html_body = _build_registration_html_body(
            employee_name=employee_name,
            employee_code=employee_code,
            token=token,
            expires_text=expires_text,
            brand=brand,
        )
        return self._send(
            to_email=to_email,
            subject=subject,
            body=body,
            html_body=html_body,
        )

    def _send(
        self,
        *,
        to_email: str,
        subject: str,
        body: str,
        html_body: str | None = None,
    ) -> GmailSendResult:
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
                html_body=html_body,
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
        except HTTPError as exc:
            return GmailSendResult(False, f"Gmail rechazo el envio: {_format_http_error(exc)}")
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
        except HTTPError as exc:
            detail = _format_http_error(exc)
            if exc.code == 400:
                detail = (
                    f"{detail}. El token OAuth de Gmail esta vencido, revocado o no "
                    "corresponde a credentials.json; regenera backend/token.json, "
                    "subelo al VPS y reinicia el backend."
                )
            raise RuntimeError(f"No se pudo refrescar OAuth de Gmail: {detail}") from exc
        except URLError as exc:
            raise RuntimeError(f"No se pudo conectar con Gmail para refrescar OAuth: {exc}") from exc
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
    def _build_message(
        *,
        sender: str,
        to_email: str,
        subject: str,
        body: str,
        html_body: str | None = None,
    ) -> str:
        message = EmailMessage()
        message["From"] = sender
        message["To"] = to_email
        message["Subject"] = subject
        message.set_content(body)
        if html_body:
            message.add_alternative(html_body, subtype="html")
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


def _load_registration_email_brand() -> dict[str, str]:
    fallback = {
        "name": "IA Facial Enterprise",
        "timezone": "America/Lima",
        "logo_url": "",
        "address": "",
        "ruc": "",
        "primary": "#0d9488",
        "accent": "#2563eb",
        "sidebar": "#101827",
    }
    try:
        from app.services.admin_service import get_admin_service

        organization = get_admin_service().get_organization()
    except Exception:
        return fallback

    return {
        "name": (organization.name or fallback["name"]).strip() or fallback["name"],
        "timezone": (organization.timezone or fallback["timezone"]).strip() or fallback["timezone"],
        "logo_url": (organization.logo_url or "").strip(),
        "address": (organization.address or "").strip(),
        "ruc": (organization.ruc or "").strip(),
        "primary": _safe_hex_color(organization.brand_primary_color, fallback["primary"]),
        "accent": _safe_hex_color(organization.brand_accent_color, fallback["accent"]),
        "sidebar": _safe_hex_color(organization.brand_sidebar_color, fallback["sidebar"]),
    }


def _build_registration_text_body(
    *,
    employee_name: str,
    employee_code: str,
    token: str,
    expires_text: str,
    company_name: str,
) -> str:
    return (
        f"Hola {employee_name},\n\n"
        f"{company_name} creo tu pre-registro para IA Facial.\n\n"
        f"Codigo empleado: {employee_code}\n"
        f"Token de registro: {token}\n"
        f"Vence: {expires_text}\n\n"
        "Abre la app movil, ingresa este token y completa las capturas: "
        "frontal, giro izquierda y giro derecha.\n\n"
        "No compartas este token. Solo puede usarse una vez.\n"
    )


def _build_registration_html_body(
    *,
    employee_name: str,
    employee_code: str,
    token: str,
    expires_text: str,
    brand: dict[str, str],
) -> str:
    company = escape(brand["name"])
    safe_name = escape(employee_name.strip() or "colaborador")
    safe_code = escape(employee_code)
    safe_token = escape(token)
    safe_expires = escape(expires_text)
    safe_address = escape(brand.get("address") or "")
    safe_ruc = escape(brand.get("ruc") or "")
    primary = brand["primary"]
    accent = brand["accent"]
    sidebar = brand["sidebar"]
    mark = escape(_company_mark(brand["name"]))
    logo_url = escape(brand.get("logo_url") or "")
    logo_markup = (
        f'<img src="{logo_url}" alt="{company}" width="44" height="44" '
        'style="display:block;border-radius:12px;object-fit:cover;border:0;" />'
        if logo_url.startswith(("https://", "http://"))
        else (
            f'<div style="width:44px;height:44px;border-radius:12px;background:{primary};'
            'color:#ffffff;font-family:Arial,sans-serif;font-size:18px;font-weight:800;'
            'line-height:44px;text-align:center;">'
            f"{mark}</div>"
        )
    )
    footer_bits = " | ".join(item for item in (safe_ruc and f"RUC {safe_ruc}", safe_address) if item)
    footer_line = f"<br />{footer_bits}" if footer_bits else ""

    return f"""<!doctype html>
<html>
  <body style="margin:0;padding:0;background:#edf3f8;color:#111827;font-family:Arial,Helvetica,sans-serif;">
    <div style="display:none;max-height:0;overflow:hidden;opacity:0;color:transparent;">
      Tu token de registro facial para {company} esta listo.
    </div>
    <table role="presentation" width="100%" cellspacing="0" cellpadding="0" style="background:#edf3f8;padding:24px 12px;">
      <tr>
        <td align="center">
          <table role="presentation" width="100%" cellspacing="0" cellpadding="0" style="max-width:560px;background:#ffffff;border-radius:18px;overflow:hidden;border:1px solid #dbe4ee;box-shadow:0 18px 42px rgba(15,23,42,0.12);">
            <tr>
              <td style="background:{sidebar};padding:22px 24px;border-bottom:4px solid {primary};">
                <table role="presentation" width="100%" cellspacing="0" cellpadding="0">
                  <tr>
                    <td style="width:54px;vertical-align:middle;">{logo_markup}</td>
                    <td style="vertical-align:middle;">
                      <div style="color:#ffffff;font-size:18px;font-weight:800;line-height:1.2;">{company}</div>
                      <div style="color:#b7c4d6;font-size:12px;letter-spacing:.08em;text-transform:uppercase;margin-top:4px;">Registro facial seguro</div>
                    </td>
                  </tr>
                </table>
              </td>
            </tr>
            <tr>
              <td style="padding:28px 24px 8px;">
                <div style="display:inline-block;background:{_soft_hex(primary)};color:{primary};border-radius:999px;padding:7px 11px;font-size:12px;font-weight:800;letter-spacing:.04em;text-transform:uppercase;">Token listo</div>
                <h1 style="margin:16px 0 8px;font-size:26px;line-height:1.15;color:#0f172a;">Hola, {safe_name}</h1>
                <p style="margin:0;color:#475569;font-size:15px;line-height:1.6;">
                  RRHH creo tu pre-registro en IA Facial. Usa este token en la app movil para completar tus capturas.
                </p>
              </td>
            </tr>
            <tr>
              <td style="padding:16px 24px 4px;">
                <table role="presentation" width="100%" cellspacing="0" cellpadding="0" style="border-collapse:separate;border-spacing:0 10px;">
                  <tr>
                    <td style="background:#f8fafc;border:1px solid #e2e8f0;border-radius:12px;padding:14px;">
                      <div style="color:#64748b;font-size:12px;font-weight:700;text-transform:uppercase;">Codigo empleado</div>
                      <div style="color:#0f172a;font-size:18px;font-weight:800;margin-top:4px;">{safe_code}</div>
                    </td>
                  </tr>
                  <tr>
                    <td style="background:{sidebar};border-radius:14px;padding:18px;border-left:6px solid {accent};">
                      <div style="color:#cbd5e1;font-size:12px;font-weight:700;text-transform:uppercase;">Token de registro</div>
                      <div style="color:#ffffff;font-family:'Courier New',monospace;font-size:24px;font-weight:800;letter-spacing:.03em;line-height:1.3;word-break:break-all;margin-top:8px;">{safe_token}</div>
                    </td>
                  </tr>
                  <tr>
                    <td style="background:#fff7ed;border:1px solid #fed7aa;border-radius:12px;padding:14px;">
                      <div style="color:#9a3412;font-size:12px;font-weight:700;text-transform:uppercase;">Vence</div>
                      <div style="color:#7c2d12;font-size:16px;font-weight:800;margin-top:4px;">{safe_expires}</div>
                    </td>
                  </tr>
                </table>
              </td>
            </tr>
            <tr>
              <td style="padding:10px 24px 24px;">
                <div style="background:#f8fafc;border:1px solid #e2e8f0;border-radius:14px;padding:16px;">
                  <div style="font-size:14px;font-weight:800;color:#0f172a;margin-bottom:10px;">Como completar tu registro</div>
                  <table role="presentation" width="100%" cellspacing="0" cellpadding="0">
                    <tr>
                      <td style="width:28px;color:{primary};font-weight:900;">1</td>
                      <td style="color:#475569;font-size:14px;line-height:1.5;padding-bottom:8px;">Abre la app movil de IA Facial.</td>
                    </tr>
                    <tr>
                      <td style="width:28px;color:{primary};font-weight:900;">2</td>
                      <td style="color:#475569;font-size:14px;line-height:1.5;padding-bottom:8px;">Ingresa el token exactamente como aparece arriba.</td>
                    </tr>
                    <tr>
                      <td style="width:28px;color:{primary};font-weight:900;">3</td>
                      <td style="color:#475569;font-size:14px;line-height:1.5;">Completa las capturas frontal, giro izquierda y giro derecha.</td>
                    </tr>
                  </table>
                </div>
                <p style="margin:16px 0 0;color:#64748b;font-size:13px;line-height:1.55;">
                  Por seguridad, no compartas este token. Solo puede usarse una vez.
                </p>
              </td>
            </tr>
            <tr>
              <td style="background:#f8fafc;border-top:1px solid #e2e8f0;padding:16px 24px;text-align:center;color:#64748b;font-size:12px;line-height:1.5;">
                Correo generado automaticamente por IA Facial para {company}.{footer_line}
              </td>
            </tr>
          </table>
        </td>
      </tr>
    </table>
  </body>
</html>"""


def _format_expiry_for_email(value: str, timezone: str) -> str:
    parsed = parse_expiry(value)
    if parsed is None:
        return value
    try:
        local_dt = parsed.astimezone(ZoneInfo(timezone))
    except ZoneInfoNotFoundError:
        local_dt = parsed
        timezone = "UTC"
    return f"{local_dt:%d/%m/%Y %H:%M} ({timezone})"


def _safe_hex_color(value: str | None, fallback: str) -> str:
    color = (value or "").strip()
    return color.lower() if _HEX_COLOR_RE.match(color) else fallback


def _soft_hex(color: str) -> str:
    if not _HEX_COLOR_RE.match(color):
        return "#e0f2fe"
    red = int(color[1:3], 16)
    green = int(color[3:5], 16)
    blue = int(color[5:7], 16)
    red = round(red + (255 - red) * 0.88)
    green = round(green + (255 - green) * 0.88)
    blue = round(blue + (255 - blue) * 0.88)
    return f"#{red:02x}{green:02x}{blue:02x}"


def _company_mark(name: str) -> str:
    letters = [part[0] for part in name.strip().split() if part]
    return "".join(letters[:2]).upper() or "IA"


def _format_http_error(exc: HTTPError) -> str:
    reason = str(exc.reason or "").strip()
    detail = ""
    try:
        body = exc.read().decode("utf-8", errors="replace")
    except Exception:
        body = ""
    if body:
        try:
            payload = json.loads(body)
        except json.JSONDecodeError:
            detail = body[:240]
        else:
            error = payload.get("error")
            if isinstance(error, dict):
                detail = str(error.get("message") or error.get("status") or "")
            elif isinstance(error, str):
                detail = error
            description = payload.get("error_description")
            if description:
                detail = f"{detail}: {description}" if detail else str(description)
    suffix = detail or reason
    return f"HTTP {exc.code}{': ' + suffix if suffix else ''}"
