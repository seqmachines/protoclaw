"""Publisher agent tools for writing protocols to DB and managing reviews."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel

from protocrawl.config import settings
from protocrawl.models.enums import ConfidenceLevel, ReviewStatus
from protocrawl.models.protocol import Protocol
from protocrawl.models.review import ReviewRequest


class PublishResult(BaseModel):
    """Serializable result of a publish operation for a single protocol."""

    slug: str
    action: str
    confidence_level: str
    confidence_score: float
    review_request_id: str | None = None
    message: str


async def publish_protocol(
    protocol_json: str,
    *,
    allow_duplicate_review: bool = False,
) -> dict:
    """Publish or queue a protocol based on its confidence score.

    HIGH confidence: writes directly to DB with approved status.
    MEDIUM/LOW: creates a review request instead.

    Args:
        protocol_json: JSON string of a normalized Protocol.

    Returns:
        Dict describing what action was taken.
    """
    protocol = Protocol.model_validate_json(protocol_json)

    from protocrawl.db.engine import async_session
    from protocrawl.db.repositories import (
        create_protocol,
        create_review_request,
        get_protocol_by_slug,
    )

    level = protocol.confidence_level

    async with async_session() as session:
        # Check if protocol already exists
        existing = await get_protocol_by_slug(session, protocol.slug)
        if existing:
            if allow_duplicate_review:
                review = ReviewRequest(
                    protocol_id=existing.id,
                    confidence_score=protocol.confidence_score,
                    extraction_notes=(
                        f"Duplicate submission for existing protocol '{protocol.slug}'. "
                        "Review the extracted draft against the current protocol before applying changes."
                    ),
                )
                await create_review_request(session, review)
                await session.commit()
                return {
                    "slug": protocol.slug,
                    "action": "duplicate_review_requested",
                    "confidence_level": level,
                    "confidence_score": protocol.confidence_score,
                    "review_request_id": str(review.id),
                    "message": (
                        f"Duplicate review requested for '{protocol.slug}' "
                        f"(confidence: {protocol.confidence_score:.2f})"
                    ),
                }
            return {
                "slug": protocol.slug,
                "action": "skipped",
                "confidence_level": level,
                "confidence_score": protocol.confidence_score,
                "message": f"Protocol '{protocol.slug}' already exists",
            }

        if level == ConfidenceLevel.HIGH:
            # Auto-publish
            protocol.review_status = ReviewStatus.APPROVED
            protocol.published_at = datetime.utcnow()
            await create_protocol(session, protocol)
            await session.commit()

            return {
                "slug": protocol.slug,
                "action": "published",
                "confidence_level": level,
                "confidence_score": protocol.confidence_score,
                "message": (
                    f"Published '{protocol.slug}' "
                    f"(confidence: {protocol.confidence_score:.2f})"
                ),
            }
        else:
            # Create review request
            protocol.review_status = ReviewStatus.PENDING
            await create_protocol(session, protocol)

            review = ReviewRequest(
                protocol_id=protocol.id,
                confidence_score=protocol.confidence_score,
                extraction_notes=protocol.extraction_notes,
            )
            await create_review_request(session, review)
            await session.commit()

            return {
                "slug": protocol.slug,
                "action": "review_requested",
                "confidence_level": level,
                "confidence_score": protocol.confidence_score,
                "review_request_id": str(review.id),
                "message": (
                    f"Review requested for '{protocol.slug}' "
                    f"(confidence: {protocol.confidence_score:.2f}, "
                    f"level: {level})"
                ),
            }


async def upload_artifact(
    slug: str,
    content: str,
    filename: str,
) -> str:
    """Upload a raw artifact to Google Cloud Storage.

    Args:
        slug: Protocol slug (used as GCS path prefix).
        content: File content to upload.
        filename: Filename within the slug directory.

    Returns:
        GCS URI of the uploaded object.
    """
    from google.cloud import storage

    client = storage.Client(project=settings.gcp_project)
    bucket = client.bucket(settings.gcs_bucket)
    blob_path = f"protocols/{slug}/{filename}"
    blob = bucket.blob(blob_path)
    blob.upload_from_string(content)

    return f"gs://{settings.gcs_bucket}/{blob_path}"
