from datetime import datetime

from pydantic import BaseModel, Field


class FaceBox(BaseModel):
    x: int
    y: int
    width: int
    height: int


class FaceDetectionResponse(BaseModel):
    image_width: int
    image_height: int
    face_count: int
    faces: list[FaceBox]


class AnalyzeFaceResponse(BaseModel):
    age: int | None = None
    dominant_gender: str | None = None
    dominant_emotion: str | None = None
    dominant_race: str | None = None
    raw: dict = Field(default_factory=dict)


class EmbeddingResponse(BaseModel):
    model: str
    vector_size: int
    embedding_preview: list[float]


class StoredFacePublic(BaseModel):
    person_id: str
    name: str
    model: str
    created_at: datetime
    image_url: str | None = None
    email: str | None = None
    employee_code: str | None = None
    is_active: bool = True
    embedding_count: int = 1


class StoredFaceEmbedding(StoredFacePublic):
    embedding: list[float]
    pose_type: str = "front"


class RegisterFaceResponse(BaseModel):
    person_id: str
    name: str
    model: str
    total_embeddings: int
    r2_saved: bool = False
    image_key: str | None = None
    image_url: str | None = None
    storage_message: str | None = None


class RegisterFaceProfileResponse(BaseModel):
    person_id: str
    name: str
    model: str
    poses_saved: list[str]
    total_embeddings: int
    embedding_count: int
    r2_saved: bool = False
    image_url: str | None = None
    storage_message: str | None = None


class MatchCandidate(BaseModel):
    person_id: str
    name: str
    model: str
    distance: float
    confidence: float


class LivenessVerifyResponse(BaseModel):
    passed: bool
    score: float
    message: str
    checks: dict[str, bool] = Field(default_factory=dict)
    challenge_id: str | None = None
    check_id: str | None = None
    method: str = "mediapipe_v2"
    anti_spoof_score: float | None = None
    candidate: MatchCandidate | None = None


class LivenessChallengeStep(BaseModel):
    type: str
    prompt: str
    form_field: str
    order: int


class LivenessChallengeResponse(BaseModel):
    challenge_id: str
    steps: list[LivenessChallengeStep]


class IdentifyFaceResponse(BaseModel):
    matched: bool
    threshold: float
    candidate: MatchCandidate | None = None
    near_miss: MatchCandidate | None = None


class RegisteredFacesResponse(BaseModel):
    faces: list[StoredFacePublic]


class StorageStatusResponse(BaseModel):
    provider: str
    enabled: bool
    connected: bool
    bucket: str | None = None
    message: str


class UpdateEmployeeRequest(BaseModel):
    name: str | None = None
    email: str | None = None
    employee_code: str | None = None
    is_active: bool | None = None


class UpdateEmployeeResponse(BaseModel):
    person: StoredFacePublic
    message: str


class UpdateEmployeePhotoResponse(BaseModel):
    person: StoredFacePublic
    message: str
    image_url: str | None = None
    r2_saved: bool = False

