"""Formatter agent — renders protocol outputs in multiple formats."""

from pathlib import Path

from google.adk.agents import LlmAgent

from protocrawl.agents.formatter.tools import (
    format_protocol,
    generate_json,
    generate_summary,
    render_read_diagram,
)
from protocrawl.config import settings

_PROMPT_PATH = (
    Path(__file__).parent.parent.parent.parent.parent
    / "docs"
    / "agent-prompts"
    / "formatter.md"
)
_INSTRUCTION = _PROMPT_PATH.read_text() if _PROMPT_PATH.exists() else ""

formatter_agent = LlmAgent(
    name="Formatter",
    model=settings.gemini_model,
    description=(
        "Renders normalized protocol records into ASCII read diagrams, "
        "human-readable summaries, and canonical JSON."
    ),
    instruction=_INSTRUCTION,
    tools=[
        render_read_diagram,
        generate_summary,
        generate_json,
        format_protocol,
    ],
    output_key="formatted_outputs",
)
