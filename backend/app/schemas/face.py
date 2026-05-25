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


class StoredFaceEmbedding(StoredFacePublic):
    embedding: list[float]


class RegisterFaceResponse(BaseModel):
    person_id: str
    name: str
    model: str
    total_embeddings: int


class MatchCandidate(BaseModel):
    person_id: str
    name: str
    model: str
    distance: float
    confidence: float


class IdentifyFaceResponse(BaseModel):
    matched: bool
    threshold: float
    candidate: MatchCandidate | None = None


class RegisteredFacesResponse(BaseModel):
    faces: list[StoredFacePublic]

