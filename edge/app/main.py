from datetime import UTC, datetime

from app.config import config
from app.dedupe import AttendanceDeduper
from app.embedding_cache import EmbeddingCache
from app.sync_client import AttendanceSyncClient
from app.voice import VoiceSpeaker


def main() -> None:
    cache = EmbeddingCache(config.cache_path)
    cache.load()

    deduper = AttendanceDeduper(config.duplicate_cooldown_seconds)
    speaker = VoiceSpeaker(enabled=config.voice_enabled)
    sync = AttendanceSyncClient(config.api_base_url, config.pending_events_path)

    print(f"Edge device: {config.device_id}")
    print(f"Embeddings cargados: {cache.count()}")
    print("Loop de camara pendiente: conectar detector/recognizer ONNX en models/.")

    # Smoke flow: useful while the recognition loop is not wired.
    person_id = "EMP-DEMO"
    if deduper.should_emit(person_id):
        speaker.say_welcome("Demo")
        sync.send_attendance_event(
            {
                "person_id": person_id,
                "employee_name": "Demo",
                "device_id": config.device_id,
                "event_type": "check_in",
                "confidence": 0.99,
                "captured_at": datetime.now(UTC).isoformat(),
                "source": "edge-smoke-test",
            }
        )


if __name__ == "__main__":
    main()

