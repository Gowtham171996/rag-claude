import logging
import traceback
import uuid
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.openapi.utils import get_openapi
from fastapi.responses import JSONResponse

from app.api.routes import router
from app.config import settings
from app.db.qdrant import get_client as get_qdrant

logging.basicConfig(
    level=settings.log_level,
    format='{"time": "%(asctime)s", "level": "%(levelname)s", "name": "%(name)s", "msg": %(message)s}',
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    try:
        get_qdrant().get_collections()
        logger.info('"Qdrant connection OK"')
    except Exception as exc:
        logger.warning('"Qdrant not reachable at startup: %s"', exc)
    yield


app = FastAPI(
    title="RAG API",
    version=settings.app_version,
    description="""
## Retrieval-Augmented Generation API

A production-ready RAG pipeline powered by **CrewAI agents**, **Ollama** (local LLM + embeddings),
and **Qdrant** vector database.

### Architecture
```
Client → Receptionist Agent (PII scrub + routing)
              ↓
         RAG Agent → Qdrant → Ollama qwen3.5:4b → Answer + Citations
              ↓
         DevOps Agent → Health checks + Golden dataset tests
```

### Quick start
1. **Ingest** a PDF/DOCX/TXT document via `POST /ingest-documents`
2. **Query** it in natural language via `POST /query`
3. Answers include source citations and a confidence level

### Authentication
All endpoints except `/health` require an `X-API-Key` header.
""",
    contact={
        "name": "Gowtham B C",
        "email": "bcgowtham17@gmail.com",
        "url": "https://github.com/Gowtham171996/rag-claude",
    },
    license_info={
        "name": "MIT",
    },
    openapi_tags=[
        {
            "name": "documents",
            "description": "Ingest PDF, DOCX, or TXT files into the vector database.",
        },
        {
            "name": "query",
            "description": "Ask questions answered from ingested documents. "
            "Responses include source citations and a confidence note.",
        },
        {
            "name": "devops",
            "description": "System health, test runner, and golden dataset evaluation.",
        },
    ],
    lifespan=lifespan,
)

app.include_router(router, prefix="/api/v1")


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    trace_id = str(uuid.uuid4())
    logger.error('"Unhandled exception trace_id=%s: %s"', trace_id, traceback.format_exc())
    return JSONResponse(
        status_code=500,
        content={
            "error": "internal_server_error",
            "message": "An unexpected error occurred.",
            "trace_id": trace_id,
        },
    )
