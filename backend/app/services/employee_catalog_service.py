from __future__ import annotations

import json
import re
from pathlib import Path

from app.core.config import settings
from app.schemas.employee import (
    EmployeeCatalogResponse,
    NextEmployeeCodeResponse,
    OrgAreaPublic,
    OrgPositionPublic,
)
from app.services.supabase_db import get_conn, resolve_org_id

_CODE_PATTERN = re.compile(r"^([A-Z]{2})-([A-Z]{2})-(\d{4})$")


class EmployeeCatalogService:
    def __init__(self) -> None:
        catalog_path = Path(__file__).resolve().parent.parent / "data" / "employee_catalog.json"
        payload = json.loads(catalog_path.read_text(encoding="utf-8"))
        self._areas = [
            OrgAreaPublic(**area) for area in sorted(payload["areas"], key=lambda item: item["sort_order"])
        ]
        self._positions = [
            OrgPositionPublic(**position)
            for position in sorted(payload["positions"], key=lambda item: (item["area_code"], item["sort_order"]))
        ]

    def get_catalog(self) -> EmployeeCatalogResponse:
        if settings.storage_backend.lower() == "supabase":
            return self._get_catalog_from_db()
        admin_catalog = self._get_catalog_from_admin_state()
        if admin_catalog is not None:
            return admin_catalog
        return EmployeeCatalogResponse(areas=self._areas, positions=self._positions)

    def _get_catalog_from_admin_state(self) -> EmployeeCatalogResponse | None:
        try:
            from app.services.admin_service import get_admin_service

            payload = get_admin_service().get_active_catalog()
            return EmployeeCatalogResponse(
                areas=[OrgAreaPublic(**area) for area in payload["areas"]],
                positions=[OrgPositionPublic(**position) for position in payload["positions"]],
            )
        except Exception:
            return None

    def _get_catalog_from_db(self) -> EmployeeCatalogResponse:
        with get_conn() as conn:
            org_id = resolve_org_id(conn)
            with conn.cursor() as cur:
                cur.execute(
                    """
                    select area_code, name, sort_order
                    from public.org_areas
                    where org_id = %s and is_active = true
                    order by sort_order, area_code
                    """,
                    (org_id,),
                )
                areas = [
                    OrgAreaPublic(code=row[0], name=row[1], sort_order=row[2])
                    for row in cur.fetchall()
                ]
                if not areas:
                    return EmployeeCatalogResponse(areas=self._areas, positions=self._positions)

                cur.execute(
                    """
                    select area_code, position_code, name, sort_order
                    from public.org_positions
                    where org_id = %s and is_active = true
                    order by area_code, sort_order, position_code
                    """,
                    (org_id,),
                )
                positions = [
                    OrgPositionPublic(
                        area_code=row[0],
                        code=row[1],
                        name=row[2],
                        sort_order=row[3],
                    )
                    for row in cur.fetchall()
                ]
        return EmployeeCatalogResponse(
            areas=areas,
            positions=positions or self._positions,
        )

    def validate_area_position(self, area_code: str, position_code: str) -> tuple[str, str, str, str]:
        area_code = area_code.strip().upper()
        position_code = position_code.strip().upper()
        catalog = self.get_catalog()
        area = next((item for item in catalog.areas if item.code == area_code), None)
        if area is None:
            raise ValueError(f"Área '{area_code}' no existe en el catálogo.")
        position = next(
            (
                item
                for item in catalog.positions
                if item.area_code == area_code and item.code == position_code
            ),
            None,
        )
        if position is None:
            raise ValueError(
                f"Cargo '{position_code}' no existe para el área '{area_code}'.",
            )
        return area_code, position_code, area.name, position.name

    def preview_next_code(self, area_code: str, position_code: str) -> NextEmployeeCodeResponse:
        area_code, position_code, area_name, position_name = self.validate_area_position(
            area_code,
            position_code,
        )
        correlativo = self._next_correlativo(area_code, position_code)
        employee_code = self._format_code(area_code, position_code, correlativo)
        return NextEmployeeCodeResponse(
            area_code=area_code,
            area_name=area_name,
            position_code=position_code,
            position_name=position_name,
            employee_code=employee_code,
            correlativo=correlativo,
        )

    def allocate_employee_code(self, area_code: str, position_code: str) -> NextEmployeeCodeResponse:
        """Genera el siguiente código disponible (uso atómico al registrar)."""
        return self.preview_next_code(area_code, position_code)

    def _next_correlativo(self, area_code: str, position_code: str) -> int:
        prefix = f"{area_code}-{position_code}-"
        existing = self._list_existing_codes(prefix)
        max_value = 0
        for code in existing:
            match = _CODE_PATTERN.match(code)
            if not match:
                continue
            if match.group(1) != area_code or match.group(2) != position_code:
                continue
            max_value = max(max_value, int(match.group(3)))
        return max_value + 1

    def _list_existing_codes(self, prefix: str) -> list[str]:
        if settings.storage_backend.lower() == "supabase":
            return self._list_existing_codes_db(prefix)
        return self._list_existing_codes_local(prefix)

    def _list_existing_codes_db(self, prefix: str) -> list[str]:
        with get_conn() as conn:
            org_id = resolve_org_id(conn)
            with conn.cursor() as cur:
                cur.execute(
                    """
                    select person_id
                    from public.persons
                    where org_id = %s and person_id like %s
                    """,
                    (org_id, f"{prefix}%"),
                )
                return [row[0] for row in cur.fetchall()]

    def _list_existing_codes_local(self, prefix: str) -> list[str]:
        from app.services.embedding_store import get_embedding_store

        store = get_embedding_store()
        codes: set[str] = set()
        for face in store.list_public():
            if face.person_id.startswith(prefix):
                codes.add(face.person_id)
            employee_code = face.employee_code or ""
            if employee_code.startswith(prefix):
                codes.add(employee_code)
        token_store_path = settings.resolved_data_dir / "employee_registration_tokens.json"
        if token_store_path.exists():
            try:
                payload = json.loads(token_store_path.read_text(encoding="utf-8"))
            except json.JSONDecodeError:
                payload = {"workers": []}
            for worker in payload.get("workers", []):
                employee_code = str(worker.get("employee_code") or "")
                if employee_code.startswith(prefix):
                    codes.add(employee_code)
        return list(codes)

    @staticmethod
    def _format_code(area_code: str, position_code: str, correlativo: int) -> str:
        return f"{area_code}-{position_code}-{correlativo:04d}"


_catalog_service: EmployeeCatalogService | None = None


def get_employee_catalog_service() -> EmployeeCatalogService:
    global _catalog_service
    if _catalog_service is None:
        _catalog_service = EmployeeCatalogService()
    return _catalog_service
