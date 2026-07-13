from fastapi import Header, HTTPException, Query, Request, status

from app.core.config import settings
from app.core.tenant import normalize_org_code, set_active_org_code
from app.schemas.auth import AuthOrganization
from app.services.auth_service import AuthenticatedUser, get_auth_service


def _extract_bearer_token(authorization: str | None, access_token: str | None) -> str | None:
    if access_token:
        return access_token.strip()
    if not authorization:
        return None
    scheme, _, token = authorization.partition(" ")
    if scheme.lower() != "bearer" or not token.strip():
        return None
    return token.strip()


def get_current_user(
    request: Request,
    authorization: str | None = Header(default=None),
    access_token: str | None = Query(default=None),
) -> AuthenticatedUser:
    requested_org = request.headers.get("x-org-code") or request.query_params.get("org_code")
    if not settings.auth_required:
        org_code = normalize_org_code(requested_org or settings.default_org_code)
        set_active_org_code(org_code)
        return AuthenticatedUser(
            user_id="dev",
            email=settings.auth_default_admin_email,
            full_name=settings.auth_default_admin_name,
            role="platform_admin",
            org_code=org_code,
            organizations=[
                AuthOrganization(
                    code=org_code,
                    name=org_code,
                    role="platform_admin",
                )
            ],
        )

    token = _extract_bearer_token(authorization, access_token)
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Inicia sesion para continuar.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    try:
        user = get_auth_service().authenticate_token(token)
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(exc),
            headers={"WWW-Authenticate": "Bearer"},
        ) from exc

    if requested_org:
        requested_org = normalize_org_code(requested_org)
        if user.role != "platform_admin" and requested_org != user.org_code:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Tu usuario no tiene acceso a esa empresa.",
            )
        user.org_code = requested_org

    set_active_org_code(user.org_code)
    return user
