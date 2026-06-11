from datetime import datetime
from pathlib import Path
from tempfile import TemporaryDirectory

from app.services.schedule_service import ScheduleService


def test_tm_tolerance_and_early_exit_rules() -> None:
    with TemporaryDirectory() as tmp:
        service = ScheduleService(Path(tmp) / "work_schedules.json")
        service.assign_shift("MS-PL-0001", "TM")

        on_time = service.evaluate_event(
            person_id="MS-PL-0001",
            event_type="check_in",
            captured_at=datetime.fromisoformat("2026-06-10T13:10:00+00:00"),
        )
        late = service.evaluate_event(
            person_id="MS-PL-0001",
            event_type="check_in",
            captured_at=datetime.fromisoformat("2026-06-10T13:11:00+00:00"),
        )
        early = service.evaluate_event(
            person_id="MS-PL-0001",
            event_type="check_out",
            captured_at=datetime.fromisoformat("2026-06-10T20:59:00+00:00"),
        )
        normal_exit = service.evaluate_event(
            person_id="MS-PL-0001",
            event_type="check_out",
            captured_at=datetime.fromisoformat("2026-06-10T21:00:00+00:00"),
        )

    assert on_time.status == "on_time"
    assert late.status == "late"
    assert late.minutes_late == 1
    assert early.status == "early_exit"
    assert early.minutes_early == 1
    assert normal_exit.status == "normal"


def test_tt_tolerance_rule() -> None:
    with TemporaryDirectory() as tmp:
        service = ScheduleService(Path(tmp) / "work_schedules.json")
        service.assign_shift("AD-AD-0001", "TT")

        on_time = service.evaluate_event(
            person_id="AD-AD-0001",
            event_type="check_in",
            captured_at=datetime.fromisoformat("2026-06-10T19:10:00+00:00"),
        )
        late = service.evaluate_event(
            person_id="AD-AD-0001",
            event_type="check_in",
            captured_at=datetime.fromisoformat("2026-06-10T19:11:00+00:00"),
        )

    assert on_time.status == "on_time"
    assert late.status == "late"
