from app.api.schemas import SourceChunk
from app.db import qdrant as db
from app.ingestion.embedder import embed_query


def retrieve(
    question: str,
    collection_name: str,
    top_k: int,
    filters: dict,
    score_threshold: float = 0.5,
) -> list[SourceChunk]:
    query_vector = embed_query(question)
    hits = db.search(
        collection=collection_name,
        query_vector=query_vector,
        top_k=top_k,
        filters=filters,
        score_threshold=score_threshold,
    )

    return [
        SourceChunk(
            document_id=hit.payload["document_id"],
            filename=hit.payload["filename"],
            chunk_index=hit.payload["chunk_index"],
            page=hit.payload.get("page"),
            excerpt=hit.payload["text"][:500],
            score=hit.score,
        )
        for hit in hits
    ]
