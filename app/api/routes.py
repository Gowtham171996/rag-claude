import logging
import time
import uuid

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from fastapi.responses import JSONResponse

from app.agents.crew import run_query_crew
from app.api.dependencies import require_api_key
from app.api.schemas import HealthResponse, IngestResponse, QueryRequest, QueryResponse
from app.config import settings
from app.db.qdrant import get_client as get_qdrant
from app.ingestion.pipeline import run_ingestion_pipeline

logger = logging.getLogger(__name__)
router = APIRouter()

_ALLOWED_EXTENSIONS = {".pdf", ".docx", ".txt"}
_MAX_FILE_BYTES = 50 * 1024 * 1024  # 50 MB


# ── /ingest-documents ─────────────────────────────────────────────────────────

@router.post(
    "/ingest-documents",
    response_model=IngestResponse,
    tags=["documents"],
    summary="Ingest a document",
    description="""
Upload a PDF, DOCX, or TXT file. The pipeline:
1. Parses the document into raw text
2. Chunks it (512 tokens, 64-token overlap)
3. Embeds each chunk via Ollama `qwen3-embedding:0.6b`
4. Stores vectors + metadata in Qdrant

Re-ingesting the same file into the same collection is **idempotent** —
old chunks are replaced.
""",
    responses={
        200: {"description": "Document ingested successfully"},
        422: {"description": "Invalid file type, oversized file, or malformed metadata"},
        500: {"description": "Ingestion pipeline failure"},
    },
    dependencies=[Depends(require_api_key)],
)
async def ingest_documents(
    file: UploadFile = File(..., description="PDF, DOCX, or TXT file. Max 50 MB."),
    collection_name: str = Form(default="default", description="Target Qdrant collection name"),
    metadata: str = Form(default="{}", description="Optional JSON string of extra metadata"),
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

@router.post(
    "/query",
    response_model=QueryResponse,
    tags=["query"],
    summary="Ask a question",
    description="""
Submit a natural-language question. The pipeline:

1. **Receptionist Agent** — greets, scrubs PII, filters harmful content, classifies intent
2. **RAG Agent** — embeds question → searches Qdrant → assembles context → calls LLM
3. Returns answer with `[N]` source citations and a `CONFIDENCE` note

If the Receptionist detects a **DevOps intent** (e.g. "run tests", "check health"),
the request is automatically routed to the DevOps Agent instead.

**Example questions:**
- `"What are Gowtham's key skills?"`
- `"What P95 latency was achieved at Solventum?"`
- `"run health check and golden dataset tests"` ← routes to DevOps Agent
""",
    responses={
        200: {"description": "Answer with source citations"},
        404: {"description": "Collection not found — ingest a document first"},
        422: {"description": "Invalid question"},
    },
    dependencies=[Depends(require_api_key)],
)
async def query(body: QueryRequest):
    qdrant = get_qdrant()
    collections = [c.name for c in qdrant.get_collections().collections]
    if body.collection_name not in collections:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Collection '{body.collection_name}' not found. Ingest a document first.",
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

@router.get(
    "/health",
    response_model=HealthResponse,
    tags=["devops"],
    summary="Health check",
    description="Liveness + readiness check. Returns 200 when all services are reachable, 503 when degraded.",
)
async def health():
    checks: dict[str, str] = {}

    try:
        get_qdrant().get_collections()
        checks["vector_db"] = "ok"
    except Exception:
        checks["vector_db"] = "unreachable"

    checks["llm_api"] = "ok"

    overall = "ok" if all(v == "ok" for v in checks.values()) else "degraded"
    http_status = 200 if overall == "ok" else 503

    return JSONResponse(
        status_code=http_status,
        content=HealthResponse(
            status=overall,
            version=settings.app_version,
            checks=checks,
        ).model_dump(mode="json"),
    )
