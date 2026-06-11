from fastapi import APIRouter, HTTPException, Query

from app.schemas.employee import EmployeeCatalogResponse, NextEmployeeCodeResponse
from app.schemas.registration import (
    PreRegisterEmployeeRequest,
    PreRegisterEmployeeResponse,
    RegistrationTokenResponse,
    RegistrationWorkersResponse,
)
from app.services.employee_catalog_service import get_employee_catalog_service
from app.services.registration_token_service import get_registration_token_service

router = APIRouter()
catalog_service = get_employee_catalog_service()
registration_service = get_registration_token_service()


@router.get("/catalog", response_model=EmployeeCatalogResponse)
def get_employee_catalog() -> EmployeeCatalogResponse:
    return catalog_service.get_catalog()


@router.get("/next-code", response_model=NextEmployeeCodeResponse)
def get_next_employee_code(
    area_code: str = Query(..., min_length=2, max_length=2),
    position_code: str = Query(..., min_length=2, max_length=2),
) -> NextEmployeeCodeResponse:
    try:
        return catalog_service.preview_next_code(area_code, position_code)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/pre-registrations", response_model=RegistrationWorkersResponse)
def list_pre_registered_workers() -> RegistrationWorkersResponse:
    return RegistrationWorkersResponse(workers=registration_service.list_workers())


@router.post("/pre-register", response_model=PreRegisterEmployeeResponse)
def pre_register_employee(payload: PreRegisterEmployeeRequest) -> PreRegisterEmployeeResponse:
    try:
        worker, email_sent, dev_token, email_message = registration_service.pre_register(payload)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return PreRegisterEmployeeResponse(
        worker=worker,
        email_sent=email_sent,
        dev_token=dev_token,
        message=(
            "Trabajador pre-registrado y token enviado."
            if email_sent
            else f"Trabajador pre-registrado. {email_message}"
        ),
    )


@router.post("/{employee_id}/send-registration-token", response_model=RegistrationTokenResponse)
def send_registration_token(employee_id: str) -> RegistrationTokenResponse:
    try:
        worker, email_sent, dev_token, email_message = registration_service.resend_token(employee_id)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return RegistrationTokenResponse(
        worker=worker,
        email_sent=email_sent,
        dev_token=dev_token,
        message="Token reenviado." if email_sent else f"Token regenerado para envio manual. {email_message}",
    )


@router.post("/{employee_id}/regenerate-registration-token", response_model=RegistrationTokenResponse)
def regenerate_registration_token(employee_id: str) -> RegistrationTokenResponse:
    try:
        worker, email_sent, dev_token, email_message = registration_service.regenerate_token(employee_id)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return RegistrationTokenResponse(
        worker=worker,
        email_sent=email_sent,
        dev_token=dev_token,
        message="Token regenerado y enviado." if email_sent else f"Token regenerado. {email_message}",
    )


@router.post("/{employee_id}/cancel-registration-token", response_model=RegistrationTokenResponse)
def cancel_registration_token(employee_id: str) -> RegistrationTokenResponse:
    try:
        worker = registration_service.cancel_token(employee_id)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return RegistrationTokenResponse(
        worker=worker,
        email_sent=False,
        dev_token=None,
        message="Token cancelado.",
    )
