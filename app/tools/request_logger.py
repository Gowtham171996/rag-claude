import json
import logging
import uuid
from datetime import datetime, timezone

from pydantic import BaseModel, Field
from crewai.tools import BaseTool

logger = logging.getLogger(__name__)


class RequestLoggerInput(BaseModel):
    intent: str = Field(description="Request intent: 'ingest' or 'query'")
    detail: str = Field(default="", description="Optional detail string")


class RequestLoggerTool(BaseTool):
    name: str = "RequestLoggerTool"
    description: str = "Logs a structured entry for the incoming request."
    args_schema: type[BaseModel] = RequestLoggerInput

    def _run(self, intent: str, detail: str = "") -> str:
        entry = {
            "request_id": str(uuid.uuid4()),
            "intent": intent,
            "detail": detail,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        logger.info(json.dumps(entry))
        return json.dumps({"logged": True, "request_id": entry["request_id"]})
