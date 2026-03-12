"""Source Scout agent — discovers candidate protocol documents."""

from pathlib import Path

from google.adk.agents import LlmAgent

from protocrawl.agents.source_scout.tools import (
    fetch_page_text,
    load_seed_sources,
    search_arxiv,
    search_github,
)
from protocrawl.config import settings

_PROMPT_PATH = (
    Path(__file__).parent.parent.parent.parent.parent
    / "docs"
    / "agent-prompts"
    / "source_scout.md"
)
_INSTRUCTION = _PROMPT_PATH.read_text() if _PROMPT_PATH.exists() else ""

source_scout_agent = LlmAgent(
    name="SourceScout",
    model=settings.gemini_model,
    description=(
        "Monitors and discovers candidate protocol documents from "
        "papers, repos, vendor sites, and curated seed lists."
    ),
    instruction=_INSTRUCTION,
    tools=[load_seed_sources, search_arxiv, search_github, fetch_page_text],
    output_key="candidate_sources",
)
