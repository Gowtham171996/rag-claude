from pydantic import BaseModel, Field
from crewai.tools import BaseTool


_ALLOWED = {".pdf", ".docx", ".txt"}
_MAX_MB = 50


class FileValidatorInput(BaseModel):
    filename: str = Field(description="Original filename including extension")
    size_bytes: int = Field(description="File size in bytes")


class FileValidatorTool(BaseTool):
    name: str = "FileValidatorTool"
    description: str = "Validates that a file has an allowed extension and is within the size limit."
    args_schema: type[BaseModel] = FileValidatorInput

    def _run(self, filename: str, size_bytes: int) -> str:
        import json
        import os

        ext = os.path.splitext(filename)[1].lower()
        if ext not in _ALLOWED:
            return json.dumps({"valid": False, "error": f"Unsupported file type '{ext}'"})
        if size_bytes > _MAX_MB * 1024 * 1024:
            mb = size_bytes / 1_048_576
            return json.dumps({"valid": False, "error": f"File too large ({mb:.1f} MB > {_MAX_MB} MB)"})
        return json.dumps({"valid": True})
