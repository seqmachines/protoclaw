"""Publisher agent — writes validated protocols to DB and manages reviews."""

from pathlib import Path

from google.adk.agents import LlmAgent

from protocrawl.agents.publisher.tools import publish_protocol, upload_artifact
from protocrawl.config import settings

_PROMPT_PATH = (
    Path(__file__).parent.parent.parent.parent.parent
    / "docs"
    / "agent-prompts"
    / "publisher.md"
)
_INSTRUCTION = _PROMPT_PATH.read_text() if _PROMPT_PATH.exists() else ""

publisher_agent = LlmAgent(
    name="Publisher",
    model=settings.gemini_model,
    description=(
        "Writes validated protocol records to the database, "
        "uploads artifacts to GCS, and manages the human review "
        "workflow based on confidence scores."
    ),
    instruction=_INSTRUCTION,
    tools=[publish_protocol, upload_artifact],
    output_key="publish_results",
)
