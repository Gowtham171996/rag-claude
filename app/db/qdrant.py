import threading
from typing import Optional

from qdrant_client import QdrantClient
from qdrant_client.models import (
    Distance,
    FieldCondition,
    Filter,
    MatchValue,
    PointStruct,
    VectorParams,
)

from app.config import settings

_client: Optional[QdrantClient] = None
_lock = threading.Lock()


def get_client() -> QdrantClient:
    global _client
    if _client is None:
        with _lock:
            if _client is None:
                _client = QdrantClient(host=settings.qdrant_host, port=settings.qdrant_port)
    return _client


def ensure_collection(name: str) -> None:
    client = get_client()
    existing = {c.name for c in client.get_collections().collections}
    if name in existing:
        return

    client.create_collection(
        collection_name=name,
        vectors_config=VectorParams(size=settings.embedding_dim, distance=Distance.COSINE),
    )
    client.create_payload_index(collection_name=name, field_name="document_id", field_schema="keyword")
    client.create_payload_index(collection_name=name, field_name="filename", field_schema="keyword")


def upsert_chunks(collection: str, chunks: list[dict], vectors: list[list[float]]) -> None:
    client = get_client()
    points = [
        PointStruct(id=chunk["id"], vector=vector, payload=chunk["payload"])
        for chunk, vector in zip(chunks, vectors)
    ]
    # Batch in groups of 100 to avoid large request timeouts
    batch_size = 100
    for i in range(0, len(points), batch_size):
        client.upsert(collection_name=collection, points=points[i : i + batch_size])


def search(
    collection: str,
    query_vector: list[float],
    top_k: int,
    filters: dict,
    score_threshold: float = 0.0,   # set per-call; 0.0 returns all top_k results unfiltered
):
    client = get_client()
    qdrant_filter: Optional[Filter] = None
    if filters:
        conditions = [
            FieldCondition(key=k, match=MatchValue(value=v)) for k, v in filters.items()
        ]
        qdrant_filter = Filter(must=conditions)

    # qdrant-client >= 1.7 replaced .search() with .query_points()
    # .query_points() returns a QueryResponse; .points is the list of ScoredPoint
    return client.query_points(
        collection_name=collection,
        query=query_vector,
        limit=top_k,
        query_filter=qdrant_filter,
        with_payload=True,
        score_threshold=score_threshold,
    ).points


def delete_by_document_id(collection: str, document_id: str) -> None:
    client = get_client()
    client.delete(
        collection_name=collection,
        points_selector=Filter(
            must=[FieldCondition(key="document_id", match=MatchValue(value=document_id))]
        ),
    )
