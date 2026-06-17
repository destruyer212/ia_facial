from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class OrganizationSite(BaseModel):
    code: str
    name: str
    address: str | None = None
    is_active: bool = True


class OrganizationProfile(BaseModel):
    code: str
    name: str
    timezone: str = "America/Lima"
    ruc: str | None = None
    logo_url: str | None = None
    address: str | None = None
    brand_primary_color: str = "#0d9488"
    brand_accent_color: str = "#2563eb"
    brand_sidebar_color: str = "#101827"
    sites: list[OrganizationSite] = Field(default_factory=list)


class OrganizationUpdate(BaseModel):
    name: str | None = None
    timezone: str | None = None
    ruc: str | None = None
    logo_url: str | None = None
    address: str | None = None
    brand_primary_color: str | None = None
    brand_accent_color: str | None = None
    brand_sidebar_color: str | None = None
    sites: list[OrganizationSite] | None = None


class AdminArea(BaseModel):
    code: str
    name: str
    sort_order: int = 0
    is_active: bool = True


class AdminAreaCreate(BaseModel):
    code: str
    name: str
    sort_order: int = 0
    is_active: bool = True


class AdminAreaUpdate(BaseModel):
    name: str | None = None
    sort_order: int | None = None
    is_active: bool | None = None


class AdminPosition(BaseModel):
    area_code: str
    code: str
    name: str
    sort_order: int = 0
    is_active: bool = True


class AdminPositionCreate(BaseModel):
    area_code: str
    code: str
    name: str
    sort_order: int = 0
    is_active: bool = True


class AdminPositionUpdate(BaseModel):
    name: str | None = None
    sort_order: int | None = None
    is_active: bool | None = None


class AdminDevice(BaseModel):
    device_id: str
    label: str
    kind: str = "edge"
    location: str | None = None
    is_active: bool = True
    online: bool = False
    last_seen_at: datetime | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None


class AdminDeviceCreate(BaseModel):
    device_id: str
    label: str
    kind: str = "edge"
    location: str | None = None
    is_active: bool = True


class AdminDeviceUpdate(BaseModel):
    label: str | None = None
    kind: str | None = None
    location: str | None = None
    is_active: bool | None = None


class SystemSettings(BaseModel):
    storage_backend: str
    json_mode: bool
    r2_enabled: bool
    camera_device_id: str = "dashboard-camera-001"
    liveness_enabled: bool = True
    voice_enabled: bool = True
    attendance_cooldown_ms: int = Field(default=12000, ge=1000, le=120000)
    face_match_threshold: float = Field(default=0.35, ge=0.05, le=1.0)
    face_scan_match_threshold: float = Field(default=0.48, ge=0.05, le=1.0)
    default_scheduled_exit_time: str = "22:00"
    default_exit_tolerance_minutes: int = Field(default=10, ge=0, le=240)


class SystemSettingsUpdate(BaseModel):
    camera_device_id: str | None = None
    liveness_enabled: bool | None = None
    voice_enabled: bool | None = None
    attendance_cooldown_ms: int | None = Field(default=None, ge=1000, le=120000)
    face_match_threshold: float | None = Field(default=None, ge=0.05, le=1.0)
    face_scan_match_threshold: float | None = Field(default=None, ge=0.05, le=1.0)
    default_scheduled_exit_time: str | None = None
    default_exit_tolerance_minutes: int | None = Field(default=None, ge=0, le=240)


class AdminOverviewResponse(BaseModel):
    organization: OrganizationProfile
    areas: list[AdminArea]
    positions: list[AdminPosition]
    devices: list[AdminDevice]
    settings: SystemSettings
    warnings: list[str] = Field(default_factory=list)
    raw: dict[str, Any] = Field(default_factory=dict)


class AdminMessageResponse(BaseModel):
    message: str


class OrganizationResponse(AdminMessageResponse):
    organization: OrganizationProfile


class AreaResponse(AdminMessageResponse):
    area: AdminArea


class PositionResponse(AdminMessageResponse):
    position: AdminPosition


class DeviceResponse(AdminMessageResponse):
    device: AdminDevice


class SettingsResponse(AdminMessageResponse):
    settings: SystemSettings
