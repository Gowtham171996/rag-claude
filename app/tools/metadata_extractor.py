import json
from datetime import datetime, timezone

from pydantic import BaseModel, Field
from crewai.tools import BaseTool


class MetadataExtractorInput(BaseModel):
    filename: str = Field(description="Original filename")
    size_bytes: int = Field(description="File size in bytes")
    user_metadata: str = Field(default="{}", description="JSON string of user-supplied metadata")


class MetadataExtractorTool(BaseTool):
    name: str = "MetadataExtractorTool"
    description: str = "Extracts and normalises file metadata for downstream processing."
    args_schema: type[BaseModel] = MetadataExtractorInput

    def _run(self, filename: str, size_bytes: int, user_metadata: str = "{}") -> str:
        try:
            extra = json.loads(user_metadata)
        except json.JSONDecodeError:
            extra = {}

        return json.dumps({
            "filename": filename,
            "size_bytes": size_bytes,
            "upload_timestamp": datetime.now(timezone.utc).isoformat(),
            "user_metadata": extra,
        })
