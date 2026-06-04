import uuid
from datetime import datetime, timezone
from typing import Optional

from pydantic import BaseModel, Field


def _new_uuid() -> str:
    return str(uuid.uuid4())


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


# ── Ingest ────────────────────────────────────────────────────────────────────

class IngestResponse(BaseModel):
    document_id: str = Field(default_factory=_new_uuid)
    filename: str
    collection: str
    chunks_stored: int
    ingested_at: datetime = Field(default_factory=_utcnow)


# ── Query ─────────────────────────────────────────────────────────────────────

class QueryRequest(BaseModel):
    question: str = Field(..., min_length=1, max_length=2000)
    collection_name: str = Field(default="default")
    top_k: int = Field(default=5, ge=1, le=20)
    filters: dict = Field(default_factory=dict)


class SourceChunk(BaseModel):
    document_id: str
    filename: str
    chunk_index: int
    page: Optional[int]
    excerpt: str
    score: float


class QueryResponse(BaseModel):
    answer: str
    sources: list[SourceChunk]
    query_id: str = Field(default_factory=_new_uuid)
    model_used: str
    latency_ms: int


# ── Health ────────────────────────────────────────────────────────────────────

class HealthResponse(BaseModel):
    status: str
    version: str
    checks: dict[str, str]
    timestamp: datetime = Field(default_factory=_utcnow)
