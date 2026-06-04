"""
Run the golden dataset queries against the live /query endpoint and
evaluate each answer for keyword presence (basic recall check).
"""
import json
import time

import httpx
from crewai.tools import BaseTool
from pydantic import BaseModel, Field


class GoldenDatasetInput(BaseModel):
    collection_name: str = Field(default="default", description="Qdrant collection to query against")
    api_base_url: str = Field(default="http://localhost:8000", description="Base URL of the RAG API")


class GoldenDatasetTool(BaseTool):
    name: str = "GoldenDatasetTool"
    description: str = (
        "Runs predefined golden-dataset queries against the live /query endpoint "
        "and checks whether expected keywords appear in each answer."
    )
    args_schema: type[BaseModel] = GoldenDatasetInput

    def _run(self, collection_name: str = "default", api_base_url: str = "http://localhost:8000") -> str:
        from app.config import settings

        # Load golden dataset
        try:
            with open("/app/tests/fixtures/queries.json") as f:
                cases = json.load(f)
        except FileNotFoundError:
            return json.dumps({"error": "queries.json not found at tests/fixtures/queries.json"})

        results = []
        passed = 0

        for case in cases:
            question = case["question"]
            expected_keywords = [kw.lower() for kw in case.get("expected_keywords", [])]

            start = time.monotonic()
            try:
                resp = httpx.post(
                    f"{api_base_url}/api/v1/query",
                    json={"question": question, "collection_name": collection_name},
                    headers={"X-API-Key": settings.api_key},
                    timeout=60,
                )
                latency_ms = int((time.monotonic() - start) * 1000)

                if resp.status_code != 200:
                    results.append({
                        "question": question,
                        "status": "error",
                        "detail": f"HTTP {resp.status_code}",
                    })
                    continue

                data = resp.json()
                answer = data.get("answer", "").lower()
                sources_count = len(data.get("sources", []))

                found = [kw for kw in expected_keywords if kw in answer]
                missing = [kw for kw in expected_keywords if kw not in answer]
                ok = len(missing) == 0

                if ok:
                    passed += 1

                results.append({
                    "question": question,
                    "status": "pass" if ok else "fail",
                    "keywords_found": found,
                    "keywords_missing": missing,
                    "sources_returned": sources_count,
                    "latency_ms": latency_ms,
                    "answer_snippet": data.get("answer", "")[:200],
                })

            except Exception as e:
                results.append({"question": question, "status": "error", "detail": str(e)})

        return json.dumps({
            "total": len(cases),
            "passed": passed,
            "failed": len(cases) - passed,
            "pass_rate": f"{(passed / len(cases) * 100):.0f}%" if cases else "N/A",
            "results": results,
        }, indent=2)
