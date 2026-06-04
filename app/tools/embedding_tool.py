import json

from pydantic import BaseModel, Field
from crewai.tools import BaseTool


class EmbeddingToolInput(BaseModel):
    text: str = Field(description="Text to embed as a query vector")


class EmbeddingTool(BaseTool):
    name: str = "EmbeddingTool"
    description: str = "Converts a query string into a dense embedding vector using Voyage AI."
    args_schema: type[BaseModel] = EmbeddingToolInput

    def _run(self, text: str) -> str:
        from app.ingestion.embedder import embed_query

        vector = embed_query(text)
        # Return as JSON string — the RAG agent parses this
        return json.dumps({"vector": vector, "dim": len(vector)})
