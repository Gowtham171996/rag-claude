import json

from pydantic import BaseModel, Field
from crewai.tools import BaseTool


class LLMAnswerInput(BaseModel):
    question: str = Field(description="The user's question")
    context_json: str = Field(description="JSON string from ContextAssemblerTool with key 'context'")


class LLMAnswerTool(BaseTool):
    name: str = "LLMAnswerTool"
    description: str = (
        "Generates a grounded answer from document context. "
        "Uses local Ollama (qwen3.5:4b) and falls back to Claude if Ollama is unavailable."
    )
    args_schema: type[BaseModel] = LLMAnswerInput

    def _run(self, question: str, context_json: str) -> str:
        from app.llm.provider import chat

        ctx_data = json.loads(context_json)
        if ctx_data.get("empty"):
            return json.dumps({"answer": "No relevant documents found for this query."})

        context = ctx_data["context"]
        prompt = (
            f"Context:\n{context}\n\n"
            f"Question: {question}\n\n"
            "Answer:"
        )

        answer = chat(prompt)
        return json.dumps({"answer": answer})
