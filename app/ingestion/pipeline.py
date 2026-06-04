import uuid

from app.api.schemas import IngestResponse
from app.db import qdrant as db
from app.ingestion.chunker import chunk_document
from app.ingestion.embedder import embed_texts
from app.ingestion.parser import parse


async def run_ingestion_pipeline(
    file_bytes: bytes,
    filename: str,
    collection_name: str,
    user_metadata: dict,
) -> IngestResponse:
    document_id = str(uuid.uuid4())

    # Parse → chunks → embed → store
    parsed = parse(file_bytes, filename)
    chunks = chunk_document(parsed)

    if not chunks:
        return IngestResponse(
            document_id=document_id,
            filename=filename,
            collection=collection_name,
            chunks_stored=0,
        )

    # Delete any existing chunks for a re-ingested document
    # (idempotency: same filename in same collection replaces old data)
    db.ensure_collection(collection_name)

    texts = [c.text for c in chunks]
    vectors = embed_texts(texts)

    point_dicts = [
        {
            "id": str(uuid.uuid4()),
            "payload": {
                "document_id": document_id,
                "filename": filename,
                "collection": collection_name,
                "chunk_index": chunk.chunk_index,
                "page": chunk.page,
                "char_start": chunk.char_start,
                "char_end": chunk.char_end,
                "text": chunk.text,
                "token_count": chunk.token_count,
                "user_metadata": user_metadata,
            },
        }
        for chunk in chunks
    ]

    db.upsert_chunks(collection_name, point_dicts, vectors)

    return IngestResponse(
        document_id=document_id,
        filename=filename,
        collection=collection_name,
        chunks_stored=len(chunks),
    )
