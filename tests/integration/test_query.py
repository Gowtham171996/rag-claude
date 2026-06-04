"""
Integration tests for POST /query.
Both embed and Crew calls are mocked so tests run without API keys.
"""
import io
import json


def _seed_collection(client, auth_headers, sample_txt_bytes, mocker, collection="query_test"):
    mocker.patch(
        "app.ingestion.embedder.embed_texts",
        side_effect=lambda texts: [[0.1] * 1024 for _ in texts],
    )
    r = client.post(
        "/api/v1/ingest-documents",
        files={"file": ("sample.txt", io.BytesIO(sample_txt_bytes), "text/plain")},
        data={"collection_name": collection},
        headers=auth_headers,
    )
    assert r.status_code == 200


def _mock_crew(mocker):
    mocker.patch(
        "app.agents.crew.run_query_crew",
        return_value={
            "answer": "TechCorp revenue was $4.2 billion [1].",
            "sources": [
                {
                    "document_id": "abc",
                    "filename": "sample.txt",
                    "chunk_index": 0,
                    "page": None,
                    "excerpt": "Total revenue reached $4.2 billion",
                    "score": 0.92,
                }
            ],
        },
    )


def test_query_returns_answer(client, auth_headers, sample_txt_bytes, mocker):
    _seed_collection(client, auth_headers, sample_txt_bytes, mocker)
    _mock_crew(mocker)
    response = client.post(
        "/api/v1/query",
        json={"question": "What was the total revenue?", "collection_name": "query_test"},
        headers=auth_headers,
    )
    assert response.status_code == 200
    data = response.json()
    assert len(data["answer"]) > 0
    assert isinstance(data["sources"], list)


def test_query_returns_sources(client, auth_headers, sample_txt_bytes, mocker):
    _seed_collection(client, auth_headers, sample_txt_bytes, mocker)
    _mock_crew(mocker)
    response = client.post(
        "/api/v1/query",
        json={"question": "Revenue?", "collection_name": "query_test"},
        headers=auth_headers,
    )
    assert response.status_code == 200
    sources = response.json()["sources"]
    assert len(sources) >= 1
    assert sources[0]["filename"] == "sample.txt"


def test_query_empty_question(client, auth_headers):
    response = client.post(
        "/api/v1/query",
        json={"question": ""},
        headers=auth_headers,
    )
    assert response.status_code == 422


def test_query_nonexistent_collection(client, auth_headers):
    response = client.post(
        "/api/v1/query",
        json={"question": "What happened?", "collection_name": "does_not_exist_xyz"},
        headers=auth_headers,
    )
    assert response.status_code == 404


def test_query_requires_auth(client):
    response = client.post(
        "/api/v1/query",
        json={"question": "hello"},
    )
    assert response.status_code == 401


def test_query_top_k_bounds(client, auth_headers):
    response = client.post(
        "/api/v1/query",
        json={"question": "hello", "top_k": 0},
        headers=auth_headers,
    )
    assert response.status_code == 422
