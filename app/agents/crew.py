"""
Crew orchestration with three-agent pipeline:

  Receptionist  →  classifies intent and scrubs PII/unsafe content
       │
       ├─ intent: rag_query   →  RAG Agent  (retrieve + answer)
       ├─ intent: devops_task →  DevOps Agent (health / tests / golden dataset)
       └─ intent: off_topic   →  return rejection message directly
"""

import json
import logging

from crewai import Crew, Process, Task

from app.agents.devops import create_devops_agent
from app.agents.rag import create_rag_agent
from app.agents.receptionist import create_receptionist_agent
from app.api.schemas import SourceChunk
from app.retrieval.searcher import retrieve

logger = logging.getLogger(__name__)


# ── Receptionist gate (runs for EVERY request) ────────────────────────────────

def _run_receptionist(user_input: str) -> dict:
    """
    Run the receptionist in a single-agent crew.
    Returns a dict with at minimum:
      {"intent": "rag_query"|"devops_task"|"off_topic",
       "clean_input": "...",
       "rejection_message": "..." (only when off_topic or blocked)}
    """
    receptionist = create_receptionist_agent()

    task = Task(
        description=(
            f"A user has sent the following request:\n\n"
            f"\"\"\"\n{user_input}\n\"\"\"\n\n"
            "Follow your checklist:\n"
            "1. Greet the user (one sentence, warm and professional).\n"
            "2. Scrub any PII — replace with [REDACTED].\n"
            "3. Check for adult content, harmful requests, or off-topic queries.\n"
            "4. Classify intent: 'rag_query', 'devops_task', or 'off_topic'.\n"
            "5. Return ONLY a JSON object with these exact keys:\n"
            "   {\n"
            "     \"greeting\": \"<one-sentence warm greeting>\",\n"
            "     \"intent\": \"rag_query\" | \"devops_task\" | \"off_topic\",\n"
            "     \"clean_input\": \"<scrubbed version of the input>\",\n"
            "     \"rejection_message\": \"<polite refusal if off_topic or blocked, else null>\"\n"
            "   }"
        ),
        expected_output="JSON object with keys: greeting, intent, clean_input, rejection_message",
        agent=receptionist,
    )

    crew = Crew(agents=[receptionist], tasks=[task], process=Process.sequential, verbose=False)
    raw = str(crew.kickoff())

    try:
        # Strip markdown code fences if model wrapped the JSON
        clean = raw.strip().strip("```json").strip("```").strip()
        return json.loads(clean)
    except json.JSONDecodeError:
        logger.warning("Receptionist returned non-JSON: %s", raw[:200])
        return {"intent": "rag_query", "clean_input": user_input, "greeting": "Hello!", "rejection_message": None}


# ── RAG crew ──────────────────────────────────────────────────────────────────

async def run_query_crew(
    question: str,
    collection_name: str,
    top_k: int,
    filters: dict,
) -> dict:
    # 1. Receptionist gate
    gate = _run_receptionist(question)
    greeting = gate.get("greeting", "")
    intent = gate.get("intent", "rag_query")
    clean_question = gate.get("clean_input", question)

    if intent == "off_topic" or gate.get("rejection_message"):
        msg = gate.get("rejection_message") or "I'm sorry, I can't help with that request."
        return {"answer": f"{greeting}\n\n{msg}", "sources": []}

    if intent == "devops_task":
        return await run_devops_crew(clean_question)

    # 2. Deterministic retrieval (outside the crew for reliability)
    sources: list[SourceChunk] = retrieve(
        question=clean_question,
        collection_name=collection_name,
        top_k=top_k,
        filters=filters,
    )

    if not sources:
        return {
            "answer": (
                f"{greeting}\n\n"
                "I don't have enough information in the available documents to answer this question."
            ),
            "sources": [],
        }

    # 3. Build numbered context block
    context_lines = []
    for i, src in enumerate(sources, start=1):
        page_info = f", page {src.page}" if src.page else ""
        context_lines.append(
            f"[{i}] {src.filename}{page_info} (score: {src.score:.3f})\n{src.excerpt}"
        )
    context = "\n\n---\n\n".join(context_lines)

    # 4. RAG agent answers
    rag = create_rag_agent()

    answer_task = Task(
        description=(
            f"{greeting}\n\n"
            f"The user asked (after PII scrubbing): {clean_question}\n\n"
            f"Retrieved context ({len(sources)} chunks):\n{context}\n\n"
            "Answer the question using ONLY the context above. "
            "Apply your three quality checks (context relevancy, faithfulness, citation accuracy). "
            "Include [N] citations. "
            "If the context is insufficient, say so explicitly. "
            "End with a one-line CONFIDENCE note (High/Medium/Low + reason). "
            "Return a JSON object: {\"answer\": \"<full response>\"}"
        ),
        expected_output='JSON object with key "answer"',
        agent=rag,
    )

    crew = Crew(agents=[rag], tasks=[answer_task], process=Process.sequential, verbose=False)
    raw = str(crew.kickoff())

    try:
        clean = raw.strip().strip("```json").strip("```").strip()
        answer = json.loads(clean).get("answer", raw)
    except json.JSONDecodeError:
        answer = raw

    # Prepend greeting
    if greeting and not answer.startswith(greeting):
        answer = f"{greeting}\n\n{answer}"

    return {"answer": answer, "sources": [s.model_dump() for s in sources]}


# ── DevOps crew ───────────────────────────────────────────────────────────────

async def run_devops_crew(task_description: str) -> dict:
    devops = create_devops_agent()

    task = Task(
        description=(
            f"A DevOps task has been requested:\n\n{task_description}\n\n"
            "1. Always run HealthCheckTool first.\n"
            "2. Based on the request, run TestRunnerTool and/or GoldenDatasetTool.\n"
            "3. Return a clear summary: overall status, what passed, what failed, "
            "   and recommended next steps."
        ),
        expected_output="A clear DevOps status report with pass/fail counts and next steps.",
        agent=devops,
    )

    crew = Crew(agents=[devops], tasks=[task], process=Process.sequential, verbose=False)
    result = str(crew.kickoff())

    return {"answer": result, "sources": []}
