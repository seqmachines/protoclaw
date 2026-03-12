import uuid
from types import SimpleNamespace

from fastapi import FastAPI
from fastapi.testclient import TestClient

from protocrawl.api.dependencies import get_db
from protocrawl.api.routes import reviews
from protocrawl.models import (
    AssayFamily,
    MoleculeType,
    Protocol,
    ReadGeometry,
    ReadType,
    ReviewStatus,
)


def _protocol(**overrides) -> Protocol:
    base = Protocol(
        slug="10x-gem-x-3prime-v4-csp-v4",
        name="Chromium GEM-X",
        version="v4",
        assay_family=AssayFamily.CITE_SEQ,
        molecule_type=MoleculeType.RNA,
        description="Protocol",
        read_geometry=ReadGeometry(read_type=ReadType.PAIRED_END),
        confidence_score=1.0,
        review_status=ReviewStatus.APPROVED,
    )
    return base.model_copy(update=overrides)


async def _fake_get_db():
    class _FakeDb:
        async def commit(self) -> None:
            return None

    yield _FakeDb()


def test_review_api_routes(monkeypatch):
    app = FastAPI()
    app.include_router(reviews.router, prefix="/reviews")
    app.dependency_overrides[get_db] = _fake_get_db

    review_row = SimpleNamespace(
        id=uuid.UUID("11111111-1111-1111-1111-111111111111"),
        protocol_id=uuid.UUID("22222222-2222-2222-2222-222222222222"),
        confidence_score=1.0,
        status="pending",
        created_at=SimpleNamespace(isoformat=lambda: "2026-03-09T10:00:00"),
        extraction_notes="Duplicate submission",
        protocol=SimpleNamespace(slug="10x-gem-x-3prime-v4-csp-v4", name="Chromium GEM-X"),
    )
    submission_row = SimpleNamespace(id=uuid.UUID("33333333-3333-3333-3333-333333333333"), source_url="https://example.com/protocol.pdf")
    run_row = SimpleNamespace(
        results={
            "publish_result": {"action": "duplicate_review_requested"},
            "normalized": _protocol(description="Updated protocol").model_dump(mode="json"),
        }
    )

    async def fake_list_pending_reviews(db):
        return [review_row]

    async def fake_get_review_by_id(db, review_id):
        return review_row

    async def fake_get_protocol_by_id(db, protocol_id):
        return SimpleNamespace()

    async def fake_get_latest_submission_for_review(db, review_id):
        return submission_row

    async def fake_get_latest_run_for_submission(db, submission_id):
        return run_row

    async def fake_update_review_status(db, review_id, status, **kwargs):
        return SimpleNamespace(id=review_id, status=status)

    monkeypatch.setattr(reviews.repo, "list_pending_reviews", fake_list_pending_reviews)
    monkeypatch.setattr(reviews.repo, "get_review_by_id", fake_get_review_by_id)
    monkeypatch.setattr(reviews.repo, "get_protocol_by_id", fake_get_protocol_by_id)
    monkeypatch.setattr(reviews.repo, "get_latest_submission_for_review", fake_get_latest_submission_for_review)
    monkeypatch.setattr(reviews.repo, "get_latest_run_for_submission", fake_get_latest_run_for_submission)
    monkeypatch.setattr(reviews.repo, "update_review_status", fake_update_review_status)
    monkeypatch.setattr(reviews, "row_to_protocol", lambda row: _protocol())

    client = TestClient(app)

    list_response = client.get("/reviews/api")
    assert list_response.status_code == 200
    assert list_response.json()[0]["duplicate_submission"] is True

    comparison_response = client.get("/reviews/11111111-1111-1111-1111-111111111111/comparison")
    assert comparison_response.status_code == 200
    assert comparison_response.json()["diffs"][0]["field"] == "description"

    decision_response = client.post(
        "/reviews/11111111-1111-1111-1111-111111111111/decision",
        json={"decision": "approved"},
    )
    assert decision_response.status_code == 200
    assert decision_response.json()["status"] == "approved"
