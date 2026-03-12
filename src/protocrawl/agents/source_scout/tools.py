"""Source Scout agent tools for discovering protocol source documents."""

from __future__ import annotations

import hashlib
import re
from io import BytesIO
from datetime import datetime
from pathlib import Path
from urllib.parse import urlparse

import httpx
import yaml

from protocrawl.models.source import SourceDocument


def _infer_title_from_url(url: str) -> str | None:
    path = urlparse(url).path
    name = Path(path).name
    return name or None


def _source_path_from_ref(source_ref: str) -> Path | None:
    parsed = urlparse(source_ref)
    if parsed.scheme in {"http", "https"}:
        return None
    if parsed.scheme == "file":
        return Path(parsed.path)

    candidate = Path(source_ref)
    return candidate if candidate.exists() else None


def _extract_html_text(raw_html: str, max_chars: int) -> tuple[str, str | None]:
    title_match = re.search(
        r"<title[^>]*>(.*?)</title>",
        raw_html,
        flags=re.IGNORECASE | re.DOTALL,
    )
    title = title_match.group(1).strip() if title_match else None

    text = re.sub(r"<script[^>]*>.*?</script>", "", raw_html, flags=re.DOTALL)
    text = re.sub(r"<style[^>]*>.*?</style>", "", text, flags=re.DOTALL)
    text = re.sub(r"<[^>]+>", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text[:max_chars], title


def _extract_pdf_text(pdf_bytes: bytes, max_chars: int) -> tuple[str, str | None, dict]:
    try:
        from pypdf import PdfReader
    except ImportError as exc:
        raise RuntimeError(
            "PDF URL support requires `pypdf`. Reinstall project dependencies "
            "or run `pip install pypdf`."
        ) from exc

    reader = PdfReader(BytesIO(pdf_bytes))
    chunks: list[str] = []
    for page in reader.pages:
        page_text = page.extract_text() or ""
        if page_text:
            chunks.append(page_text)

    text = re.sub(r"\s+", " ", " ".join(chunks)).strip()[:max_chars]
    metadata = reader.metadata or {}
    title = getattr(metadata, "title", None) or metadata.get("/Title")
    return text, title, {"page_count": len(reader.pages)}


def _extract_plain_text(raw_bytes: bytes, max_chars: int) -> str:
    return raw_bytes.decode("utf-8", errors="ignore").strip()[:max_chars]


async def load_seed_sources(
    seeds_path: str | None = None,
) -> list[SourceDocument]:
    """Load curated source URLs from the seeds/sources.yaml file.

    Args:
        seeds_path: Path to sources.yaml. Defaults to seeds/sources.yaml
            relative to the project root.

    Returns:
        List of source documents from the seed file.
    """
    if seeds_path is None:
        seeds_path = str(
            Path(__file__).parent.parent.parent.parent.parent / "seeds" / "sources.yaml"
        )

    path = Path(seeds_path)
    if not path.exists():
        return []

    data = yaml.safe_load(path.read_text())
    sources = data.get("sources", [])

    return [
        SourceDocument(
            url=s["url"],
            title=s.get("title"),
            source_type=s.get("source_type", "unknown"),
        )
        for s in sources
    ]


async def search_arxiv(
    query: str,
    max_results: int = 10,
) -> list[SourceDocument]:
    """Search arXiv for papers matching a query.

    Args:
        query: Search query string (e.g., "single-cell RNA-seq library").
        max_results: Maximum number of results to return.

    Returns:
        List of source documents from arXiv search results.
    """
    import arxiv

    client = arxiv.Client()
    search = arxiv.Search(
        query=query,
        max_results=max_results,
        sort_by=arxiv.SortCriterion.Relevance,
    )

    results = []
    for paper in client.results(search):
        results.append(
            SourceDocument(
                url=paper.entry_id,
                title=paper.title,
                source_type="preprint",
                metadata={
                    "abstract": paper.summary,
                    "authors": [a.name for a in paper.authors],
                    "published": paper.published.isoformat()
                    if paper.published
                    else None,
                    "categories": paper.categories,
                },
                discovered_at=datetime.utcnow(),
            )
        )

    return results


async def search_github(
    query: str,
    max_results: int = 10,
) -> list[SourceDocument]:
    """Search GitHub repositories for protocol-related content.

    Args:
        query: Search query string.
        max_results: Maximum number of results to return.

    Returns:
        List of source documents from GitHub search.
    """
    async with httpx.AsyncClient() as client:
        response = await client.get(
            "https://api.github.com/search/repositories",
            params={
                "q": query,
                "sort": "stars",
                "order": "desc",
                "per_page": max_results,
            },
            headers={"Accept": "application/vnd.github.v3+json"},
        )
        response.raise_for_status()
        data = response.json()

    results = []
    for repo in data.get("items", []):
        results.append(
            SourceDocument(
                url=repo["html_url"],
                title=repo.get("full_name", ""),
                source_type="github",
                metadata={
                    "description": repo.get("description", ""),
                    "stars": repo.get("stargazers_count", 0),
                    "language": repo.get("language"),
                    "topics": repo.get("topics", []),
                },
                discovered_at=datetime.utcnow(),
            )
        )

    return results


async def fetch_page_text(
    url: str,
    max_chars: int = 5000,
) -> SourceDocument:
    """Fetch a web page, PDF, or local file and extract its text content.

    Args:
        url: URL, `file://` reference, or local path to fetch.
        max_chars: Maximum characters of text to retain.

    Returns:
        Source document with raw_text populated.
    """
    fetched_at = datetime.utcnow()
    source_path = _source_path_from_ref(url)

    if source_path is not None:
        raw_bytes = source_path.read_bytes()
        content_type = "application/pdf" if source_path.suffix.lower() == ".pdf" else None
        is_pdf = source_path.suffix.lower() == ".pdf"
        if is_pdf:
            text, title, extra_metadata = _extract_pdf_text(raw_bytes, max_chars)
        elif source_path.suffix.lower() in {".html", ".htm"}:
            text, title = _extract_html_text(
                raw_bytes.decode("utf-8", errors="ignore"),
                max_chars,
            )
            extra_metadata = {}
        else:
            text = _extract_plain_text(raw_bytes, max_chars)
            title = source_path.name
            extra_metadata = {}
        content_hash = hashlib.sha256(raw_bytes).hexdigest()
        source_url = source_path.resolve().as_uri()
        title = title or source_path.name
    else:
        async with httpx.AsyncClient(follow_redirects=True) as client:
            response = await client.get(url, timeout=30.0)
            response.raise_for_status()
            content_type = response.headers.get("content-type", "").lower()
            is_pdf = "application/pdf" in content_type or urlparse(url).path.lower().endswith(
                ".pdf"
            )

        if is_pdf:
            text, title, extra_metadata = _extract_pdf_text(response.content, max_chars)
        else:
            text, title = _extract_html_text(response.text, max_chars)
            extra_metadata = {}

        content_hash = hashlib.sha256(response.content).hexdigest()
        source_url = url

    return SourceDocument(
        url=source_url,
        title=title or _infer_title_from_url(source_url),
        source_type="vendor_docs",
        raw_text=text,
        content_hash=content_hash,
        metadata={
            "content_type": content_type or None,
            "fetched_from_pdf": is_pdf,
            "local_file": source_path is not None,
            **extra_metadata,
        },
        fetched_at=fetched_at,
    )


def get_search_keywords(
    seeds_path: str | None = None,
) -> list[str]:
    """Load search keywords from seeds/sources.yaml.

    Args:
        seeds_path: Path to sources.yaml.

    Returns:
        List of keyword strings for arXiv/GitHub search.
    """
    if seeds_path is None:
        seeds_path = str(
            Path(__file__).parent.parent.parent.parent.parent / "seeds" / "sources.yaml"
        )

    path = Path(seeds_path)
    if not path.exists():
        return []

    data = yaml.safe_load(path.read_text())
    return data.get("search_keywords", [])
