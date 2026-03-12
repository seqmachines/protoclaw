"""Normalizer agent — converts raw parsed data to canonical Protocol schema."""

from pathlib import Path

from google.adk.agents import LlmAgent

from protocrawl.agents.normalizer.tools import compute_confidence, normalize_to_schema
from protocrawl.config import settings

_PROMPT_PATH = (
    Path(__file__).parent.parent.parent.parent.parent
    / "docs"
    / "agent-prompts"
    / "normalizer.md"
)
_INSTRUCTION = _PROMPT_PATH.read_text() if _PROMPT_PATH.exists() else ""

normalizer_agent = LlmAgent(
    name="Normalizer",
    model=settings.gemini_model,
    description=(
        "Validates and normalizes raw parsed protocol data into the "
        "canonical Protocrawl schema, computing confidence scores."
    ),
    instruction=_INSTRUCTION,
    tools=[normalize_to_schema, compute_confidence],
    output_key="normalized_protocols",
)
