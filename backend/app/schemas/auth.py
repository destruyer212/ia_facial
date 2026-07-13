from pydantic import BaseModel


class AuthOrganization(BaseModel):
    code: str
    name: str
    role: str


class LoginRequest(BaseModel):
    email: str
    password: str
    org_code: str | None = None


class AuthUserPublic(BaseModel):
    user_id: str
    email: str
    full_name: str | None = None
    role: str
    org_code: str
    organizations: list[AuthOrganization] = []


class LoginResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_at: str
    user: AuthUserPublic


class MeResponse(BaseModel):
    user: AuthUserPublic
