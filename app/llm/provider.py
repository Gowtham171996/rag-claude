"""
LLM provider: Ollama primary, Claude fallback.

All Ollama calls use an explicit Client(host=settings.ollama_base_url)
so the Docker service URL  http://ollama:11434  is used instead of the
SDK default of localhost:11434.
"""

import logging

from app.config import settings

logger = logging.getLogger(__name__)

_SYSTEM_PROMPT = (
    "You are a precise research analyst. Answer the user's question using ONLY the provided "
    "document context. If the answer is not in the context, say so explicitly. "
    "Always reference the source document and page (if available) for each claim using [N] notation "
    "where N is the context chunk number."
)


def _ollama_client():
    import ollama
    return ollama.Client(host=settings.ollama_base_url)


def chat(prompt: str, system: str = _SYSTEM_PROMPT, max_tokens: int = 2048) -> str:
    """Send a chat prompt. Tries Ollama; falls back to Claude on failure."""
    try:
        return _ollama_chat(prompt, system)
    except Exception as err:
        logger.warning("Ollama chat unavailable (%s), falling back to Claude.", err)

    if not settings.anthropic_api_key:
        raise RuntimeError(
            "Ollama is unreachable and ANTHROPIC_API_KEY is not set. "
            "Check that the ollama container is running."
        )
    return _claude_chat(prompt, system, max_tokens)


def _ollama_chat(prompt: str, system: str) -> str:
    response = _ollama_client().chat(
        model=settings.ollama_model,
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": prompt},
        ],
        options={"num_predict": 2048},
    )
    return response["message"]["content"]


def _claude_chat(prompt: str, system: str, max_tokens: int) -> str:
    import anthropic
    client = anthropic.Anthropic(api_key=settings.anthropic_api_key)
    msg = client.messages.create(
        model=settings.claude_model,
        max_tokens=max_tokens,
        system=system,
        messages=[{"role": "user", "content": prompt}],
    )
    return msg.content[0].text


def crewai_llm():
    """Return a CrewAI LLM object pointing at Ollama (or Claude as fallback)."""
    from crewai import LLM

    try:
        # Connectivity check using explicit host
        _ollama_client().list()
        logger.info("CrewAI using Ollama (%s).", settings.ollama_model)
        return LLM(
            model=f"ollama/{settings.ollama_model}",
            base_url=settings.ollama_base_url,
        )
    except Exception as err:
        logger.warning("Ollama not reachable for CrewAI (%s). Falling back to Claude.", err)

    if not settings.anthropic_api_key:
        raise RuntimeError(
            "Ollama unreachable and ANTHROPIC_API_KEY not set."
        )
    logger.info("CrewAI using Claude (%s).", settings.claude_model)
    return LLM(
        model=f"anthropic/{settings.claude_model}",
        api_key=settings.anthropic_api_key,
        max_tokens=2048,
    )
