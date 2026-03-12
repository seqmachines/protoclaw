"""Parser agent — extracts structured protocol fields from source documents."""

from pathlib import Path

from google.adk.agents import LlmAgent

from protocrawl.agents.parser.tools import (
    extract_adapters,
    extract_barcodes,
    extract_metadata,
    extract_protocol_details,
    extract_read_structure,
    extract_reagents,
    extract_seqspec,
)
from protocrawl.config import settings

_PROMPT_PATH = (
    Path(__file__).parent.parent.parent.parent.parent
    / "docs"
    / "agent-prompts"
    / "parser.md"
)
_INSTRUCTION = _PROMPT_PATH.read_text() if _PROMPT_PATH.exists() else ""

parser_agent = LlmAgent(
    name="Parser",
    model=settings.gemini_model,
    description=(
        "Extracts structured protocol fields (read structure, barcodes, "
        "adapters, reagents, metadata) from source documents."
    ),
    instruction=_INSTRUCTION,
    tools=[
        extract_metadata,
        extract_read_structure,
        extract_barcodes,
        extract_adapters,
        extract_reagents,
        extract_protocol_details,
        extract_seqspec,
    ],
    output_key="parsed_protocols",
)
