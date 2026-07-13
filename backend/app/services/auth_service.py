from __future__ import annotations

import base64
import hashlib
import hmac
import json
import secrets
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from pathlib import Path
from uuid import uuid4

from psycopg.errors import UndefinedTable

from app.core.config import settings
from app.core.tenant import normalize_org_code
from app.schemas.auth import AuthOrganization, AuthUserPublic, LoginResponse
from app.services.supabase_db import get_conn, resolve_org_id

PASSWORD_ALGORITHM = "pbkdf2_sha256"
PASSWORD_ITERATIONS = 260_000
TOKEN_ALGORITHM = "HS256"


@dataclass
class AuthenticatedUser:
    user_id: str
    email: str
    full_name: str | None
    role: str
    org_code: str
    organizations: list[AuthOrganization] = field(default_factory=list)

    def public(self) -> AuthUserPublic:
        return AuthUserPublic(
            user_id=self.user_id,
            email=self.email,
            full_name=self.full_name,
            role=self.role,
            org_code=self.org_code,
            organizations=self.organizations,
        )


def _b64url(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode("ascii")


def _unb64url(value: str) -> bytes:
    padded = value + ("=" * (-len(value) % 4))
    return base64.urlsafe_b64decode(padded.encode("ascii"))


def hash_password(password: str) -> str:
    salt = secrets.token_bytes(16)
    digest = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        salt,
        PASSWORD_ITERATIONS,
    )
    return f"{PASSWORD_ALGORITHM}${PASSWORD_ITERATIONS}${_b64url(salt)}${_b64url(digest)}"


def verify_password(password: str, stored_hash: str) -> bool:
    try:
        algorithm, raw_iterations, raw_salt, raw_digest = stored_hash.split("$", 3)
        if algorithm != PASSWORD_ALGORITHM:
            return False
        iterations = int(raw_iterations)
        salt = _unb64url(raw_salt)
        expected = _unb64url(raw_digest)
    except Exception:
        return False
    actual = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        salt,
        iterations,
    )
    return hmac.compare_digest(actual, expected)


def _sign(message: bytes) -> str:
    digest = hmac.new(
        settings.auth_secret_key.encode("utf-8"),
        message,
        hashlib.sha256,
    ).digest()
    return _b64url(digest)


def create_access_token(user: AuthenticatedUser) -> tuple[str, datetime]:
    now = datetime.now(timezone.utc)
    expires_at = now + timedelta(minutes=max(settings.auth_token_ttl_minutes, 5))
    header = {"alg": TOKEN_ALGORITHM, "typ": "JWT"}
    payload = {
        "sub": user.user_id,
        "email": user.email,
        "name": user.full_name,
        "role": user.role,
        "org_code": user.org_code,
        "iat": int(now.timestamp()),
        "exp": int(expires_at.timestamp()),
        "jti": secrets.token_urlsafe(12),
    }
    encoded_header = _b64url(json.dumps(header, separators=(",", ":")).encode("utf-8"))
    encoded_payload = _b64url(json.dumps(payload, separators=(",", ":")).encode("utf-8"))
    signing_input = f"{encoded_header}.{encoded_payload}".encode("ascii")
    return f"{encoded_header}.{encoded_payload}.{_sign(signing_input)}", expires_at


def decode_access_token(token: str) -> dict:
    parts = token.split(".")
    if len(parts) != 3:
        raise ValueError("Token invalido.")
    encoded_header, encoded_payload, signature = parts
    signing_input = f"{encoded_header}.{encoded_payload}".encode("ascii")
    expected = _sign(signing_input)
    if not hmac.compare_digest(signature, expected):
        raise ValueError("Firma de token invalida.")
    try:
        header = json.loads(_unb64url(encoded_header))
        payload = json.loads(_unb64url(encoded_payload))
    except Exception as exc:
        raise ValueError("Token invalido.") from exc
    if header.get("alg") != TOKEN_ALGORITHM:
        raise ValueError("Algoritmo de token no soportado.")
    expires_at = int(payload.get("exp", 0))
    if expires_at <= int(datetime.now(timezone.utc).timestamp()):
        raise ValueError("La sesion expiro.")
    return payload


class AuthService:
    def __init__(self, path: Path | None = None) -> None:
        self.path = path or settings.resolved_data_dir / "auth_users.json"

    def login(self, email: str, password: str, org_code: str | None = None) -> LoginResponse:
        self._ensure_safe_auth_config()
        normalized_email = self._normalize_email(email)
        requested_org = normalize_org_code(org_code) if org_code else None
        if settings.storage_backend.lower() == "supabase":
            user = self._login_supabase(normalized_email, password, requested_org)
        else:
            user = self._login_json(normalized_email, password, requested_org)
        token, expires_at = create_access_token(user)
        return LoginResponse(
            access_token=token,
            expires_at=expires_at.isoformat(),
            user=user.public(),
        )

    def authenticate_token(self, token: str) -> AuthenticatedUser:
        self._ensure_safe_auth_config()
        payload = decode_access_token(token)
        email = self._normalize_email(str(payload.get("email") or ""))
        org_code = normalize_org_code(str(payload.get("org_code") or settings.default_org_code))
        if settings.storage_backend.lower() == "supabase":
            return self._load_user_supabase(email, org_code)
        return self._load_user_json(email, org_code)

    def _normalize_email(self, email: str) -> str:
        normalized = str(email or "").strip().lower()
        if not normalized or "@" not in normalized:
            raise ValueError("Correo o contrasena invalidos.")
        return normalized

    def _ensure_safe_auth_config(self) -> None:
        environment = settings.environment.lower().strip()
        if environment in {"development", "local", "test", "testing"}:
            return
        if (
            settings.auth_secret_key == "change-me-dev-secret"
            or settings.auth_default_admin_password == "Admin123!"
        ):
            raise RuntimeError(
                "Configura AUTH_SECRET_KEY y AUTH_DEFAULT_ADMIN_PASSWORD antes de usar login en produccion."
            )

    def _login_supabase(
        self,
        email: str,
        password: str,
        requested_org: str | None,
    ) -> AuthenticatedUser:
        try:
            with get_conn() as conn:
                self._ensure_bootstrap_admin_supabase(conn)
                with conn.cursor() as cur:
                    cur.execute(
                        """
                        select user_id::text, email, full_name, password_hash, is_active
                        from public.app_users
                        where lower(email) = %s
                        limit 1
                        """,
                        (email,),
                    )
                    row = cur.fetchone()
                    if not row or not row[4] or not verify_password(password, row[3]):
                        raise ValueError("Correo o contrasena invalidos.")
                    memberships = self._memberships_supabase(conn, row[0])
                    user = self._select_membership(
                        user_id=row[0],
                        email=row[1],
                        full_name=row[2],
                        memberships=memberships,
                        requested_org=requested_org,
                    )
                    cur.execute(
                        "update public.app_users set last_login_at = now(), updated_at = now() where user_id = %s",
                        (row[0],),
                    )
                    return user
        except UndefinedTable as exc:
            raise RuntimeError(
                "Faltan tablas de autenticacion. Ejecuta la migracion "
                "infra/supabase/migrations/v9_auth_users.sql en Supabase/Flyway."
            ) from exc

    def _load_user_supabase(self, email: str, org_code: str) -> AuthenticatedUser:
        try:
            with get_conn() as conn:
                with conn.cursor() as cur:
                    cur.execute(
                        """
                        select user_id::text, email, full_name, is_active
                        from public.app_users
                        where lower(email) = %s
                        limit 1
                        """,
                        (email,),
                    )
                    row = cur.fetchone()
                    if not row or not row[3]:
                        raise ValueError("Usuario inactivo o inexistente.")
                    memberships = self._memberships_supabase(conn, row[0])
                    return self._select_membership(
                        user_id=row[0],
                        email=row[1],
                        full_name=row[2],
                        memberships=memberships,
                        requested_org=org_code,
                    )
        except UndefinedTable as exc:
            raise RuntimeError(
                "Faltan tablas de autenticacion. Ejecuta la migracion "
                "infra/supabase/migrations/v9_auth_users.sql en Supabase/Flyway."
            ) from exc

    def _ensure_bootstrap_admin_supabase(self, conn) -> None:
        with conn.cursor() as cur:
            cur.execute("select count(*) from public.app_users")
            count = cur.fetchone()[0]
            if count:
                return
            org_id = resolve_org_id(conn, settings.default_org_code)
            cur.execute(
                """
                insert into public.app_users (email, full_name, password_hash)
                values (%s, %s, %s)
                returning user_id
                """,
                (
                    self._normalize_email(settings.auth_default_admin_email),
                    settings.auth_default_admin_name,
                    hash_password(settings.auth_default_admin_password),
                ),
            )
            user_id = cur.fetchone()[0]
            cur.execute(
                """
                insert into public.app_user_memberships (user_id, org_id, role)
                values (%s, %s, 'platform_admin')
                on conflict (user_id, org_id) do update set
                  role = excluded.role,
                  is_active = true
                """,
                (user_id, org_id),
            )

    def _memberships_supabase(self, conn, user_id: str) -> list[AuthOrganization]:
        with conn.cursor() as cur:
            cur.execute(
                """
                select o.code, o.name, m.role
                from public.app_user_memberships m
                join public.organizations o on o.org_id = m.org_id
                where m.user_id = %s
                  and m.is_active = true
                  and o.is_active = true
                order by case when o.code = %s then 0 else 1 end, o.name
                """,
                (user_id, settings.default_org_code),
            )
            return [
                AuthOrganization(code=row[0], name=row[1], role=row[2])
                for row in cur.fetchall()
            ]

    def _login_json(
        self,
        email: str,
        password: str,
        requested_org: str | None,
    ) -> AuthenticatedUser:
        data = self._read_json_auth()
        user = next((item for item in data["users"] if item["email"] == email), None)
        if not user or not user.get("is_active", True) or not verify_password(password, user["password_hash"]):
            raise ValueError("Correo o contrasena invalidos.")
        user["last_login_at"] = datetime.now(timezone.utc).isoformat()
        self._write_json_auth(data)
        return self._select_membership(
            user_id=user["user_id"],
            email=user["email"],
            full_name=user.get("full_name"),
            memberships=[AuthOrganization(**item) for item in user.get("organizations", [])],
            requested_org=requested_org,
        )

    def _load_user_json(self, email: str, org_code: str) -> AuthenticatedUser:
        data = self._read_json_auth()
        user = next((item for item in data["users"] if item["email"] == email), None)
        if not user or not user.get("is_active", True):
            raise ValueError("Usuario inactivo o inexistente.")
        return self._select_membership(
            user_id=user["user_id"],
            email=user["email"],
            full_name=user.get("full_name"),
            memberships=[AuthOrganization(**item) for item in user.get("organizations", [])],
            requested_org=org_code,
        )

    def _read_json_auth(self) -> dict:
        if not self.path.exists():
            data = {"users": []}
        else:
            data = json.loads(self.path.read_text(encoding="utf-8"))
            if "users" not in data or not isinstance(data["users"], list):
                data = {"users": []}
        if not data["users"]:
            data["users"].append(
                {
                    "user_id": str(uuid4()),
                    "email": self._normalize_email(settings.auth_default_admin_email),
                    "full_name": settings.auth_default_admin_name,
                    "password_hash": hash_password(settings.auth_default_admin_password),
                    "is_active": True,
                    "created_at": datetime.now(timezone.utc).isoformat(),
                    "organizations": [
                        {
                            "code": normalize_org_code(settings.default_org_code),
                            "name": "Demo Company",
                            "role": "platform_admin",
                        }
                    ],
                }
            )
            self._write_json_auth(data)
        return data

    def _write_json_auth(self, data: dict) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(
            json.dumps(data, ensure_ascii=True, indent=2),
            encoding="utf-8",
        )

    def _select_membership(
        self,
        *,
        user_id: str,
        email: str,
        full_name: str | None,
        memberships: list[AuthOrganization],
        requested_org: str | None,
    ) -> AuthenticatedUser:
        if not memberships:
            raise ValueError("El usuario no tiene empresas asignadas.")
        platform_membership = next(
            (membership for membership in memberships if membership.role == "platform_admin"),
            None,
        )
        selected = None
        if requested_org:
            selected = next((item for item in memberships if item.code == requested_org), None)
            if selected is None and platform_membership is not None:
                selected = AuthOrganization(
                    code=requested_org,
                    name=requested_org,
                    role=platform_membership.role,
                )
        else:
            selected = memberships[0]
        if selected is None:
            raise ValueError("El usuario no tiene acceso a esa empresa.")
        return AuthenticatedUser(
            user_id=user_id,
            email=email,
            full_name=full_name,
            role=selected.role,
            org_code=normalize_org_code(selected.code),
            organizations=memberships,
        )


_auth_service: AuthService | None = None


def get_auth_service() -> AuthService:
    global _auth_service
    if _auth_service is None:
        _auth_service = AuthService()
    return _auth_service
