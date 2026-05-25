from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class EdgeConfig:
    device_id: str = "edge-windows-001"
    camera_index: int = 0
    api_base_url: str = "http://127.0.0.1:8000"
    cache_path: Path = Path("data/employee_embeddings.json")
    pending_events_path: Path = Path("data/pending_events.json")
    match_threshold: float = 0.35
    duplicate_cooldown_seconds: int = 45
    frame_skip: int = 2
    max_faces_per_frame: int = 3
    voice_enabled: bool = True


config = EdgeConfig()

