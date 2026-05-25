from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "IA Facial Enterprise MVP"
    environment: str = "development"
    api_v1_prefix: str = "/api/v1"
    cors_origins: list[str] = Field(
        default_factory=lambda: [
            "http://localhost:3000",
            "http://localhost:5173",
            "http://127.0.0.1:5173",
        ]
    )
    deepface_model: str = "Facenet512"
    deepface_detector_backend: str = "opencv"
    face_match_threshold: float = 0.35
    default_scheduled_exit_time: str = "22:00"
    default_exit_tolerance_minutes: int = 10
    ollama_enabled: bool = False
    ollama_base_url: str = "http://localhost:11434"
    ollama_model: str = "llama3.1"
    max_upload_mb: int = 8
    local_data_dir: Path = Path("./data")
    database_url: str = "postgresql+psycopg://ia_facial:ia_facial@localhost:5432/ia_facial"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    @property
    def resolved_data_dir(self) -> Path:
        if self.local_data_dir.is_absolute():
            return self.local_data_dir
        return Path.cwd() / self.local_data_dir


settings = Settings()
