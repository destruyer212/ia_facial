from datetime import datetime

from pydantic import BaseModel, Field


class PreRegisterEmployeeRequest(BaseModel):
    name: str
    dni: str = Field(min_length=4, max_length=20)
    email: str
    area_code: str = Field(min_length=2, max_length=2)
    position_code: str = Field(min_length=2, max_length=2)
    shift_code: str = Field(min_length=2, max_length=2)
    token_expires_hours: int = Field(default=48, ge=1, le=168)


class RegistrationWorkerPublic(BaseModel):
    employee_id: str
    employee_code: str
    name: str
    dni: str
    email: str
    area_code: str
    area_name: str
    position_code: str
    position_name: str
    shift_code: str
    shift_name: str
    schedule_label: str | None = None
    registration_status: str
    face_registered_at: datetime | None = None
    created_at: datetime
    updated_at: datetime
    token_status: str | None = None
    token_expires_at: datetime | None = None
    token_sent_to_email: str | None = None
    token_sent_at: datetime | None = None


class PreRegisterEmployeeResponse(BaseModel):
    worker: RegistrationWorkerPublic
    message: str
    email_sent: bool
    dev_token: str | None = None


class RegistrationTokenResponse(BaseModel):
    worker: RegistrationWorkerPublic
    message: str
    email_sent: bool
    dev_token: str | None = None


class ValidateRegistrationTokenRequest(BaseModel):
    token: str = Field(min_length=8, max_length=256)


class ValidateRegistrationTokenResponse(BaseModel):
    valid: bool
    worker: RegistrationWorkerPublic | None = None
    registration_session: str | None = None
    message: str


class CompleteRegistrationTokenRequest(BaseModel):
    token: str = Field(min_length=8, max_length=256)


class CompleteRegistrationTokenResponse(BaseModel):
    worker: RegistrationWorkerPublic
    message: str


class RegistrationWorkersResponse(BaseModel):
    workers: list[RegistrationWorkerPublic]
