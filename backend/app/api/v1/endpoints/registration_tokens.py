from fastapi import APIRouter, HTTPException, Request

from app.schemas.registration import (
    CompleteRegistrationTokenRequest,
    CompleteRegistrationTokenResponse,
    ValidateRegistrationTokenRequest,
    ValidateRegistrationTokenResponse,
)
from app.services.registration_token_service import get_registration_token_service
from app.services.token_rate_limiter import get_token_validation_rate_limiter

router = APIRouter()
registration_service = get_registration_token_service()
rate_limiter = get_token_validation_rate_limiter()


def _client_key(request: Request) -> str:
    forwarded = request.headers.get("x-forwarded-for", "").split(",")[0].strip()
    if forwarded:
        return forwarded
    if request.client and request.client.host:
        return request.client.host
    return "unknown"


@router.post("/validate", response_model=ValidateRegistrationTokenResponse)
def validate_registration_token(
    payload: ValidateRegistrationTokenRequest,
    request: Request,
) -> ValidateRegistrationTokenResponse:
    client_key = _client_key(request)
    try:
        rate_limiter.check(client_key)
    except ValueError as exc:
        raise HTTPException(status_code=429, detail=str(exc)) from exc

    source = request.headers.get("x-client-source", "api")
    result = registration_service.validate_token(payload.token, source=source)
    if not result.valid:
        rate_limiter.record_failure(client_key)
    else:
        rate_limiter.reset(client_key)
    return result


@router.post("/complete", response_model=CompleteRegistrationTokenResponse)
def complete_registration_token(
    payload: CompleteRegistrationTokenRequest,
) -> CompleteRegistrationTokenResponse:
    try:
        worker = registration_service.complete_token(payload.token)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return CompleteRegistrationTokenResponse(
        worker=worker,
        message="Registro facial completado correctamente.",
    )
