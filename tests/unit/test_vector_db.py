"""
Vector DB unit tests use the in-memory Qdrant client injected by conftest.py.
"""
import uuid

import pytest
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams

import app.db.qdrant as qdrant_module
from app.db.qdrant import ensure_collection, search, upsert_chunks, delete_by_document_id
from app.config import settings


COLLECTION = "test_unit"


@pytest.fixture(autouse=True)
def setup_collection(in_memory_qdrant):
    in_memory_qdrant.recreate_collection(
        collection_name=COLLECTION,
        vectors_config=VectorParams(size=settings.embedding_dim, distance=Distance.COSINE),
    )
    yield


def _make_chunk(doc_id: str, filename: str, index: int) -> tuple[dict, list[float]]:
    point_id = str(uuid.uuid4())
    chunk = {
        "id": point_id,
        "payload": {
            "document_id": doc_id,
            "filename": filename,
            "chunk_index": index,
            "page": None,
            "char_start": 0,
            "char_end": 100,
            "text": f"chunk {index} of {filename}",
            "token_count": 10,
            "user_metadata": {},
        },
    }
    vector = [0.1 * (index + 1)] * settings.embedding_dim
    return chunk, vector


def test_upsert_and_search(in_memory_qdrant):
    doc_id = str(uuid.uuid4())
    chunk, vector = _make_chunk(doc_id, "test.txt", 0)
    upsert_chunks(COLLECTION, [chunk], [vector])

    hits = search(COLLECTION, query_vector=vector, top_k=5, filters={}, score_threshold=0.0)
    assert len(hits) >= 1
    assert hits[0].payload["document_id"] == doc_id


def test_upsert_idempotent(in_memory_qdrant):
    doc_id = str(uuid.uuid4())
    chunk, vector = _make_chunk(doc_id, "dup.txt", 0)
    upsert_chunks(COLLECTION, [chunk], [vector])
    upsert_chunks(COLLECTION, [chunk], [vector])  # second upsert

    count = in_memory_qdrant.count(collection_name=COLLECTION).count
    assert count == 1


def test_delete_by_document_id(in_memory_qdrant):
    doc_id = str(uuid.uuid4())
    chunks = [_make_chunk(doc_id, "del.txt", i) for i in range(3)]
    upsert_chunks(COLLECTION, [c[0] for c in chunks], [c[1] for c in chunks])

    delete_by_document_id(COLLECTION, doc_id)

    vector = [0.1] * settings.embedding_dim
    hits = search(COLLECTION, query_vector=vector, top_k=10, filters={}, score_threshold=0.0)
    assert all(h.payload["document_id"] != doc_id for h in hits)


def test_filter_by_filename(in_memory_qdrant):
    doc_id = str(uuid.uuid4())
    chunk_a, vec_a = _make_chunk(doc_id, "alpha.txt", 0)
    chunk_b, vec_b = _make_chunk(str(uuid.uuid4()), "beta.txt", 0)
    upsert_chunks(COLLECTION, [chunk_a, chunk_b], [vec_a, vec_b])

    hits = search(
        COLLECTION,
        query_vector=vec_a,
        top_k=10,
        filters={"filename": "alpha.txt"},
        score_threshold=0.0,
    )
    assert all(h.payload["filename"] == "alpha.txt" for h in hits)
