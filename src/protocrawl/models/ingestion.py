from datetime import datetime
from uuid import UUID, uuid4

from pydantic import BaseModel, Field

from protocrawl.models.enums import IngestionStatus


class ProtocolSubmission(BaseModel):
    """A user or agent submitted source URL for protocol extraction."""

    id: UUID = Field(default_factory=uuid4)
    source_url: str
    notes: str | None = None
    submitted_by: str = "system"
    status: IngestionStatus = IngestionStatus.QUEUED
    source_document_id: UUID | None = None
    protocol_id: UUID | None = None
    review_request_id: UUID | None = None
    error_message: str | None = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class IngestionRun(BaseModel):
    """A concrete pipeline execution for a protocol submission."""

    id: UUID = Field(default_factory=uuid4)
    submission_id: UUID
    status: IngestionStatus = IngestionStatus.QUEUED
    stage: str = "queued"
    results: dict = Field(default_factory=dict)
    errors: list[str] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    completed_at: datetime | None = None
