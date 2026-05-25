from datetime import UTC, datetime, time, timedelta

from app.core.config import settings
from app.schemas.attendance import (
    AttendanceDecision,
    AttendanceIncident,
    ExitAttemptResponse,
    ExitPolicyResponse,
)
from app.services.incident_store import LocalIncidentStore, new_incident_id
from app.services.reason_ai_service import ReasonAIService


class AttendanceService:
    def __init__(
        self,
        reason_ai_service: ReasonAIService | None = None,
        incident_store: LocalIncidentStore | None = None,
    ) -> None:
        self.reason_ai_service = reason_ai_service or ReasonAIService()
        self.incident_store = incident_store or LocalIncidentStore()

    def get_policy(
        self,
        scheduled_exit_time: time | None = None,
        tolerance_minutes: int | None = None,
    ) -> ExitPolicyResponse:
        scheduled_time = scheduled_exit_time or parse_time(settings.default_scheduled_exit_time)
        resolved_tolerance = (
            settings.default_exit_tolerance_minutes
            if tolerance_minutes is None
            else tolerance_minutes
        )
        tolerance_end = add_minutes_to_time(scheduled_time, resolved_tolerance)
        return ExitPolicyResponse(
            scheduled_exit_time=scheduled_time,
            tolerance_minutes=resolved_tolerance,
            tolerance_end_time=tolerance_end,
        )

    def evaluate_exit_attempt(
        self,
        person_id: str,
        employee_name: str | None,
        attempted_at: datetime | None,
        scheduled_exit_time: time | None = None,
        tolerance_minutes: int | None = None,
        reason: str | None = None,
        source: str = "manual",
        evidence_ref: str | None = None,
    ) -> ExitAttemptResponse:
        attempt_time = attempted_at or datetime.now(UTC)
        policy = self.get_policy(
            scheduled_exit_time=scheduled_exit_time,
            tolerance_minutes=tolerance_minutes,
        )
        scheduled_exit = datetime.combine(
            attempt_time.date(),
            policy.scheduled_exit_time,
            tzinfo=attempt_time.tzinfo,
        )
        minutes_early = max(0, int((scheduled_exit - attempt_time).total_seconds() // 60))

        if attempt_time >= scheduled_exit:
            return ExitAttemptResponse(
                decision=AttendanceDecision.allowed,
                allowed=True,
                person_id=person_id,
                employee_name=employee_name,
                attempted_at=attempt_time,
                policy=policy,
                minutes_early=0,
                reason_required=False,
                message=self._allowed_message(attempt_time, policy),
            )

        if not reason or not reason.strip():
            return ExitAttemptResponse(
                decision=AttendanceDecision.requires_reason,
                allowed=False,
                person_id=person_id,
                employee_name=employee_name,
                attempted_at=attempt_time,
                policy=policy,
                minutes_early=minutes_early,
                reason_required=True,
                message="Salida temprana detectada. El empleado debe registrar un motivo.",
            )

        analysis = self.reason_ai_service.analyze_reason(reason)
        if analysis.is_valid:
            return ExitAttemptResponse(
                decision=AttendanceDecision.approved_exception,
                allowed=True,
                person_id=person_id,
                employee_name=employee_name,
                attempted_at=attempt_time,
                policy=policy,
                minutes_early=minutes_early,
                reason_required=True,
                reason_analysis=analysis,
                message="Salida temprana aprobada como excepcion; queda registrada para auditoria.",
            )

        incident = AttendanceIncident(
            incident_id=new_incident_id(),
            person_id=person_id,
            employee_name=employee_name,
            violation_type="early_exit",
            attempted_at=attempt_time,
            scheduled_exit_time=policy.scheduled_exit_time,
            tolerance_minutes=policy.tolerance_minutes,
            minutes_early=minutes_early,
            reason=reason,
            analysis=analysis,
            severity=self._severity(minutes_early, analysis.risk_score),
            status="open",
            evidence_ref=evidence_ref or source,
            supervisor_notified=True,
            created_at=datetime.now(UTC),
        )
        self.incident_store.save(incident)

        return ExitAttemptResponse(
            decision=AttendanceDecision.incident_created,
            allowed=False,
            person_id=person_id,
            employee_name=employee_name,
            attempted_at=attempt_time,
            policy=policy,
            minutes_early=minutes_early,
            reason_required=True,
            reason_analysis=analysis,
            incident=incident,
            message="Motivo no validado. Se genero incidencia y se notifico al supervisor.",
        )

    @staticmethod
    def _severity(minutes_early: int, risk_score: float) -> str:
        if minutes_early >= 60 or risk_score >= 0.85:
            return "high"
        if minutes_early >= 20 or risk_score >= 0.65:
            return "medium"
        return "low"

    @staticmethod
    def _allowed_message(attempt_time: datetime, policy: ExitPolicyResponse) -> str:
        tolerance_end = datetime.combine(
            attempt_time.date(),
            policy.tolerance_end_time,
            tzinfo=attempt_time.tzinfo,
        )
        if attempt_time <= tolerance_end:
            return "Salida dentro de la ventana permitida."
        return "Salida posterior a la tolerancia; registrar como evento tardio si aplica."


def parse_time(value: str) -> time:
    return time.fromisoformat(value)


def add_minutes_to_time(value: time, minutes: int) -> time:
    base = datetime.combine(datetime.today(), value)
    return (base + timedelta(minutes=minutes)).time().replace(second=0, microsecond=0)
