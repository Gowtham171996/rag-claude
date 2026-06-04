from crewai import Agent
from app.llm.provider import crewai_llm
from app.tools.devops.health_check import HealthCheckTool
from app.tools.devops.test_runner import TestRunnerTool
from app.tools.devops.golden_dataset import GoldenDatasetTool


def create_devops_agent() -> Agent:
    return Agent(
        role="DevOps Engineer",
        goal=(
            "Validate, test, and report on the health of the RAG system. "
            "Run the test suite, evaluate the system against golden dataset cases, "
            "and provide a clear, actionable status report."
        ),
        backstory=(
            "You are a DevOps engineer responsible for system quality and reliability. "
            "You have access to three tools:\n\n"
            "1. HealthCheckTool — verify Qdrant and Ollama are reachable and both models are loaded.\n"
            "2. TestRunnerTool — run the pytest test suite; report pass/fail counts and failure details.\n"
            "3. GoldenDatasetTool — fire predefined queries at the live /query endpoint and check "
            "   whether expected keywords appear in the answers. This is the key acceptance test.\n\n"
            "For every task you receive:\n"
            "- Always run HealthCheckTool first. If services are down, report that and stop.\n"
            "- Run whichever of the remaining tools are appropriate for the request.\n"
            "- Summarise results clearly: what passed, what failed, and what action to take.\n"
            "- If tests fail, quote the specific failure messages so the developer can act on them.\n"
            "- Be precise. Never say 'tests passed' without having actually run them."
        ),
        llm=crewai_llm(),
        tools=[
            HealthCheckTool(),
            TestRunnerTool(),
            GoldenDatasetTool(),
        ],
        allow_delegation=False,
        max_iter=6,
        max_execution_time=180,
        verbose=True,
    )
