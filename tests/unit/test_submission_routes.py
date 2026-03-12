from fastapi import FastAPI
from fastapi.testclient import TestClient

from protocrawl.api.routes import submissions


def test_upload_submission_route(monkeypatch):
    app = FastAPI()
    app.include_router(submissions.router, prefix="/submissions")

    async def fake_create_submission_and_ingest(
        source_url: str,
        *,
        notes: str | None = None,
        submitted_by: str = "api",
        toolkit=None,
        force_duplicate_review: bool = False,
        draft_payload: dict | None = None,
    ) -> dict:
        return {
            "id": "sub-123",
            "source_url": source_url,
            "notes": notes,
            "submitted_by": submitted_by,
            "status": "completed",
        }

    monkeypatch.setattr(
        submissions,
        "create_submission_and_ingest",
        fake_create_submission_and_ingest,
    )

    client = TestClient(app)
    response = client.post(
        "/submissions/upload",
        files={"file": ("protocol.pdf", b"%PDF-1.4 test bytes", "application/pdf")},
        data={"notes": "uploaded pdf", "submitted_by": "test-user"},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["id"] == "sub-123"
    assert payload["source_url"].startswith("file://")
    assert payload["notes"] == "uploaded pdf"
    assert payload["submitted_by"] == "test-user"
