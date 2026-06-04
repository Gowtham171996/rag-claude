"""
Embedding via local Ollama (qwen3-embedding:0.6b).
The ollama Python SDK defaults to localhost:11434, so we always pass
an explicit Client(host=...) built from settings.ollama_base_url so the
Docker service name  http://ollama:11434  is honoured correctly.
"""

import logging

from app.config import settings

logger = logging.getLogger(__name__)


def _client():
    import ollama
    return ollama.Client(host=settings.ollama_base_url)


def embed_texts(texts: list[str]) -> list[list[float]]:
    """Embed a list of document texts. Returns one vector per text."""
    client = _client()
    vectors: list[list[float]] = []
    batch_size = 100
    for i in range(0, len(texts), batch_size):
        batch = texts[i : i + batch_size]
        result = client.embed(model=settings.ollama_embedding_model, input=batch)
        vectors.extend(result["embeddings"])
    return vectors


def embed_query(text: str) -> list[float]:
    """Embed a single query string."""
    result = _client().embed(model=settings.ollama_embedding_model, input=[text])
    return result["embeddings"][0]
