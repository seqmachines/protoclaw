from datetime import datetime
from uuid import UUID, uuid4

from pydantic import BaseModel, Field


class SourceDocument(BaseModel):
    """A raw document discovered by Source Scout."""

    id: UUID = Field(default_factory=uuid4)
    url: str
    title: str | None = None
    source_type: str  # "paper", "github", "vendor_docs", "lab_page", "preprint"
    content_hash: str | None = None  # SHA-256 of fetched content for dedup
    raw_text: str | None = None
    metadata: dict = Field(default_factory=dict)  # Flexible extra fields
    discovered_at: datetime = Field(default_factory=datetime.utcnow)
    fetched_at: datetime | None = None
