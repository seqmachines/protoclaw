"""Tests for source scout tools."""

from pathlib import Path

import pytest

from protocrawl.agents.source_scout.tools import (
    fetch_page_text,
    get_search_keywords,
    load_seed_sources,
)

SEEDS_DIR = Path(__file__).parent.parent.parent / "seeds"


@pytest.mark.asyncio
async def test_load_seed_sources():
    sources = await load_seed_sources(str(SEEDS_DIR / "sources.yaml"))
    assert len(sources) > 0
    assert all(s.url for s in sources)
    assert all(s.source_type for s in sources)

    # Check we have a mix of source types
    types = {s.source_type for s in sources}
    assert "vendor_docs" in types
    assert "paper" in types


@pytest.mark.asyncio
async def test_load_seed_sources_missing_file():
    sources = await load_seed_sources("/nonexistent/path.yaml")
    assert sources == []


def test_get_search_keywords():
    keywords = get_search_keywords(str(SEEDS_DIR / "sources.yaml"))
    assert len(keywords) > 0
    assert any("RNA-seq" in kw for kw in keywords)


def test_get_search_keywords_missing_file():
    keywords = get_search_keywords("/nonexistent/path.yaml")
    assert keywords == []


@pytest.mark.asyncio
async def test_load_seed_sources_has_expected_entries():
    sources = await load_seed_sources(str(SEEDS_DIR / "sources.yaml"))
    urls = {s.url for s in sources}
    # Check a few known seed URLs are present
    assert any("teichlab" in u for u in urls)
    assert any("10xgenomics" in u for u in urls)
    assert any("mccarrolllab" in u for u in urls)


@pytest.mark.asyncio
async def test_fetch_page_text_html(httpx_mock):
    httpx_mock.add_response(
        url="https://example.com/protocol",
        text=(
            "<html><head><title>Protocol Page</title></head>"
            "<body><h1>Protocol</h1><p>Read 1 uses a 16bp barcode.</p></body></html>"
        ),
        headers={"content-type": "text/html; charset=utf-8"},
    )

    source = await fetch_page_text("https://example.com/protocol")

    assert source.title == "Protocol Page"
    assert "16bp barcode" in source.raw_text
    assert source.metadata["fetched_from_pdf"] is False
    assert source.fetched_at is not None


@pytest.mark.asyncio
async def test_fetch_page_text_pdf(httpx_mock, monkeypatch: pytest.MonkeyPatch):
    httpx_mock.add_response(
        url="https://example.com/protocol.pdf",
        content=b"%PDF-1.4 fake pdf bytes",
        headers={"content-type": "application/pdf"},
    )

    monkeypatch.setattr(
        "protocrawl.agents.source_scout.tools._extract_pdf_text",
        lambda pdf_bytes, max_chars: (
            "Chromium GEM-X protocol text",
            "Chromium GEM-X User Guide",
            {"page_count": 12},
        ),
    )

    source = await fetch_page_text("https://example.com/protocol.pdf")

    assert source.title == "Chromium GEM-X User Guide"
    assert "protocol text" in source.raw_text
    assert source.metadata["fetched_from_pdf"] is True
    assert source.metadata["page_count"] == 12


@pytest.mark.asyncio
async def test_fetch_page_text_local_pdf(tmp_path, monkeypatch: pytest.MonkeyPatch):
    pdf_path = tmp_path / "protocol.pdf"
    pdf_path.write_bytes(b"%PDF-1.4 local fake pdf bytes")

    monkeypatch.setattr(
        "protocrawl.agents.source_scout.tools._extract_pdf_text",
        lambda pdf_bytes, max_chars: (
            "Local PDF protocol text",
            "Local PDF Guide",
            {"page_count": 3},
        ),
    )

    source = await fetch_page_text(str(pdf_path))

    assert source.url.startswith("file://")
    assert source.title == "Local PDF Guide"
    assert source.metadata["fetched_from_pdf"] is True
    assert source.metadata["local_file"] is True


@pytest.mark.asyncio
async def test_fetch_page_text_local_text_file(tmp_path):
    text_path = tmp_path / "protocol.txt"
    text_path.write_text("Local protocol notes with read structure")

    source = await fetch_page_text(str(text_path))

    assert source.url.startswith("file://")
    assert "Local protocol notes" in source.raw_text
    assert source.metadata["local_file"] is True
    assert source.metadata["fetched_from_pdf"] is False
