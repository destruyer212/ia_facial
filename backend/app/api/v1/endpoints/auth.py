from fastapi import APIRouter, Depends, HTTPException

from app.core.auth import get_current_user
from app.schemas.auth import LoginRequest, LoginResponse, MeResponse
from app.services.auth_service import AuthenticatedUser, get_auth_service

router = APIRouter()


@router.post("/login", response_model=LoginResponse)
def login(payload: LoginRequest) -> LoginResponse:
    try:
        return get_auth_service().login(
            payload.email,
            payload.password,
            payload.org_code,
        )
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=401, detail=str(exc)) from exc


@router.get("/me", response_model=MeResponse)
def me(current_user: AuthenticatedUser = Depends(get_current_user)) -> MeResponse:
    return MeResponse(user=current_user.public())
