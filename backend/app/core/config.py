from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "IA Facial Enterprise MVP"
    environment: str = "development"
    api_v1_prefix: str = "/api/v1"
    cors_origins: list[str] = Field(
        default_factory=lambda: [
            "http://127.0.0.1:5500",
            "http://localhost:5500",
            "http://localhost:3000",
            "http://localhost:5173",
            "http://127.0.0.1:5173",
        ]
    )
    deepface_model: str = "Facenet512"
    deepface_detector_backend: str = "opencv"
    face_engine: str = "deepface"
    insightface_model: str = "buffalo_l"
    face_match_threshold: float = 0.35
    face_scan_match_threshold: float = 0.40
    face_scan_max_match_threshold: float = 0.40
    face_scan_ambiguous_margin: float = 0.05
    liveness_max_same_person_distance: float = 0.52
    liveness_min_face_shift_px: float = 18.0
    liveness_ear_blink_max: float = 0.21
    liveness_ear_open_min: float = 0.22
    liveness_min_head_yaw_delta: float = 0.06
    liveness_min_texture_score: float = 12.0
    liveness_min_anti_spoof_score: float = 0.30
    register_min_anti_spoof_score: float = 0.38
    liveness_min_pass_score: float = 0.72
    liveness_mar_open_min: float = 0.28
    liveness_smile_enabled: bool = True
    register_duplicate_match_threshold: float = 0.32
    face_processing_concurrency: int = Field(default=1, ge=1, le=4)
    default_scheduled_exit_time: str = "22:00"
    default_exit_tolerance_minutes: int = 10
    ollama_enabled: bool = False
    ollama_base_url: str = "http://localhost:11434"
    ollama_model: str = "llama3.1"
    max_upload_mb: int = 8
    local_data_dir: Path = Path("./data")
    storage_backend: str = "json"
    default_org_code: str = "demo"
    database_url: str = "postgresql+psycopg://ia_facial:ia_facial@localhost:5432/ia_facial"
    auth_required: bool = True
    auth_secret_key: str = "change-me-dev-secret"
    auth_token_ttl_minutes: int = 480
    auth_default_admin_email: str = "admin@iafacial.local"
    auth_default_admin_password: str = "Admin123!"
    auth_default_admin_name: str = "Administrador"
    r2_account_id: str = ""
    r2_endpoint: str = ""
    r2_access_key_id: str = ""
    r2_secret_access_key: str = ""
    r2_bucket: str = ""
    r2_public_base_url: str = ""
    # Gmail OAuth: local = backend/token.json; Render = Secret File o GMAIL_TOKEN_JSON
    gmail_token_path: str = ""
    gmail_token_json: str = ""
    expose_dev_registration_token: bool = False

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    @property
    def active_face_model(self) -> str:
        engine = self.face_engine.lower().strip()
        if engine == "insightface":
            return f"arcface_{self.insightface_model}"
        if engine == "arcface":
            return "ArcFace"
        return self.deepface_model

    @property
    def resolved_data_dir(self) -> Path:
        if self.local_data_dir.is_absolute():
            return self.local_data_dir
        return Path.cwd() / self.local_data_dir

    @property
    def r2_enabled(self) -> bool:
        return bool(
            self.r2_endpoint
            and self.r2_access_key_id
            and self.r2_secret_access_key
            and self.r2_bucket
        )


settings = Settings()
