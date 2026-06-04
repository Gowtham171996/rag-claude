import json

from pydantic import BaseModel, Field
from crewai.tools import BaseTool


class IntentClassifierInput(BaseModel):
    request_type: str = Field(description="Either 'ingest' (file upload) or 'query' (question)")


class IntentClassifierTool(BaseTool):
    name: str = "IntentClassifierTool"
    description: str = "Classifies an incoming request as 'ingest' or 'query'."
    args_schema: type[BaseModel] = IntentClassifierInput

    def _run(self, request_type: str) -> str:
        intent = "ingest" if "ingest" in request_type.lower() else "query"
        return json.dumps({"intent": intent})
