"""Check that all services (Qdrant, Ollama) are reachable and healthy."""
import json

from crewai.tools import BaseTool
from pydantic import BaseModel


class HealthCheckInput(BaseModel):
    pass   # no input needed


class HealthCheckTool(BaseTool):
    name: str = "HealthCheckTool"
    description: str = "Checks the health of all dependent services: Qdrant and Ollama."
    args_schema: type[BaseModel] = HealthCheckInput

    def _run(self) -> str:
        import httpx
        from app.config import settings

        results: dict[str, str] = {}

        # Qdrant
        try:
            r = httpx.get(f"http://{settings.qdrant_host}:{settings.qdrant_port}/healthz", timeout=5)
            results["qdrant"] = "ok" if r.status_code == 200 else f"degraded ({r.status_code})"
        except Exception as e:
            results["qdrant"] = f"unreachable ({e})"

        # Ollama
        try:
            r = httpx.get(f"{settings.ollama_base_url}/api/tags", timeout=5)
            if r.status_code == 200:
                models = [m["name"] for m in r.json().get("models", [])]
                results["ollama"] = "ok"
                results["ollama_models"] = models
            else:
                results["ollama"] = f"degraded ({r.status_code})"
        except Exception as e:
            results["ollama"] = f"unreachable ({e})"

        overall = "healthy" if all(v == "ok" for k, v in results.items() if k != "ollama_models") else "degraded"
        results["overall"] = overall
        return json.dumps(results, indent=2)
