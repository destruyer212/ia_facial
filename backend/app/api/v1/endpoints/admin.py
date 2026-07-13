from fastapi import APIRouter, HTTPException

from app.schemas.admin import (
    AdminAreaCreate,
    AdminAreaUpdate,
    AdminDeviceCreate,
    AdminDeviceUpdate,
    AdminOverviewResponse,
    AdminPositionCreate,
    AdminPositionUpdate,
    AreaResponse,
    DeviceResponse,
    OrganizationCreate,
    OrganizationResponse,
    OrganizationUpdate,
    OrganizationsResponse,
    PositionResponse,
    SettingsResponse,
    SystemSettingsUpdate,
)
from app.services.admin_service import get_admin_service

router = APIRouter()
admin_service = get_admin_service()


@router.get("/overview", response_model=AdminOverviewResponse)
def get_admin_overview() -> AdminOverviewResponse:
    return admin_service.overview()


@router.get("/organizations", response_model=OrganizationsResponse)
def list_organizations() -> OrganizationsResponse:
    return OrganizationsResponse(organizations=admin_service.list_organizations())


@router.post("/organizations", response_model=OrganizationResponse)
def create_organization(payload: OrganizationCreate) -> OrganizationResponse:
    try:
        organization = admin_service.create_organization(payload)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return OrganizationResponse(
        organization=organization,
        message=f"Empresa {organization.code} creada.",
    )


@router.patch("/organization", response_model=OrganizationResponse)
def update_organization(payload: OrganizationUpdate) -> OrganizationResponse:
    try:
        organization = admin_service.update_organization(payload)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return OrganizationResponse(
        organization=organization,
        message="Organizacion actualizada.",
    )


@router.post("/areas", response_model=AreaResponse)
def create_area(payload: AdminAreaCreate) -> AreaResponse:
    try:
        area = admin_service.create_area(payload)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return AreaResponse(area=area, message=f"Area {area.code} guardada.")


@router.patch("/areas/{area_code}", response_model=AreaResponse)
def update_area(area_code: str, payload: AdminAreaUpdate) -> AreaResponse:
    try:
        area = admin_service.update_area(area_code, payload)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return AreaResponse(area=area, message=f"Area {area.code} actualizada.")


@router.post("/positions", response_model=PositionResponse)
def create_position(payload: AdminPositionCreate) -> PositionResponse:
    try:
        position = admin_service.create_position(payload)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return PositionResponse(
        position=position,
        message=f"Cargo {position.area_code}-{position.code} guardado.",
    )


@router.patch("/positions/{area_code}/{position_code}", response_model=PositionResponse)
def update_position(
    area_code: str,
    position_code: str,
    payload: AdminPositionUpdate,
) -> PositionResponse:
    try:
        position = admin_service.update_position(area_code, position_code, payload)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return PositionResponse(
        position=position,
        message=f"Cargo {position.area_code}-{position.code} actualizado.",
    )


@router.post("/devices", response_model=DeviceResponse)
def create_device(payload: AdminDeviceCreate) -> DeviceResponse:
    try:
        device = admin_service.create_device(payload)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return DeviceResponse(device=device, message=f"Dispositivo {device.device_id} guardado.")


@router.patch("/devices/{device_id}", response_model=DeviceResponse)
def update_device(device_id: str, payload: AdminDeviceUpdate) -> DeviceResponse:
    try:
        device = admin_service.update_device(device_id, payload)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return DeviceResponse(device=device, message=f"Dispositivo {device.device_id} actualizado.")


@router.patch("/settings", response_model=SettingsResponse)
def update_settings(payload: SystemSettingsUpdate) -> SettingsResponse:
    try:
        current = admin_service.update_system_settings(payload)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return SettingsResponse(settings=current, message="Configuracion guardada.")
