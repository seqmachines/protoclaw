from pathlib import Path
from types import SimpleNamespace

from click.testing import CliRunner

from protoclaw import cli


def test_submit_warns_on_duplicate_without_force(monkeypatch):
    runner = CliRunner()

    async def fake_ensure_schema() -> None:
        return None

    async def fake_build_protocol_draft(*, source_ref=None, source_text=None, toolkit=None):
        return {"protocol": {"slug": "10x-gem-x-3prime-v4-csp-v4"}}

    async def fake_get_protocol_by_slug(session, slug):
        return SimpleNamespace(id="existing")

    async def fake_create_submission_and_ingest(*args, **kwargs):
        raise AssertionError("duplicate submission should not ingest without --force")

    class _SessionContext:
        async def __aenter__(self):
            return object()

        async def __aexit__(self, exc_type, exc, tb):
            return None

    monkeypatch.setattr(cli, "_ensure_schema", fake_ensure_schema)
    monkeypatch.setattr(
        "protoclaw.services.ingestion.build_protocol_draft",
        fake_build_protocol_draft,
    )
    monkeypatch.setattr(
        "protoclaw.services.ingestion.create_submission_and_ingest",
        fake_create_submission_and_ingest,
    )
    monkeypatch.setattr(
        "protoclaw.db.repositories.get_protocol_by_slug",
        fake_get_protocol_by_slug,
    )
    monkeypatch.setattr("protoclaw.db.engine.async_session", lambda: _SessionContext())

    result = runner.invoke(cli.cli, ["submit", "--url", "https://example.com/protocol.pdf"])

    assert result.exit_code == 0
    assert "Duplicate protocol detected" in result.output
    assert "--force" in result.output


def test_submit_force_creates_comparison_review(monkeypatch):
    runner = CliRunner()

    async def fake_ensure_schema() -> None:
        return None

    async def fake_build_protocol_draft(*, source_ref=None, source_text=None, toolkit=None):
        return {"protocol": {"slug": "10x-gem-x-3prime-v4-csp-v4"}}

    async def fake_get_protocol_by_slug(session, slug):
        return SimpleNamespace(id="existing")

    async def fake_create_submission_and_ingest(
        source_url: str,
        *,
        notes: str | None = None,
        submitted_by: str = "api",
        toolkit=None,
        draft_payload: dict | None = None,
        force_duplicate_review: bool = False,
    ):
        return {
            "id": "sub-123",
            "source_url": source_url,
            "submitted_by": submitted_by,
            "status": "completed",
            "review_request_id": "review-123",
            "protocol_slug": draft_payload["protocol"]["slug"],
            "force_duplicate_review": force_duplicate_review,
        }

    class _SessionContext:
        async def __aenter__(self):
            return object()

        async def __aexit__(self, exc_type, exc, tb):
            return None

    monkeypatch.setattr(cli, "_ensure_schema", fake_ensure_schema)
    monkeypatch.setattr(
        "protoclaw.services.ingestion.build_protocol_draft",
        fake_build_protocol_draft,
    )
    monkeypatch.setattr(
        "protoclaw.services.ingestion.create_submission_and_ingest",
        fake_create_submission_and_ingest,
    )
    monkeypatch.setattr(
        "protoclaw.db.repositories.get_protocol_by_slug",
        fake_get_protocol_by_slug,
    )
    monkeypatch.setattr("protoclaw.db.engine.async_session", lambda: _SessionContext())

    result = runner.invoke(
        cli.cli,
        [
            "submit",
            "--url",
            "https://example.com/protocol.pdf",
            "--force",
        ],
    )

    assert result.exit_code == 0
    assert "review_request_id: review-123" in result.output
    assert "force_duplicate_review: true" in result.output
