from crewai import Agent

from app.llm.provider import crewai_llm
from app.tools.context_assembler import ContextAssemblerTool
from app.tools.embedding_tool import EmbeddingTool
from app.tools.llm_answer_tool import LLMAnswerTool
from app.tools.vector_search_tool import VectorSearchTool


def create_rag_agent() -> Agent:
    return Agent(
        role="RAG Specialist",
        goal=(
            "Answer the user's question accurately using only information found in the retrieved "
            "document chunks. Always cite your sources."
        ),
        backstory=(
            "You are a precise research analyst. You never fabricate information. If the answer "
            "is not in the retrieved chunks, you say so clearly. You always reference the specific "
            "document and page where you found each claim."
        ),
        llm=crewai_llm(),
        tools=[
            EmbeddingTool(),
            VectorSearchTool(),
            ContextAssemblerTool(),
            LLMAnswerTool(),
        ],
        allow_delegation=False,
        max_iter=5,
        max_execution_time=30,
        verbose=True,
    )
