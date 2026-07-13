from __future__ import annotations

from contextlib import contextmanager
from urllib.parse import quote, unquote, urlparse, urlunparse
from uuid import UUID

import psycopg

from app.core.config import settings
from app.core.tenant import get_active_org_code, normalize_org_code


def normalize_database_url(url: str) -> str:
    """Convierte SQLAlchemy URL y codifica la contraseña (ej. * → %2A)."""
    if url.startswith("postgresql+psycopg://"):
        url = url.replace("postgresql+psycopg://", "postgresql://", 1)
    parsed = urlparse(url)
    if not parsed.password:
        return url
    encoded_password = quote(unquote(parsed.password), safe="")
    netloc = f"{parsed.username}:{encoded_password}@{parsed.hostname}"
    if parsed.port:
        netloc += f":{parsed.port}"
    return urlunparse(
        (
            parsed.scheme,
            netloc,
            parsed.path,
            parsed.params,
            parsed.query,
            parsed.fragment,
        )
    )


def test_connection() -> tuple[bool, str]:
    try:
        with get_conn() as conn:
            with conn.cursor() as cur:
                cur.execute("select 1")
                cur.fetchone()
        return True, "ok"
    except Exception as exc:
        message = str(exc).strip()
        if "tenant/user" in message and "not found" in message:
            return (
                False,
                "Proyecto Supabase no encontrado. Copia DATABASE_URL desde "
                "Supabase → Connect → Session pooler y verifica el PROJECT_REF.",
            )
        return False, message


@contextmanager
def get_conn():
    conninfo = normalize_database_url(settings.database_url)
    conn = psycopg.connect(conninfo, autocommit=False)
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def resolve_org_id(conn: psycopg.Connection, org_code: str | None = None) -> UUID:
    code = normalize_org_code(org_code or get_active_org_code())
    with conn.cursor() as cur:
        cur.execute(
            """
            select org_id
            from public.organizations
            where code = %s
            limit 1
            """,
            (code,),
        )
        row = cur.fetchone()
        if not row:
            raise RuntimeError(
                f"No existe organization con code='{code}'. "
                "Crea la empresa desde Datos de empresa o cambia DEFAULT_ORG_CODE."
            )
        return row[0]


def ensure_person(
    conn: psycopg.Connection,
    *,
    org_id: UUID,
    person_id: str,
    full_name: str,
    email: str | None = None,
    employee_code: str | None = None,
    area_code: str | None = None,
    position_code: str | None = None,
    dni: str | None = None,
    registration_status: str = "FACE_REGISTERED",
) -> None:
    with conn.cursor() as cur:
        cur.execute(
            """
            insert into public.persons (
              person_id, org_id, full_name, email, employee_code, area_code, position_code,
              dni, registration_status, face_registered_at
            )
            values (%s, %s, %s, %s, %s, %s, %s, %s, %s, now())
            on conflict (org_id, person_id) do update set
              full_name = excluded.full_name,
              email = coalesce(excluded.email, public.persons.email),
              employee_code = coalesce(excluded.employee_code, public.persons.employee_code),
              area_code = coalesce(excluded.area_code, public.persons.area_code),
              position_code = coalesce(excluded.position_code, public.persons.position_code),
              dni = coalesce(excluded.dni, public.persons.dni),
              registration_status = excluded.registration_status,
              face_registered_at = coalesce(public.persons.face_registered_at, now()),
              updated_at = now()
            """,
            (
                person_id,
                org_id,
                full_name,
                email,
                employee_code or person_id,
                area_code,
                position_code,
                dni,
                registration_status,
            ),
        )


def update_person(
    conn: psycopg.Connection,
    *,
    org_id: UUID,
    person_id: str,
    full_name: str | None = None,
    email: str | None = None,
    employee_code: str | None = None,
    is_active: bool | None = None,
) -> bool:
    fields: list[str] = []
    values: list[object] = []
    if full_name is not None:
        fields.append("full_name = %s")
        values.append(full_name.strip())
    if email is not None:
        fields.append("email = %s")
        values.append(email.strip() or None)
    if employee_code is not None:
        fields.append("employee_code = %s")
        values.append(employee_code.strip() or None)
    if is_active is not None:
        fields.append("is_active = %s")
        values.append(is_active)
    if not fields:
        return False

    fields.append("updated_at = now()")
    values.extend([person_id, org_id])
    with conn.cursor() as cur:
        cur.execute(
            f"""
            update public.persons
            set {", ".join(fields)}
            where person_id = %s and org_id = %s
            """,
            values,
        )
        return cur.rowcount > 0


def person_exists(
    conn: psycopg.Connection,
    *,
    org_id: UUID,
    person_id: str,
) -> bool:
    with conn.cursor() as cur:
        cur.execute(
            """
            select 1
            from public.persons
            where person_id = %s and org_id = %s
            limit 1
            """,
            (person_id, org_id),
        )
        return cur.fetchone() is not None


def save_face_asset(
    conn: psycopg.Connection,
    *,
    org_id: UUID,
    person_id: str,
    r2_key: str,
    public_url: str | None,
    content_type: str,
    bytes_size: int | None = None,
) -> None:
    with conn.cursor() as cur:
        cur.execute(
            """
            insert into public.face_assets
              (org_id, person_id, r2_key, public_url, content_type, bytes_size, captured_at)
            values
              (%s, %s, %s, %s, %s, %s, now())
            """,
            (org_id, person_id, r2_key, public_url, content_type, bytes_size),
        )


def ensure_device(
    conn: psycopg.Connection,
    *,
    org_id: UUID,
    device_id: str,
) -> None:
    with conn.cursor() as cur:
        cur.execute(
            """
            insert into public.devices (device_id, org_id, label, kind)
            values (%s, %s, %s, 'edge')
            on conflict (org_id, device_id) do nothing
            """,
            (device_id, org_id, device_id),
        )
