import hashlib
import hmac
import time
import uuid

import pytest

from protocrawl.models import (
    AssayFamily,
    MoleculeType,
    Protocol,
    ReadGeometry,
    ReadType,
)
from protocrawl.services import slack as slack_service


def _sample_protocol() -> Protocol:
    return Protocol(
        slug="smart-seq2",
        name="Smart-seq2",
        version="v1",
        assay_family=AssayFamily.SCRNA_SEQ,
        molecule_type=MoleculeType.RNA,
        description="Full-length single-cell RNA-seq.",
        read_geometry=ReadGeometry(read_type=ReadType.PAIRED_END, read1_length=75),
        confidence_score=0.91,
    )


def _signature(secret: str, timestamp: str, body: bytes) -> str:
    basestring = f"v0:{timestamp}:{body.decode()}".encode()
    digest = hmac.new(secret.encode(), basestring, hashlib.sha256).hexdigest()
    return f"v0={digest}"


def test_verify_slack_request_accepts_valid_signature():
    secret = "signing-secret"
    timestamp = str(int(time.time()))
    body = b"command=%2Fprotocrawl&text=reviews"
    signature = _signature(secret, timestamp, body)

    assert slack_service.verify_slack_request(
        secret,
        timestamp=timestamp,
        body=body,
        signature=signature,
    )


def test_verify_slack_request_rejects_invalid_signature():
    assert not slack_service.verify_slack_request(
        "secret",
        timestamp=str(int(time.time())),
        body=b"text=reviews",
        signature="v0=bad",
    )


@pytest.mark.asyncio
async def test_handle_slack_protocol_command(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(slack_service, "_find_protocol", lambda query: _async_return(object()))
    monkeypatch.setattr(slack_service, "row_to_protocol", lambda row: _sample_protocol())

    response = await slack_service.handle_slack_command("protocol smart-seq2")

    assert "Smart-seq2" in response


@pytest.mark.asyncio
async def test_handle_slack_reviews_command(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(
        slack_service,
        "_list_pending_reviews",
        lambda: _async_return(["123 | Smart-seq2 | score=0.62"]),
    )

    response = await slack_service.handle_slack_command("reviews")

    assert "Pending reviews" in response
    assert "Smart-seq2" in response


@pytest.mark.asyncio
async def test_handle_slack_review_update_command(monkeypatch: pytest.MonkeyPatch):
    review_id = uuid.uuid4()
    monkeypatch.setattr(
        slack_service,
        "_update_review",
        lambda incoming_review_id, decision: _async_return(
            incoming_review_id == review_id and decision == "approved"
        ),
    )

    response = await slack_service.handle_slack_command(f"review {review_id} approve")

    assert f"Review {review_id} marked approved." == response


async def _async_return(value):
    return value
