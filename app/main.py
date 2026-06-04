import logging
import traceback
import uuid
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
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
    # Verify Qdrant is reachable at startup
    try:
        get_qdrant().get_collections()
        logger.info('"Qdrant connection OK"')
    except Exception as exc:
        logger.warning('"Qdrant not reachable at startup: %s"', exc)
    yield


app = FastAPI(
    title="RAG API",
    version=settings.app_version,
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
