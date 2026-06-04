import os

import pytest
from fastapi.testclient import TestClient
from qdrant_client import QdrantClient

# Set dummy env vars before importing app so pydantic-settings doesn't fail
os.environ.setdefault("ANTHROPIC_API_KEY", "test-anthropic-key")
os.environ.setdefault("VOYAGE_API_KEY", "test-voyage-key")
os.environ.setdefault("API_KEY", "test-api-key")

from app.main import app
from app import db as _db_module
import app.db.qdrant as qdrant_module


@pytest.fixture(scope="session")
def in_memory_qdrant() -> QdrantClient:
    return QdrantClient(":memory:")


@pytest.fixture(autouse=True)
def patch_qdrant(in_memory_qdrant, monkeypatch):
    """Redirect all qdrant calls to the in-memory client."""
    monkeypatch.setattr(qdrant_module, "_client", in_memory_qdrant)


@pytest.fixture
def client() -> TestClient:
    return TestClient(app)


@pytest.fixture
def auth_headers() -> dict:
    return {"X-API-Key": "test-api-key"}


@pytest.fixture
def sample_txt_bytes() -> bytes:
    path = os.path.join(os.path.dirname(__file__), "fixtures", "sample.txt")
    with open(path, "rb") as f:
        return f.read()


@pytest.fixture
def sample_pdf_bytes() -> bytes:
    path = os.path.join(os.path.dirname(__file__), "fixtures", "sample.pdf")
    if os.path.exists(path):
        with open(path, "rb") as f:
            return f.read()
    return None
