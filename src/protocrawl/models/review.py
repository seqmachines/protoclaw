from datetime import datetime
from uuid import UUID, uuid4

from pydantic import BaseModel, Field

from protocrawl.models.enums import ReviewStatus


class ReviewRequest(BaseModel):
    """A pending human review for a protocol record."""

    id: UUID = Field(default_factory=uuid4)
    protocol_id: UUID
    confidence_score: float
    extraction_notes: str | None = None
    status: ReviewStatus = ReviewStatus.PENDING
    assigned_to: str | None = None  # Reviewer email
    created_at: datetime = Field(default_factory=datetime.utcnow)


class ReviewDecision(BaseModel):
    """A reviewer's action on a review request."""

    id: UUID = Field(default_factory=uuid4)
    review_request_id: UUID
    reviewer: str
    decision: ReviewStatus
    comments: str | None = None
    edits: dict | None = None  # JSON patch of fields the reviewer changed
    decided_at: datetime = Field(default_factory=datetime.utcnow)
