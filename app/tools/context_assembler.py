import json

from pydantic import BaseModel, Field
from crewai.tools import BaseTool


class ContextAssemblerInput(BaseModel):
    chunks_json: str = Field(description="JSON string from VectorSearchTool containing 'chunks' list")


class ContextAssemblerTool(BaseTool):
    name: str = "ContextAssemblerTool"
    description: str = "Formats retrieved document chunks into a numbered context block for the LLM."
    args_schema: type[BaseModel] = ContextAssemblerInput

    def _run(self, chunks_json: str) -> str:
        data = json.loads(chunks_json)
        chunks = data.get("chunks", [])

        if not chunks:
            return json.dumps({"context": "", "empty": True})

        lines = []
        for i, chunk in enumerate(chunks, start=1):
            page_info = f", page {chunk['page']}" if chunk.get("page") else ""
            lines.append(
                f"[{i}] Source: {chunk['filename']}{page_info} (score: {chunk['score']:.2f})\n"
                f"{chunk['text']}\n"
            )

        context = "\n---\n".join(lines)
        return json.dumps({"context": context, "empty": False, "chunk_count": len(chunks)})
