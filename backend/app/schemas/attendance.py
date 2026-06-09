from datetime import datetime, time
from enum import Enum

from pydantic import BaseModel, Field

from app.schemas.face import MatchCandidate


class AttendanceDecision(str, Enum):
    allowed = "allowed"
    requires_reason = "requires_reason"
    approved_exception = "approved_exception"
    incident_created = "incident_created"
    face_not_recognized = "face_not_recognized"


class ExitPolicyResponse(BaseModel):
    scheduled_exit_time: time
    tolerance_minutes: int
    tolerance_end_time: time


class ReasonAnalysis(BaseModel):
    is_valid: bool
    category: str
    confidence: float = Field(ge=0.0, le=1.0)
    risk_score: float = Field(ge=0.0, le=1.0)
    explanation: str
    provider: str


class ExitAttemptRequest(BaseModel):
    person_id: str
    employee_name: str | None = None
    attempted_at: datetime | None = None
    scheduled_exit_time: time | None = None
    tolerance_minutes: int | None = Field(default=None, ge=0, le=180)
    reason: str | None = None
    source: str = "manual"


class AttendanceIncident(BaseModel):
    incident_id: str
    person_id: str
    employee_name: str | None = None
    violation_type: str
    attempted_at: datetime
    scheduled_exit_time: time
    tolerance_minutes: int
    minutes_early: int
    reason: str | None = None
    analysis: ReasonAnalysis | None = None
    severity: str
    status: str
    evidence_ref: str | None = None
    supervisor_notified: bool
    created_at: datetime


class ExitAttemptResponse(BaseModel):
    decision: AttendanceDecision
    allowed: bool
    person_id: str
    employee_name: str | None = None
    attempted_at: datetime
    policy: ExitPolicyResponse
    minutes_early: int
    reason_required: bool
    reason_analysis: ReasonAnalysis | None = None
    incident: AttendanceIncident | None = None
    message: str


class FaceExitAttemptResponse(BaseModel):
    face_matched: bool
    candidate: MatchCandidate | None = None
    attendance: ExitAttemptResponse | None = None
    message: str


class AttendanceEventCreate(BaseModel):
    person_id: str
    employee_name: str | None = None
    device_id: str
    event_type: str = "check_in"
    confidence: float = Field(ge=0.0, le=1.0)
    captured_at: datetime
    source: str = "edge"
    evidence_ref: str | None = None


class AttendanceEvent(AttendanceEventCreate):
    event_id: str
    accepted: bool
    duplicate: bool
    created_at: datetime


class AttendanceEventResponse(BaseModel):
    event: AttendanceEvent
    message: str


class AttendanceReportSummary(BaseModel):
    total: int = 0
    check_ins: int = 0
    check_outs: int = 0
    duplicates: int = 0
    rejected: int = 0


class AttendanceEventListResponse(BaseModel):
    events: list[AttendanceEvent]
    summary: AttendanceReportSummary = Field(default_factory=AttendanceReportSummary)


class AttendanceEventUpdate(BaseModel):
    employee_name: str | None = None
    device_id: str | None = None
    event_type: str | None = None
    confidence: float | None = Field(default=None, ge=0.0, le=1.0)
    captured_at: datetime | None = None
    source: str | None = None
    evidence_ref: str | None = None
    accepted: bool | None = None
    duplicate: bool | None = None


class SuggestEventResponse(BaseModel):
    person_id: str
    suggested_event_type: str
    can_register: bool
    shift_status: str
    reason: str
    policy: ExitPolicyResponse
    last_event_today: AttendanceEvent | None = None


class AttendanceEventUpdateResponse(BaseModel):
    event: AttendanceEvent
    message: str


class AttendanceEventDeleteResponse(BaseModel):
    event_id: str
    message: str


class IncidentListResponse(BaseModel):
    incidents: list[AttendanceIncident]
