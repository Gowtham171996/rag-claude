"""Run the pytest test suite and return a structured result."""
import json
import subprocess

from crewai.tools import BaseTool
from pydantic import BaseModel, Field


class TestRunnerInput(BaseModel):
    path: str = Field(default="tests/", description="Test path to run (e.g. 'tests/unit/')")
    extra_args: str = Field(default="", description="Extra pytest args, e.g. '-k test_chunking'")


class TestRunnerTool(BaseTool):
    name: str = "TestRunnerTool"
    description: str = "Runs the pytest test suite and returns pass/fail counts and any failure details."
    args_schema: type[BaseModel] = TestRunnerInput

    def _run(self, path: str = "tests/", extra_args: str = "") -> str:
        cmd = ["python", "-m", "pytest", path, "--tb=short", "-q", "--no-header"]
        if extra_args:
            cmd += extra_args.split()

        try:
            proc = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=120,
                cwd="/app",
            )
            output = proc.stdout + proc.stderr
            passed = output.count(" passed")
            failed = output.count(" failed")
            error = output.count(" error")

            return json.dumps({
                "exit_code": proc.returncode,
                "status": "passed" if proc.returncode == 0 else "failed",
                "summary": output.strip().split("\n")[-1] if output.strip() else "no output",
                "details": output[-3000:],  # last 3000 chars to stay within context
            }, indent=2)
        except subprocess.TimeoutExpired:
            return json.dumps({"status": "timeout", "detail": "Test run exceeded 120 seconds."})
        except Exception as e:
            return json.dumps({"status": "error", "detail": str(e)})
