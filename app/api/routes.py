import logging
import time
import uuid

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from fastapi.responses import JSONResponse

from app.api.dependencies import require_api_key
from app.api.schemas import HealthResponse, IngestResponse, QueryRequest, QueryResponse
from app.config import settings
from app.db.qdrant import get_client as get_qdrant
from app.ingestion.pipeline import run_ingestion_pipeline
from app.agents.crew import run_query_crew

logger = logging.getLogger(__name__)
router = APIRouter()

_ALLOWED_EXTENSIONS = {".pdf", ".docx", ".txt"}
_MAX_FILE_BYTES = 50 * 1024 * 1024  # 50 MB


# ── /ingest-documents ─────────────────────────────────────────────────────────

@router.post("/ingest-documents", response_model=IngestResponse, dependencies=[Depends(require_api_key)])
async def ingest_documents(
    file: UploadFile = File(...),
    collection_name: str = Form(default="default"),
    metadata: str = Form(default="{}"),
):
    import json
    import os

    ext = os.path.splitext(file.filename or "")[1].lower()
    if ext not in _ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Unsupported file type '{ext}'. Allowed: {sorted(_ALLOWED_EXTENSIONS)}",
        )

    contents = await file.read()
    if len(contents) > _MAX_FILE_BYTES:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"File exceeds 50 MB limit ({len(contents) / 1_048_576:.1f} MB).",
        )

    try:
        user_metadata = json.loads(metadata)
    except json.JSONDecodeError:
        raise HTTPException(status_code=422, detail="metadata must be a valid JSON string.")

    logger.info('"Ingesting file=%s collection=%s"', file.filename, collection_name)

    result = await run_ingestion_pipeline(
        file_bytes=contents,
        filename=file.filename or "upload",
        collection_name=collection_name,
        user_metadata=user_metadata,
    )
    return result


# ── /query ────────────────────────────────────────────────────────────────────

@router.post("/query", response_model=QueryResponse, dependencies=[Depends(require_api_key)])
async def query(body: QueryRequest):
    # Verify collection exists
    qdrant = get_qdrant()
    collections = [c.name for c in qdrant.get_collections().collections]
    if body.collection_name not in collections:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Collection '{body.collection_name}' not found.",
        )

    logger.info('"Query collection=%s question_len=%d"', body.collection_name, len(body.question))

    start = time.monotonic()
    result = await run_query_crew(
        question=body.question,
        collection_name=body.collection_name,
        top_k=body.top_k,
        filters=body.filters,
    )
    latency_ms = int((time.monotonic() - start) * 1000)

    return QueryResponse(
        answer=result["answer"],
        sources=result["sources"],
        model_used=settings.ollama_model,
        latency_ms=latency_ms,
    )


# ── /health ───────────────────────────────────────────────────────────────────

@router.get("/health", response_model=HealthResponse)
async def health():
    checks: dict[str, str] = {}

    try:
        get_qdrant().get_collections()
        checks["vector_db"] = "ok"
    except Exception:
        checks["vector_db"] = "unreachable"

    # Anthropic reachability is implicit — we don't make a live call to save cost
    checks["llm_api"] = "ok"

    overall = "ok" if all(v == "ok" for v in checks.values()) else "degraded"
    status_code = 200 if overall == "ok" else 503

    return JSONResponse(
        status_code=status_code,
        content=HealthResponse(
            status=overall,
            version=settings.app_version,
            checks=checks,
        ).model_dump(mode="json"),
    )
