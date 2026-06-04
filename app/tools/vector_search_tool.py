import json

from pydantic import BaseModel, Field
from crewai.tools import BaseTool


class VectorSearchInput(BaseModel):
    collection: str = Field(description="Qdrant collection name")
    vector_json: str = Field(description="JSON string with key 'vector' containing a list of floats")
    top_k: int = Field(default=5, description="Number of results to return")
    filters_json: str = Field(default="{}", description="JSON string of payload filters")


class VectorSearchTool(BaseTool):
    name: str = "VectorSearchTool"
    description: str = "Searches a Qdrant collection for the most relevant chunks given a query vector."
    args_schema: type[BaseModel] = VectorSearchInput

    def _run(self, collection: str, vector_json: str, top_k: int = 5, filters_json: str = "{}") -> str:
        from app.db import qdrant as db

        vector = json.loads(vector_json)["vector"]
        filters = json.loads(filters_json)

        hits = db.search(
            collection=collection,
            query_vector=vector,
            top_k=top_k,
            filters=filters,
        )

        results = [
            {
                "document_id": h.payload["document_id"],
                "filename": h.payload["filename"],
                "chunk_index": h.payload["chunk_index"],
                "page": h.payload.get("page"),
                "text": h.payload["text"],
                "score": h.score,
            }
            for h in hits
        ]
        return json.dumps({"chunks": results, "count": len(results)})
