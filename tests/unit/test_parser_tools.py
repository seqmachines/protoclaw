"""Tests for parser tools with mocked LLM responses."""

from unittest.mock import AsyncMock, patch

import pytest

from protocrawl.agents.parser.tools import (
    ParsedBarcodes,
    ParsedMetadata,
    ParsedReadStructure,
    extract_barcodes,
    extract_metadata,
    extract_read_structure,
)


@pytest.fixture
def mock_extract():
    """Patch glm5.extract_structured to return controlled responses."""
    with patch("protocrawl.agents.parser.tools.glm5") as mock:
        yield mock


@pytest.mark.asyncio
async def test_extract_metadata(mock_extract):
    mock_extract.extract_structured = AsyncMock(
        return_value=ParsedMetadata(
            name="10x Chromium 3' v3",
            version="v3",
            assay_family="scRNA-seq",
            molecule_type="RNA",
            description="Droplet-based scRNA-seq using 10x Chromium.",
            vendor="10x Genomics",
            platform="Illumina",
        )
    )

    result = await extract_metadata("Some protocol document text...")
    assert result.name == "10x Chromium 3' v3"
    assert result.assay_family == "scRNA-seq"
    assert result.vendor == "10x Genomics"
    mock_extract.extract_structured.assert_called_once()


@pytest.mark.asyncio
async def test_extract_read_structure(mock_extract):
    mock_extract.extract_structured = AsyncMock(
        return_value=ParsedReadStructure(
            read_type="paired-end",
            read1_length=28,
            read2_length=91,
            index1_length=8,
            segments=[
                {
                    "role": "cell_barcode",
                    "read_number": 1,
                    "start_pos": 0,
                    "length": 16,
                },
                {
                    "role": "umi",
                    "read_number": 1,
                    "start_pos": 16,
                    "length": 12,
                },
                {
                    "role": "cdna",
                    "read_number": 2,
                    "start_pos": 0,
                    "length": 91,
                },
            ],
        )
    )

    result = await extract_read_structure("Some protocol document text...")
    assert result.read_type == "paired-end"
    assert result.read1_length == 28
    assert len(result.segments) == 3
    assert result.segments[0].role == "cell_barcode"


@pytest.mark.asyncio
async def test_extract_barcodes(mock_extract):
    mock_extract.extract_structured = AsyncMock(
        return_value=ParsedBarcodes(
            barcodes=[
                {
                    "role": "cell_barcode",
                    "length": 16,
                    "whitelist_source": "3M-february-2018.txt.gz",
                    "addition_method": "ligation",
                },
                {
                    "role": "umi",
                    "length": 12,
                    "addition_method": "ligation",
                },
            ]
        )
    )

    result = await extract_barcodes("Some protocol document text...")
    assert len(result.barcodes) == 2
    assert result.barcodes[0].role == "cell_barcode"
    assert result.barcodes[0].length == 16
    assert result.barcodes[1].role == "umi"
