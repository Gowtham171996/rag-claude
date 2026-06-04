"""
Unit tests for individual CrewAI tools (not the full crew run).
"""
import json

from app.tools.file_validator import FileValidatorTool
from app.tools.metadata_extractor import MetadataExtractorTool
from app.tools.intent_classifier import IntentClassifierTool
from app.tools.context_assembler import ContextAssemblerTool


# ── FileValidatorTool ─────────────────────────────────────────────────────────

def test_file_validator_accepts_pdf():
    tool = FileValidatorTool()
    result = json.loads(tool._run(filename="doc.pdf", size_bytes=1024))
    assert result["valid"] is True


def test_file_validator_rejects_xlsx():
    tool = FileValidatorTool()
    result = json.loads(tool._run(filename="data.xlsx", size_bytes=1024))
    assert result["valid"] is False
    assert "xlsx" in result["error"]


def test_file_validator_rejects_oversized():
    tool = FileValidatorTool()
    result = json.loads(tool._run(filename="big.pdf", size_bytes=51 * 1024 * 1024))
    assert result["valid"] is False
    assert "large" in result["error"].lower()


def test_file_validator_accepts_txt_and_docx():
    tool = FileValidatorTool()
    for ext in ("file.txt", "report.docx"):
        result = json.loads(tool._run(filename=ext, size_bytes=500))
        assert result["valid"] is True, f"Expected valid for {ext}"


# ── MetadataExtractorTool ─────────────────────────────────────────────────────

def test_metadata_extractor_returns_fields():
    tool = MetadataExtractorTool()
    result = json.loads(tool._run(filename="report.pdf", size_bytes=2048))
    assert result["filename"] == "report.pdf"
    assert result["size_bytes"] == 2048
    assert "upload_timestamp" in result


def test_metadata_extractor_merges_user_metadata():
    tool = MetadataExtractorTool()
    result = json.loads(
        tool._run(filename="f.txt", size_bytes=100, user_metadata='{"dept": "finance"}')
    )
    assert result["user_metadata"]["dept"] == "finance"


# ── IntentClassifierTool ──────────────────────────────────────────────────────

def test_intent_classifier_ingest():
    tool = IntentClassifierTool()
    result = json.loads(tool._run(request_type="ingest"))
    assert result["intent"] == "ingest"


def test_intent_classifier_query():
    tool = IntentClassifierTool()
    result = json.loads(tool._run(request_type="query"))
    assert result["intent"] == "query"


# ── ContextAssemblerTool ──────────────────────────────────────────────────────

def test_context_assembler_formats_chunks():
    tool = ContextAssemblerTool()
    chunks_json = json.dumps({
        "chunks": [
            {"filename": "a.txt", "page": 1, "text": "Hello world", "score": 0.9, "chunk_index": 0},
        ]
    })
    result = json.loads(tool._run(chunks_json=chunks_json))
    assert result["empty"] is False
    assert "Hello world" in result["context"]
    assert "a.txt" in result["context"]


def test_context_assembler_empty_chunks():
    tool = ContextAssemblerTool()
    result = json.loads(tool._run(chunks_json=json.dumps({"chunks": []})))
    assert result["empty"] is True
