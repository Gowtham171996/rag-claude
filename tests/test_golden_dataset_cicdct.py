"""
CI/CD Continuous Testing — Golden Dataset

Loads golden_dataset_cicdct.json and fires each question at the live
/query endpoint. Tests are parameterised so each case appears as a
separate pytest result.

Run locally:
    pytest tests/test_golden_dataset_cicdct.py -v

Run against a non-default API URL:
    API_URL=http://staging:8000 pytest tests/test_golden_dataset_cicdct.py -v

Prerequisites:
    - RAG API running on localhost:8000
    - gowtham-resume-LLM.pdf already ingested into the 'default' collection
    - API_KEY env var set (or defaults to 'my-secret-key-123' for local dev)
"""

import json
import os
from pathlib import Path

import httpx
import pytest

API_URL = os.getenv("API_URL", "http://localhost:8000")
API_KEY = os.getenv("API_KEY", "my-secret-key-123")
COLLECTION = os.getenv("COLLECTION_NAME", "default")

DATASET_PATH = Path(__file__).parent / "fixtures" / "golden_dataset_cicdct.json"


def load_cases():
    with open(DATASET_PATH) as f:
        return json.load(f)


def pytest_generate_tests(metafunc):
    if "case" in metafunc.fixturenames:
        cases = load_cases()
        metafunc.parametrize(
            "case",
            cases,
            ids=[c["id"] for c in cases],
        )


@pytest.mark.integration
def test_golden_case(case):
    """
    Each golden dataset case must:
    1. Receive a 200 response from /query
    2. Return at least one source chunk
    3. Have ALL expected_keywords present in the answer (case-insensitive)
    """
    resp = httpx.post(
        f"{API_URL}/api/v1/query",
        json={"question": case["question"], "collection_name": COLLECTION},
        headers={"X-API-Key": API_KEY},
        timeout=120,
    )

    assert resp.status_code == 200, (
        f"[{case['id']}] HTTP {resp.status_code}: {resp.text[:300]}"
    )

    data = resp.json()
    answer = data.get("answer", "").lower()
    sources = data.get("sources", [])

    # Must have retrieved at least one source
    assert len(sources) > 0, (
        f"[{case['id']}] No sources returned for: {case['question']}\n"
        f"Answer: {data.get('answer', '')[:300]}"
    )

    # All expected keywords must appear in the answer
    missing = [kw for kw in case["expected_keywords"] if kw.lower() not in answer]
    assert not missing, (
        f"[{case['id']}] Missing keywords {missing}\n"
        f"Category: {case['category']} | Difficulty: {case['difficulty']}\n"
        f"Question: {case['question']}\n"
        f"Ground truth: {case['ground_truth']}\n"
        f"Actual answer: {data.get('answer', '')[:500]}"
    )


@pytest.mark.integration
def test_golden_dataset_overall_pass_rate():
    """
    Aggregate test: at least 70% of all golden cases must pass.
    This gives a system-level quality gate for CI/CD.
    """
    cases = load_cases()
    passed = 0
    failures = []

    for case in cases:
        try:
            resp = httpx.post(
                f"{API_URL}/api/v1/query",
                json={"question": case["question"], "collection_name": COLLECTION},
                headers={"X-API-Key": API_KEY},
                timeout=120,
            )
            if resp.status_code != 200:
                failures.append(f"{case['id']}: HTTP {resp.status_code}")
                continue

            answer = resp.json().get("answer", "").lower()
            missing = [kw for kw in case["expected_keywords"] if kw.lower() not in answer]
            if not missing:
                passed += 1
            else:
                failures.append(f"{case['id']}: missing {missing}")
        except Exception as e:
            failures.append(f"{case['id']}: {e}")

    total = len(cases)
    pass_rate = passed / total if total else 0

    report = (
        f"\nGolden Dataset Results: {passed}/{total} passed ({pass_rate:.0%})\n"
        + ("\nFailures:\n" + "\n".join(f"  - {f}" for f in failures) if failures else "")
    )

    assert pass_rate >= 0.70, f"Pass rate {pass_rate:.0%} below 70% threshold.{report}"
    print(report)
