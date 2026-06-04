from crewai import Agent

from app.llm.provider import crewai_llm
from app.tools.file_validator import FileValidatorTool
from app.tools.intent_classifier import IntentClassifierTool
from app.tools.metadata_extractor import MetadataExtractorTool
from app.tools.request_logger import RequestLoggerTool


def create_receptionist_agent() -> Agent:
    return Agent(
        role="Receptionist",
        goal=(
            "Ensure every incoming request is valid, well-formed, and routed to the correct "
            "specialist agent with all necessary context attached."
        ),
        backstory=(
            "You are a meticulous intake coordinator. You never skip validation, always log what "
            "you receive, and hand off clean, structured work orders to your colleagues."
        ),
        llm=crewai_llm(),
        tools=[
            FileValidatorTool(),
            MetadataExtractorTool(),
            IntentClassifierTool(),
            RequestLoggerTool(),
        ],
        allow_delegation=False,
        max_iter=5,
        max_execution_time=30,
        verbose=True,
    )
