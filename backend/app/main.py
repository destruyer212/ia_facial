from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.openapi.docs import get_swagger_ui_html
from fastapi.responses import JSONResponse
from psycopg import OperationalError

from app.api.v1.router import api_router
from app.core.config import settings
from app.core.tenant import reset_active_org_code, set_active_org_code


def create_app() -> FastAPI:
    app = FastAPI(
        title=settings.app_name,
        version="0.1.0",
        description="MVP profesional de reconocimiento facial empresarial.",
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.middleware("http")
    async def tenant_context_middleware(request: Request, call_next):
        token = set_active_org_code(
            request.headers.get("x-org-code") or request.query_params.get("org_code")
        )
        try:
            return await call_next(request)
        finally:
            reset_active_org_code(token)

    app.include_router(api_router, prefix=settings.api_v1_prefix)

    @app.get("/api/openapi.json", include_in_schema=False)
    def public_openapi_schema() -> dict:
        return app.openapi()

    @app.get("/api/docs", include_in_schema=False)
    def public_swagger_docs():
        return get_swagger_ui_html(
            openapi_url="/api/openapi.json",
            title=f"{settings.app_name} - Swagger",
        )

    @app.exception_handler(OperationalError)
    async def database_unavailable_handler(
        _request: Request,
        exc: OperationalError,
    ) -> JSONResponse:
        detail = str(exc).strip()
        if "tenant/user" in detail and "not found" in detail:
            detail = (
                "No se pudo conectar a Supabase: proyecto o usuario del pooler incorrecto. "
                "Revisa DATABASE_URL en backend/.env (Connect → Session pooler)."
            )
        return JSONResponse(
            status_code=503,
            content={
                "detail": detail,
                "storage_backend": settings.storage_backend,
                "hint": "Usa STORAGE_BACKEND=json para desarrollo local sin Supabase.",
            },
        )

    @app.get("/", tags=["root"])
    def root() -> dict[str, str]:
        return {
            "service": settings.app_name,
            "status": "running",
            "docs": "/docs",
            "public_docs": "/api/docs",
            "api": settings.api_v1_prefix,
        }

    return app


app = create_app()
