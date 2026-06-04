"""
Integration tests for POST /ingest-documents.
Voyage AI embed calls are mocked to avoid real API calls in CI.
"""
import io


def _ingest(client, auth_headers, file_bytes, filename="sample.txt", collection="test_ingest"):
    return client.post(
        "/api/v1/ingest-documents",
        files={"file": (filename, io.BytesIO(file_bytes), "text/plain")},
        data={"collection_name": collection},
        headers=auth_headers,
    )


def test_ingest_txt_success(client, auth_headers, sample_txt_bytes, mocker):
    mocker.patch(
        "app.ingestion.embedder.embed_texts",
        side_effect=lambda texts: [[0.1] * 1024 for _ in texts],
    )
    response = _ingest(client, auth_headers, sample_txt_bytes)
    assert response.status_code == 200
    data = response.json()
    assert data["chunks_stored"] > 0
    assert data["filename"] == "sample.txt"
    assert "document_id" in data


def test_ingest_invalid_extension(client, auth_headers):
    response = client.post(
        "/api/v1/ingest-documents",
        files={"file": ("data.xlsx", io.BytesIO(b"content"), "application/octet-stream")},
        headers=auth_headers,
    )
    assert response.status_code == 422


def test_ingest_oversized_file(client, auth_headers):
    big = b"x" * (51 * 1024 * 1024)
    response = client.post(
        "/api/v1/ingest-documents",
        files={"file": ("big.pdf", io.BytesIO(big), "application/pdf")},
        headers=auth_headers,
    )
    assert response.status_code == 422


def test_ingest_requires_auth(client, sample_txt_bytes):
    response = client.post(
        "/api/v1/ingest-documents",
        files={"file": ("sample.txt", io.BytesIO(sample_txt_bytes), "text/plain")},
    )
    assert response.status_code == 401


def test_ingest_bad_metadata_json(client, auth_headers, sample_txt_bytes):
    response = client.post(
        "/api/v1/ingest-documents",
        files={"file": ("sample.txt", io.BytesIO(sample_txt_bytes), "text/plain")},
        data={"metadata": "not-json"},
        headers=auth_headers,
    )
    assert response.status_code == 422


def test_reingest_same_collection(client, auth_headers, sample_txt_bytes, mocker):
    mocker.patch(
        "app.ingestion.embedder.embed_texts",
        side_effect=lambda texts: [[0.1] * 1024 for _ in texts],
    )
    # First ingest
    r1 = _ingest(client, auth_headers, sample_txt_bytes, collection="reingest_test")
    assert r1.status_code == 200
    first_count = r1.json()["chunks_stored"]

    # Second ingest — should succeed (idempotent, not double-store same content)
    r2 = _ingest(client, auth_headers, sample_txt_bytes, collection="reingest_test")
    assert r2.status_code == 200
    assert r2.json()["chunks_stored"] == first_count
