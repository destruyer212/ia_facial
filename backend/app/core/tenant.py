from __future__ import annotations

import re
from contextvars import ContextVar

from app.core.config import settings

_ORG_CODE_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_-]{0,31}$")
_active_org_code: ContextVar[str | None] = ContextVar("active_org_code", default=None)


def normalize_org_code(value: str | None) -> str:
    code = (value or settings.default_org_code).strip()
    if not code:
        code = settings.default_org_code
    if not _ORG_CODE_RE.match(code):
        raise ValueError("El codigo de empresa debe ser alfanumerico y de hasta 32 caracteres.")
    return code.lower()


def get_active_org_code() -> str:
    return normalize_org_code(_active_org_code.get())


def set_active_org_code(value: str | None):
    return _active_org_code.set(normalize_org_code(value))


def reset_active_org_code(token) -> None:
    _active_org_code.reset(token)
