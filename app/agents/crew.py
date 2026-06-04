"""
Crew orchestration for the query path.

A new Crew is created per request so tasks carry the correct parameterised
context. The receptionist validates and enriches; the RAG agent retrieves
and answers. Output from the RAG task is parsed back to a structured dict.
"""

import json
import logging

from crewai import Crew, Process, Task

from app.agents.rag import create_rag_agent
from app.agents.receptionist import create_receptionist_agent
from app.api.schemas import SourceChunk
from app.retrieval.searcher import retrieve

logger = logging.getLogger(__name__)


async def run_query_crew(
    question: str,
    collection_name: str,
    top_k: int,
    filters: dict,
) -> dict:
    """
    Run the two-agent query pipeline.

    Rather than passing raw bytes through CrewAI tasks (slow and fragile),
    the retrieval step runs directly here and the assembled context is injected
    into the RAG task description. This keeps the Crew focused on reasoning
    while giving us deterministic retrieval.
    """
    # Retrieval happens outside the crew for reliability and testability
    sources: list[SourceChunk] = retrieve(
        question=question,
        collection_name=collection_name,
        top_k=top_k,
        filters=filters,
    )

    if not sources:
        return {"answer": "No relevant documents found for this query.", "sources": []}

    # Build numbered context block
    context_lines = []
    for i, src in enumerate(sources, start=1):
        page_info = f", page {src.page}" if src.page else ""
        context_lines.append(
            f"[{i}] {src.filename}{page_info} (score: {src.score:.2f})\n{src.excerpt}"
        )
    context = "\n\n---\n\n".join(context_lines)

    receptionist = create_receptionist_agent()
    rag = create_rag_agent()

    validation_task = Task(
        description=(
            f"Validate this query request:\n"
            f"Question: {question}\n"
            f"Collection: {collection_name}\n"
            f"Confirm the question is non-empty and under 2000 characters. "
            f"Log the request with intent='query'. "
            f"Return a JSON object: {{\"valid\": true, \"question\": \"<question>\"}}"
        ),
        expected_output='JSON object with keys "valid" and "question"',
        agent=receptionist,
    )

    answer_task = Task(
        description=(
            f"Answer this question using ONLY the context below. "
            f"Do not invent facts. Cite sources using [N] notation.\n\n"
            f"Question: {question}\n\n"
            f"Context:\n{context}\n\n"
            f"Return a JSON object with a single key 'answer' containing your response."
        ),
        expected_output='JSON object with key "answer"',
        agent=rag,
        context=[validation_task],
    )

    crew = Crew(
        agents=[receptionist, rag],
        tasks=[validation_task, answer_task],
        process=Process.sequential,
        verbose=False,
    )

    result = crew.kickoff()

    # CrewAI returns the final task output as a string — extract the answer
    raw = str(result)
    try:
        parsed = json.loads(raw)
        answer = parsed.get("answer", raw)
    except json.JSONDecodeError:
        # Agent returned prose instead of JSON — use it directly
        answer = raw

    return {
        "answer": answer,
        "sources": [s.model_dump() for s in sources],
    }
