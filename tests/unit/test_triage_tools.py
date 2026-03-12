"""Tests for triage tools with mocked LLM responses."""

from unittest.mock import AsyncMock, patch

import pytest

from protocrawl.agents.triage.tools import (
    CategoryResult,
    RelevanceResult,
    assign_category,
    classify_relevance,
    triage_source,
)


@pytest.fixture
def mock_glm5():
    with patch("protocrawl.agents.triage.tools.glm5") as mock:
        yield mock


@pytest.mark.asyncio
async def test_classify_relevance_relevant(mock_glm5):
    mock_glm5.extract_structured = AsyncMock(
        return_value=RelevanceResult(
            score=0.92,
            reason=(
                "Primary method paper describing a novel "
                "scRNA-seq protocol with detailed read structure."
            ),
            is_relevant=True,
        )
    )

    result = await classify_relevance(
        title="A new droplet-based single-cell RNA-seq method",
        abstract_or_snippet=(
            "We present a novel approach to single-cell "
            "transcriptomics using barcoded hydrogel beads..."
        ),
        source_type="paper",
    )
    assert result.score >= 0.9
    assert result.is_relevant is True


@pytest.mark.asyncio
async def test_classify_relevance_not_relevant(mock_glm5):
    mock_glm5.extract_structured = AsyncMock(
        return_value=RelevanceResult(
            score=0.15,
            reason="Software tool paper for data analysis, not a protocol description.",
            is_relevant=False,
        )
    )

    result = await classify_relevance(
        title="CellRanger: a pipeline for processing 10x data",
        abstract_or_snippet=(
            "We present a computational pipeline for alignment and quantification..."
        ),
        source_type="paper",
    )
    assert result.score < 0.5
    assert result.is_relevant is False


@pytest.mark.asyncio
async def test_assign_category(mock_glm5):
    mock_glm5.extract_structured = AsyncMock(
        return_value=CategoryResult(
            assay_family="scRNA-seq",
            confidence=0.95,
            reasoning="The paper describes a droplet-based single-cell RNA-seq method.",
        )
    )

    result = await assign_category(
        title="Drop-seq protocol",
        abstract_or_snippet="Droplet-based single-cell RNA-seq...",
    )
    assert result.assay_family == "scRNA-seq"
    assert result.confidence >= 0.9


@pytest.mark.asyncio
async def test_triage_source_relevant(mock_glm5):
    mock_glm5.extract_structured = AsyncMock(
        side_effect=[
            RelevanceResult(
                score=0.88,
                reason="Vendor documentation with protocol details.",
                is_relevant=True,
            ),
            CategoryResult(
                assay_family="scATAC-seq",
                confidence=0.90,
                reasoning="Describes chromatin accessibility profiling.",
            ),
        ]
    )

    result = await triage_source(
        title="10x Chromium Single Cell ATAC",
        abstract_or_snippet="Profile open chromatin at single-cell resolution...",
        source_type="vendor_docs",
    )
    assert result.should_parse is True
    assert result.category is not None
    assert result.category.assay_family == "scATAC-seq"


@pytest.mark.asyncio
async def test_triage_source_not_relevant(mock_glm5):
    mock_glm5.extract_structured = AsyncMock(
        return_value=RelevanceResult(
            score=0.2,
            reason="Marketing page with no technical details.",
            is_relevant=False,
        )
    )

    result = await triage_source(
        title="Company About Page",
        abstract_or_snippet="We are a leading biotech company...",
        source_type="vendor_docs",
    )
    assert result.should_parse is False
    assert result.category is None
    # Only one LLM call — no category assignment for irrelevant sources
    assert mock_glm5.extract_structured.call_count == 1
