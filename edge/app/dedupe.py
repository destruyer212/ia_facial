from datetime import UTC, datetime, timedelta


class AttendanceDeduper:
    def __init__(self, cooldown_seconds: int) -> None:
        self.cooldown = timedelta(seconds=cooldown_seconds)
        self.last_seen: dict[str, datetime] = {}

    def should_emit(self, person_id: str, now: datetime | None = None) -> bool:
        current = now or datetime.now(UTC)
        previous = self.last_seen.get(person_id)
        if previous is not None and current - previous < self.cooldown:
            return False
        self.last_seen[person_id] = current
        return True

