from __future__ import annotations

import json
import re
from datetime import UTC, datetime, timedelta, time
from pathlib import Path
from typing import Any

from app.core.config import settings
from app.schemas.admin import (
    AdminArea,
    AdminAreaCreate,
    AdminAreaUpdate,
    AdminDevice,
    AdminDeviceCreate,
    AdminDeviceUpdate,
    AdminOverviewResponse,
    AdminPosition,
    AdminPositionCreate,
    AdminPositionUpdate,
    OrganizationProfile,
    OrganizationSite,
    OrganizationUpdate,
    SystemSettings,
    SystemSettingsUpdate,
)
from app.services.supabase_db import get_conn, resolve_org_id

_CODE_RE = re.compile(r"^[A-Z0-9]{2}$")


class AdminService:
    """Small admin facade for Phase 1.

    Local JSON keeps the desktop MVP usable without Postgres. When Supabase is
    enabled, catalog and device CRUD use the existing business tables.
    """

    def __init__(self, path: Path | None = None) -> None:
        data_dir = settings.resolved_data_dir
        data_dir.mkdir(parents=True, exist_ok=True)
        self.path = path or data_dir / "enterprise_admin.json"
        self.seed_catalog_path = Path(__file__).resolve().parent.parent / "data" / "employee_catalog.json"

    def overview(self) -> AdminOverviewResponse:
        warnings: list[str] = []
        try:
            organization = self.get_organization()
        except Exception as exc:
            warnings.append(f"No se pudo leer organizacion en Supabase: {exc}")
            organization = self._local_organization()
        try:
            areas = self.list_areas()
            positions = self.list_positions()
        except Exception as exc:
            warnings.append(f"No se pudo leer areas/cargos en Supabase: {exc}")
            areas = self._local_areas()
            positions = self._local_positions()
        try:
            devices = self.list_devices()
        except Exception as exc:
            warnings.append(f"No se pudo leer dispositivos en Supabase: {exc}")
            devices = self._local_devices()
        return AdminOverviewResponse(
            organization=organization,
            areas=areas,
            positions=positions,
            devices=devices,
            settings=self.get_system_settings(),
            warnings=warnings,
            raw={"storage_backend": settings.storage_backend},
        )

    def get_organization(self) -> OrganizationProfile:
        if self._uses_supabase():
            return self._get_organization_db()
        return self._local_organization()

    def update_organization(self, payload: OrganizationUpdate) -> OrganizationProfile:
        if self._uses_supabase():
            self._update_organization_db(payload)
        state = self._load_state()
        current = OrganizationProfile(**state["organization"])
        updates = payload.model_dump(exclude_unset=True)
        merged = current.model_copy(update=updates)
        state["organization"] = merged.model_dump(mode="json")
        self._save_state(state)
        return self.get_organization()

    def list_areas(self, include_inactive: bool = True) -> list[AdminArea]:
        areas = self._list_areas_db() if self._uses_supabase() else self._local_areas()
        if not include_inactive:
            areas = [area for area in areas if area.is_active]
        return sorted(areas, key=lambda item: (item.sort_order, item.code))

    def list_positions(self, include_inactive: bool = True) -> list[AdminPosition]:
        positions = self._list_positions_db() if self._uses_supabase() else self._local_positions()
        if not include_inactive:
            positions = [position for position in positions if position.is_active]
        return sorted(positions, key=lambda item: (item.area_code, item.sort_order, item.code))

    def get_active_catalog(self) -> dict[str, list[dict[str, Any]]]:
        return {
            "areas": [
                {"code": area.code, "name": area.name, "sort_order": area.sort_order}
                for area in self.list_areas(include_inactive=False)
            ],
            "positions": [
                {
                    "area_code": position.area_code,
                    "code": position.code,
                    "name": position.name,
                    "sort_order": position.sort_order,
                }
                for position in self.list_positions(include_inactive=False)
            ],
        }

    def create_area(self, payload: AdminAreaCreate) -> AdminArea:
        area = AdminArea(
            code=self._normalize_code(payload.code),
            name=payload.name.strip(),
            sort_order=payload.sort_order,
            is_active=payload.is_active,
        )
        if not area.name:
            raise ValueError("El nombre del area es obligatorio.")
        if self._uses_supabase():
            self._upsert_area_db(area)
        else:
            state = self._load_state()
            state["areas"] = [
                existing for existing in state["areas"] if existing["code"] != area.code
            ]
            state["areas"].append(area.model_dump(mode="json"))
            self._save_state(state)
        return area

    def update_area(self, area_code: str, payload: AdminAreaUpdate) -> AdminArea:
        area_code = self._normalize_code(area_code)
        if self._uses_supabase():
            self._update_area_db(area_code, payload)
            return next(area for area in self.list_areas() if area.code == area_code)

        state = self._load_state()
        areas = [AdminArea(**item) for item in state["areas"]]
        for index, area in enumerate(areas):
            if area.code != area_code:
                continue
            updates = payload.model_dump(exclude_unset=True)
            if "name" in updates and updates["name"] is not None:
                updates["name"] = updates["name"].strip()
                if not updates["name"]:
                    raise ValueError("El nombre del area es obligatorio.")
            areas[index] = area.model_copy(update=updates)
            state["areas"] = [item.model_dump(mode="json") for item in areas]
            self._save_state(state)
            return areas[index]
        raise LookupError(f"No existe area '{area_code}'.")

    def create_position(self, payload: AdminPositionCreate) -> AdminPosition:
        position = AdminPosition(
            area_code=self._normalize_code(payload.area_code),
            code=self._normalize_code(payload.code),
            name=payload.name.strip(),
            sort_order=payload.sort_order,
            is_active=payload.is_active,
        )
        if not position.name:
            raise ValueError("El nombre del cargo es obligatorio.")
        if not any(area.code == position.area_code for area in self.list_areas()):
            raise ValueError(f"No existe area '{position.area_code}'.")
        if self._uses_supabase():
            self._upsert_position_db(position)
        else:
            state = self._load_state()
            state["positions"] = [
                existing
                for existing in state["positions"]
                if not (
                    existing["area_code"] == position.area_code
                    and existing["code"] == position.code
                )
            ]
            state["positions"].append(position.model_dump(mode="json"))
            self._save_state(state)
        return position

    def update_position(
        self,
        area_code: str,
        position_code: str,
        payload: AdminPositionUpdate,
    ) -> AdminPosition:
        area_code = self._normalize_code(area_code)
        position_code = self._normalize_code(position_code)
        if self._uses_supabase():
            self._update_position_db(area_code, position_code, payload)
            return next(
                position
                for position in self.list_positions()
                if position.area_code == area_code and position.code == position_code
            )

        state = self._load_state()
        positions = [AdminPosition(**item) for item in state["positions"]]
        for index, position in enumerate(positions):
            if position.area_code != area_code or position.code != position_code:
                continue
            updates = payload.model_dump(exclude_unset=True)
            if "name" in updates and updates["name"] is not None:
                updates["name"] = updates["name"].strip()
                if not updates["name"]:
                    raise ValueError("El nombre del cargo es obligatorio.")
            positions[index] = position.model_copy(update=updates)
            state["positions"] = [item.model_dump(mode="json") for item in positions]
            self._save_state(state)
            return positions[index]
        raise LookupError(f"No existe cargo '{position_code}' en area '{area_code}'.")

    def list_devices(self) -> list[AdminDevice]:
        devices = self._list_devices_db() if self._uses_supabase() else self._local_devices()
        now = datetime.now(UTC)
        normalized: list[AdminDevice] = []
        for device in devices:
            last_seen = ensure_aware_utc(device.last_seen_at) if device.last_seen_at else None
            normalized.append(
                device.model_copy(
                    update={
                        "last_seen_at": last_seen,
                        "online": bool(last_seen and now - last_seen <= timedelta(minutes=5)),
                    }
                )
            )
        return sorted(normalized, key=lambda item: item.device_id)

    def create_device(self, payload: AdminDeviceCreate) -> AdminDevice:
        now = datetime.now(UTC)
        device = AdminDevice(
            device_id=payload.device_id.strip(),
            label=payload.label.strip(),
            kind=(payload.kind or "edge").strip() or "edge",
            location=payload.location.strip() if payload.location else None,
            is_active=payload.is_active,
            created_at=now,
            updated_at=now,
        )
        if not device.device_id or not device.label:
            raise ValueError("device_id y nombre son obligatorios.")
        if self._uses_supabase():
            self._upsert_device_db(device)
        else:
            state = self._load_state()
            state["devices"] = [
                existing
                for existing in state["devices"]
                if existing["device_id"] != device.device_id
            ]
            state["devices"].append(device.model_dump(mode="json"))
            self._save_state(state)
        return next(item for item in self.list_devices() if item.device_id == device.device_id)

    def update_device(self, device_id: str, payload: AdminDeviceUpdate) -> AdminDevice:
        device_id = device_id.strip()
        if self._uses_supabase():
            self._update_device_db(device_id, payload)
            return next(device for device in self.list_devices() if device.device_id == device_id)

        state = self._load_state()
        devices = [AdminDevice(**item) for item in state["devices"]]
        for index, device in enumerate(devices):
            if device.device_id != device_id:
                continue
            updates = payload.model_dump(exclude_unset=True)
            for key in ("label", "kind", "location"):
                if key in updates and isinstance(updates[key], str):
                    updates[key] = updates[key].strip() or None
            updates["updated_at"] = datetime.now(UTC)
            devices[index] = device.model_copy(update=updates)
            state["devices"] = [item.model_dump(mode="json") for item in devices]
            self._save_state(state)
            return next(item for item in self.list_devices() if item.device_id == device_id)
        raise LookupError(f"No existe dispositivo '{device_id}'.")

    def get_system_settings(self) -> SystemSettings:
        state = self._load_state()
        defaults = self._default_settings()
        merged = {**defaults, **state.get("settings", {})}
        merged["storage_backend"] = settings.storage_backend
        merged["json_mode"] = settings.storage_backend.lower() != "supabase"
        merged["r2_enabled"] = settings.r2_enabled
        return SystemSettings(**merged)

    def update_system_settings(self, payload: SystemSettingsUpdate) -> SystemSettings:
        updates = payload.model_dump(exclude_unset=True)
        if "default_scheduled_exit_time" in updates and updates["default_scheduled_exit_time"]:
            time.fromisoformat(str(updates["default_scheduled_exit_time"]))
        state = self._load_state()
        settings_payload = state.get("settings", {})
        settings_payload.update(updates)
        state["settings"] = settings_payload
        self._save_state(state)
        return self.get_system_settings()

    def _get_organization_db(self) -> OrganizationProfile:
        local = self._local_organization()
        with get_conn() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    select code, name, timezone
                    from public.organizations
                    where code = %s
                    limit 1
                    """,
                    (settings.default_org_code,),
                )
                row = cur.fetchone()
        if not row:
            return local
        return local.model_copy(update={"code": row[0], "name": row[1], "timezone": row[2]})

    def _update_organization_db(self, payload: OrganizationUpdate) -> None:
        fields: list[str] = []
        values: list[object] = []
        if payload.name is not None:
            fields.append("name = %s")
            values.append(payload.name.strip())
        if payload.timezone is not None:
            fields.append("timezone = %s")
            values.append(payload.timezone.strip())
        if not fields:
            return
        fields.append("updated_at = now()")
        values.append(settings.default_org_code)
        with get_conn() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    f"""
                    update public.organizations
                    set {", ".join(fields)}
                    where code = %s
                    """,
                    values,
                )

    def _list_areas_db(self) -> list[AdminArea]:
        with get_conn() as conn:
            org_id = resolve_org_id(conn)
            with conn.cursor() as cur:
                cur.execute(
                    """
                    select area_code, name, sort_order, is_active
                    from public.org_areas
                    where org_id = %s
                    order by sort_order, area_code
                    """,
                    (org_id,),
                )
                rows = cur.fetchall()
        return [
            AdminArea(code=row[0], name=row[1], sort_order=row[2], is_active=bool(row[3]))
            for row in rows
        ]

    def _list_positions_db(self) -> list[AdminPosition]:
        with get_conn() as conn:
            org_id = resolve_org_id(conn)
            with conn.cursor() as cur:
                cur.execute(
                    """
                    select area_code, position_code, name, sort_order, is_active
                    from public.org_positions
                    where org_id = %s
                    order by area_code, sort_order, position_code
                    """,
                    (org_id,),
                )
                rows = cur.fetchall()
        return [
            AdminPosition(
                area_code=row[0],
                code=row[1],
                name=row[2],
                sort_order=row[3],
                is_active=bool(row[4]),
            )
            for row in rows
        ]

    def _upsert_area_db(self, area: AdminArea) -> None:
        with get_conn() as conn:
            org_id = resolve_org_id(conn)
            with conn.cursor() as cur:
                cur.execute(
                    """
                    insert into public.org_areas
                      (org_id, area_code, name, sort_order, is_active)
                    values (%s, %s, %s, %s, %s)
                    on conflict (org_id, area_code) do update set
                      name = excluded.name,
                      sort_order = excluded.sort_order,
                      is_active = excluded.is_active,
                      updated_at = now()
                    """,
                    (org_id, area.code, area.name, area.sort_order, area.is_active),
                )

    def _update_area_db(self, area_code: str, payload: AdminAreaUpdate) -> None:
        updates = payload.model_dump(exclude_unset=True)
        if not updates:
            return
        fields: list[str] = []
        values: list[object] = []
        for key, value in updates.items():
            if key == "name" and value is not None:
                value = str(value).strip()
                if not value:
                    raise ValueError("El nombre del area es obligatorio.")
            fields.append(f"{key} = %s")
            values.append(value)
        fields.append("updated_at = now()")
        with get_conn() as conn:
            org_id = resolve_org_id(conn)
            values.extend([org_id, area_code])
            with conn.cursor() as cur:
                cur.execute(
                    f"""
                    update public.org_areas
                    set {", ".join(fields)}
                    where org_id = %s and area_code = %s
                    """,
                    values,
                )
                if cur.rowcount == 0:
                    raise LookupError(f"No existe area '{area_code}'.")

    def _upsert_position_db(self, position: AdminPosition) -> None:
        with get_conn() as conn:
            org_id = resolve_org_id(conn)
            with conn.cursor() as cur:
                cur.execute(
                    """
                    insert into public.org_positions
                      (org_id, area_code, position_code, name, sort_order, is_active)
                    values (%s, %s, %s, %s, %s, %s)
                    on conflict (org_id, area_code, position_code) do update set
                      name = excluded.name,
                      sort_order = excluded.sort_order,
                      is_active = excluded.is_active,
                      updated_at = now()
                    """,
                    (
                        org_id,
                        position.area_code,
                        position.code,
                        position.name,
                        position.sort_order,
                        position.is_active,
                    ),
                )

    def _update_position_db(
        self,
        area_code: str,
        position_code: str,
        payload: AdminPositionUpdate,
    ) -> None:
        updates = payload.model_dump(exclude_unset=True)
        if not updates:
            return
        fields: list[str] = []
        values: list[object] = []
        for key, value in updates.items():
            if key == "name" and value is not None:
                value = str(value).strip()
                if not value:
                    raise ValueError("El nombre del cargo es obligatorio.")
            fields.append(f"{key} = %s")
            values.append(value)
        fields.append("updated_at = now()")
        with get_conn() as conn:
            org_id = resolve_org_id(conn)
            values.extend([org_id, area_code, position_code])
            with conn.cursor() as cur:
                cur.execute(
                    f"""
                    update public.org_positions
                    set {", ".join(fields)}
                    where org_id = %s and area_code = %s and position_code = %s
                    """,
                    values,
                )
                if cur.rowcount == 0:
                    raise LookupError(f"No existe cargo '{position_code}' en area '{area_code}'.")

    def _list_devices_db(self) -> list[AdminDevice]:
        with get_conn() as conn:
            org_id = resolve_org_id(conn)
            with conn.cursor() as cur:
                cur.execute(
                    """
                    select
                      d.device_id,
                      d.label,
                      d.kind,
                      d.location,
                      d.is_active,
                      d.created_at,
                      d.updated_at,
                      max(a.captured_at) as last_seen_at
                    from public.devices d
                    left join public.attendance_events a
                      on a.org_id = d.org_id and a.device_id = d.device_id
                    where d.org_id = %s
                    group by d.device_id, d.label, d.kind, d.location,
                             d.is_active, d.created_at, d.updated_at
                    order by d.device_id
                    """,
                    (org_id,),
                )
                rows = cur.fetchall()
        return [
            AdminDevice(
                device_id=row[0],
                label=row[1],
                kind=row[2],
                location=row[3],
                is_active=bool(row[4]),
                created_at=row[5],
                updated_at=row[6],
                last_seen_at=row[7],
            )
            for row in rows
        ]

    def _upsert_device_db(self, device: AdminDevice) -> None:
        with get_conn() as conn:
            org_id = resolve_org_id(conn)
            with conn.cursor() as cur:
                cur.execute(
                    """
                    insert into public.devices
                      (device_id, org_id, label, kind, location, is_active)
                    values (%s, %s, %s, %s, %s, %s)
                    on conflict (device_id) do update set
                      label = excluded.label,
                      kind = excluded.kind,
                      location = excluded.location,
                      is_active = excluded.is_active,
                      updated_at = now()
                    """,
                    (
                        device.device_id,
                        org_id,
                        device.label,
                        device.kind,
                        device.location,
                        device.is_active,
                    ),
                )

    def _update_device_db(self, device_id: str, payload: AdminDeviceUpdate) -> None:
        updates = payload.model_dump(exclude_unset=True)
        if not updates:
            return
        fields: list[str] = []
        values: list[object] = []
        for key, value in updates.items():
            if key in {"label", "kind", "location"} and value is not None:
                value = str(value).strip()
                if key in {"label", "kind"} and not value:
                    raise ValueError(f"{key} es obligatorio.")
            fields.append(f"{key} = %s")
            values.append(value)
        fields.append("updated_at = now()")
        with get_conn() as conn:
            org_id = resolve_org_id(conn)
            values.extend([device_id, org_id])
            with conn.cursor() as cur:
                cur.execute(
                    f"""
                    update public.devices
                    set {", ".join(fields)}
                    where device_id = %s and org_id = %s
                    """,
                    values,
                )
                if cur.rowcount == 0:
                    raise LookupError(f"No existe dispositivo '{device_id}'.")

    def _local_organization(self) -> OrganizationProfile:
        return OrganizationProfile(**self._load_state()["organization"])

    def _local_areas(self) -> list[AdminArea]:
        return [AdminArea(**item) for item in self._load_state()["areas"]]

    def _local_positions(self) -> list[AdminPosition]:
        return [AdminPosition(**item) for item in self._load_state()["positions"]]

    def _local_devices(self) -> list[AdminDevice]:
        state = self._load_state()
        by_id = {item["device_id"]: AdminDevice(**item) for item in state["devices"]}
        for device_id, last_seen in self._load_local_device_activity().items():
            if device_id in by_id:
                by_id[device_id] = by_id[device_id].model_copy(update={"last_seen_at": last_seen})
            else:
                by_id[device_id] = AdminDevice(
                    device_id=device_id,
                    label=device_id,
                    kind="edge",
                    location=None,
                    is_active=True,
                    last_seen_at=last_seen,
                )
        return list(by_id.values())

    def _load_local_device_activity(self) -> dict[str, datetime]:
        events_path = settings.resolved_data_dir / "attendance_events.json"
        if not events_path.exists():
            return {}
        try:
            payload = json.loads(events_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            return {}
        seen: dict[str, datetime] = {}
        for event in payload:
            device_id = str(event.get("device_id") or "").strip()
            captured_at = parse_datetime(event.get("captured_at"))
            if not device_id or captured_at is None:
                continue
            if device_id not in seen or captured_at > seen[device_id]:
                seen[device_id] = captured_at
        return seen

    def _load_state(self) -> dict[str, Any]:
        defaults = self._default_state()
        if not self.path.exists():
            self._save_state(defaults)
            return defaults
        try:
            state = json.loads(self.path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            state = {}
        merged = {
            "organization": {**defaults["organization"], **state.get("organization", {})},
            "areas": state.get("areas") or defaults["areas"],
            "positions": state.get("positions") or defaults["positions"],
            "devices": state.get("devices") or defaults["devices"],
            "settings": {**defaults["settings"], **state.get("settings", {})},
        }
        return merged

    def _save_state(self, state: dict[str, Any]) -> None:
        self.path.write_text(json.dumps(state, indent=2, ensure_ascii=False), encoding="utf-8")

    def _default_state(self) -> dict[str, Any]:
        seed = json.loads(self.seed_catalog_path.read_text(encoding="utf-8"))
        areas = [
            AdminArea(
                code=item["code"],
                name=item["name"],
                sort_order=item.get("sort_order", 0),
                is_active=True,
            ).model_dump(mode="json")
            for item in seed.get("areas", [])
        ]
        positions = [
            AdminPosition(
                area_code=item["area_code"],
                code=item["code"],
                name=item["name"],
                sort_order=item.get("sort_order", 0),
                is_active=True,
            ).model_dump(mode="json")
            for item in seed.get("positions", [])
        ]
        now = datetime.now(UTC)
        return {
            "organization": OrganizationProfile(
                code=settings.default_org_code,
                name="IA Facial Demo",
                timezone="America/Lima",
                ruc="",
                logo_url="",
                address="",
                brand_primary_color="#0d9488",
                brand_accent_color="#2563eb",
                brand_sidebar_color="#101827",
                sites=[
                    OrganizationSite(
                        code="HQ",
                        name="Oficina Principal",
                        address="",
                        is_active=True,
                    )
                ],
            ).model_dump(mode="json"),
            "areas": areas,
            "positions": positions,
            "devices": [
                AdminDevice(
                    device_id="dashboard-camera-001",
                    label="Dashboard Camara",
                    kind="web",
                    location="Oficina Principal",
                    created_at=now,
                    updated_at=now,
                ).model_dump(mode="json"),
                AdminDevice(
                    device_id="edge-windows-001",
                    label="Edge Windows",
                    kind="edge",
                    location="Oficina Principal",
                    created_at=now,
                    updated_at=now,
                ).model_dump(mode="json"),
            ],
            "settings": self._default_settings(),
        }

    def _default_settings(self) -> dict[str, Any]:
        return {
            "storage_backend": settings.storage_backend,
            "json_mode": settings.storage_backend.lower() != "supabase",
            "r2_enabled": settings.r2_enabled,
            "camera_device_id": "dashboard-camera-001",
            "liveness_enabled": True,
            "voice_enabled": True,
            "attendance_cooldown_ms": 12000,
            "face_match_threshold": settings.face_match_threshold,
            "face_scan_match_threshold": settings.face_scan_match_threshold,
            "default_scheduled_exit_time": settings.default_scheduled_exit_time,
            "default_exit_tolerance_minutes": settings.default_exit_tolerance_minutes,
        }

    @staticmethod
    def _uses_supabase() -> bool:
        return settings.storage_backend.lower() == "supabase"

    @staticmethod
    def _normalize_code(value: str) -> str:
        code = value.strip().upper()
        if not _CODE_RE.match(code):
            raise ValueError("El codigo debe tener exactamente 2 caracteres alfanumericos.")
        return code


def parse_datetime(value: object) -> datetime | None:
    if not value:
        return None
    try:
        text = str(value).replace("Z", "+00:00")
        return ensure_aware_utc(datetime.fromisoformat(text))
    except ValueError:
        return None


def ensure_aware_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)


_admin_service: AdminService | None = None


def get_admin_service() -> AdminService:
    global _admin_service
    if _admin_service is None:
        _admin_service = AdminService()
    return _admin_service
