import pytest
from pydantic import ValidationError

from app.api.schemas import IngestResponse, QueryRequest, QueryResponse, SourceChunk


def test_query_request_requires_question():
    with pytest.raises(ValidationError):
        QueryRequest(question="")


def test_query_request_top_k_too_low():
    with pytest.raises(ValidationError):
        QueryRequest(question="hello", top_k=0)


def test_query_request_top_k_too_high():
    with pytest.raises(ValidationError):
        QueryRequest(question="hello", top_k=21)


def test_query_request_defaults():
    q = QueryRequest(question="hello")
    assert q.collection_name == "default"
    assert q.top_k == 5
    assert q.filters == {}


def test_ingest_response_has_uuid():
    import uuid
    r = IngestResponse(filename="f.txt", collection="default", chunks_stored=3)
    uuid.UUID(r.document_id)  # raises if not a valid UUID


def test_source_chunk_model():
    s = SourceChunk(
        document_id="abc",
        filename="f.txt",
        chunk_index=0,
        page=None,
        excerpt="text",
        score=0.9,
    )
    assert s.page is None
    assert s.score == 0.9
