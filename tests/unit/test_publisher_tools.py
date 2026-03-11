"""Tests for publisher tools — confidence-gated publishing logic."""

from protoclaw.agents.publisher.tools import PublishResult
from protoclaw.models import (
    AssayFamily,
    MoleculeType,
    Protocol,
    ReadGeometry,
    ReadType,
)
from protoclaw.models.enums import ConfidenceLevel


def _protocol_with_confidence(score: float) -> Protocol:
    return Protocol(
        slug=f"test-protocol-{int(score * 100)}",
        name="Test Protocol",
        version="v1",
        assay_family=AssayFamily.SCRNA_SEQ,
        molecule_type=MoleculeType.RNA,
        description="Test protocol for publisher tests.",
        read_geometry=ReadGeometry(read_type=ReadType.PAIRED_END),
        confidence_score=score,
    )


class TestConfidenceGating:
    def test_high_confidence_should_publish(self):
        p = _protocol_with_confidence(0.92)
        assert p.confidence_level == ConfidenceLevel.HIGH

    def test_medium_confidence_should_review(self):
        p = _protocol_with_confidence(0.70)
        assert p.confidence_level == ConfidenceLevel.MEDIUM

    def test_low_confidence_should_review(self):
        p = _protocol_with_confidence(0.40)
        assert p.confidence_level == ConfidenceLevel.LOW

    def test_boundary_high(self):
        p = _protocol_with_confidence(0.85)
        assert p.confidence_level == ConfidenceLevel.HIGH

    def test_boundary_medium(self):
        p = _protocol_with_confidence(0.60)
        assert p.confidence_level == ConfidenceLevel.MEDIUM

    def test_boundary_low(self):
        p = _protocol_with_confidence(0.59)
        assert p.confidence_level == ConfidenceLevel.LOW


class TestPublishResult:
    def test_published_result(self):
        r = PublishResult(
            slug="test",
            action="published",
            confidence_level="high",
            confidence_score=0.92,
            message="Published 'test'",
        )
        assert r.action == "published"
        assert r.review_request_id is None

    def test_review_requested_result(self):
        r = PublishResult(
            slug="test",
            action="review_requested",
            confidence_level="medium",
            confidence_score=0.70,
            review_request_id="abc-123",
            message="Review requested",
        )
        assert r.action == "review_requested"
        assert r.review_request_id == "abc-123"

    def test_duplicate_review_requested_result(self):
        r = PublishResult(
            slug="test",
            action="duplicate_review_requested",
            confidence_level="high",
            confidence_score=1.0,
            review_request_id="dup-123",
            message="Duplicate review requested",
        )
        assert r.action == "duplicate_review_requested"
        assert r.review_request_id == "dup-123"
