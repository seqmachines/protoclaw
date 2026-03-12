"""Triage agent — evaluates source document relevance and assigns categories."""

from pathlib import Path

from google.adk.agents import LlmAgent

from protocrawl.agents.triage.tools import (
    assign_category,
    classify_relevance,
    triage_source,
)
from protocrawl.config import settings

_PROMPT_PATH = (
    Path(__file__).parent.parent.parent.parent.parent
    / "docs"
    / "agent-prompts"
    / "triage.md"
)
_INSTRUCTION = _PROMPT_PATH.read_text() if _PROMPT_PATH.exists() else ""

triage_agent = LlmAgent(
    name="Triage",
    model=settings.gemini_model,
    description=(
        "Evaluates candidate source documents for relevance to "
        "sequencing protocols and assigns assay family categories."
    ),
    instruction=_INSTRUCTION,
    tools=[classify_relevance, assign_category, triage_source],
    output_key="triaged_sources",
)
