"""Review UI routes — server-rendered Jinja2 templates."""

import uuid
from json import dumps
from pathlib import Path

from fastapi import APIRouter, Depends, Form, HTTPException, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from protocrawl.agents.formatter.tools import render_read_diagram
from protocrawl.api.dependencies import get_db
from protocrawl.db import repositories as repo
from protocrawl.models import Protocol, ReviewStatus
from protocrawl.services.protocols import row_to_protocol

router = APIRouter()

_TEMPLATE_DIR = Path(__file__).parent.parent / "templates"
templates = Jinja2Templates(directory=str(_TEMPLATE_DIR))


class ReviewDecisionRequest(BaseModel):
    decision: ReviewStatus
    comments: str | None = None


def _build_diff(current: dict, draft: dict) -> list[dict]:
    diffs: list[dict] = []
    keys = sorted(set(current) | set(draft))
    ignored = {"id", "created_at", "updated_at", "published_at"}
    for key in keys:
        if key in ignored:
            continue
        left = current.get(key)
        right = draft.get(key)
        if left == right:
            continue
        diffs.append(
            {
                "field": key,
                "current": left,
                "draft": right,
                "current_text": dumps(left, sort_keys=True, default=str) if isinstance(left, (dict, list)) else left,
                "draft_text": dumps(right, sort_keys=True, default=str) if isinstance(right, (dict, list)) else right,
            }
        )
    return diffs


@router.get("/api")
async def list_reviews_api(
    db: AsyncSession = Depends(get_db),
) -> list[dict]:
    reviews = await repo.list_pending_reviews(db)
    payload = []
    for review in reviews:
        submission = await repo.get_latest_submission_for_review(db, review.id)
        latest_run = (
            await repo.get_latest_run_for_submission(db, submission.id)
            if submission is not None
            else None
        )
        publish_result = (latest_run.results or {}).get("publish_result", {}) if latest_run else {}
        payload.append(
            {
                "id": str(review.id),
                "protocol_id": str(review.protocol_id),
                "protocol_slug": review.protocol.slug if review.protocol else None,
                "protocol_name": review.protocol.name if review.protocol else None,
                "confidence_score": review.confidence_score,
                "status": review.status,
                "created_at": review.created_at.isoformat(),
                "extraction_notes": review.extraction_notes,
                "submission_id": str(submission.id) if submission else None,
                "source_url": submission.source_url if submission else None,
                "duplicate_submission": publish_result.get("action") == "duplicate_review_requested",
            }
        )
    return payload


@router.get("/{review_id}/comparison")
async def review_comparison(
    review_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
) -> dict:
    review = await repo.get_review_by_id(db, review_id)
    if not review:
        raise HTTPException(status_code=404, detail="Review not found")

    protocol_row = await repo.get_protocol_by_id(db, review.protocol_id)
    if not protocol_row:
        raise HTTPException(status_code=404, detail="Protocol not found")

    current_protocol = row_to_protocol(protocol_row)
    submission = await repo.get_latest_submission_for_review(db, review.id)
    latest_run = (
        await repo.get_latest_run_for_submission(db, submission.id)
        if submission is not None
        else None
    )
    normalized = (latest_run.results or {}).get("normalized") if latest_run else None
    draft_protocol = (
        Protocol.model_validate(normalized)
        if normalized
        else current_protocol
    )
    publish_result = (latest_run.results or {}).get("publish_result", {}) if latest_run else {}
    return {
        "review": {
            "id": str(review.id),
            "status": review.status,
            "confidence_score": review.confidence_score,
            "created_at": review.created_at.isoformat(),
            "extraction_notes": review.extraction_notes,
            "duplicate_submission": publish_result.get("action") == "duplicate_review_requested",
            "submission_id": str(submission.id) if submission else None,
            "source_url": submission.source_url if submission else None,
        },
        "current_protocol": current_protocol.model_dump(mode="json"),
        "draft_protocol": draft_protocol.model_dump(mode="json"),
        "diffs": _build_diff(
            current_protocol.model_dump(mode="json"),
            draft_protocol.model_dump(mode="json"),
        ),
    }


@router.post("/{review_id}/decision")
async def decide_review_api(
    review_id: uuid.UUID,
    payload: ReviewDecisionRequest,
    db: AsyncSession = Depends(get_db),
) -> dict:
    review = await repo.update_review_status(
        db,
        review_id,
        payload.decision.value,
        protocol_published=payload.decision == ReviewStatus.APPROVED,
        comments=payload.comments,
        reviewer="frontend",
    )
    if review is None:
        raise HTTPException(status_code=404, detail="Review not found")
    await db.commit()
    return {"id": str(review.id), "status": review.status}


@router.get("", response_class=HTMLResponse)
async def list_reviews(
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> HTMLResponse:
    """List all pending review requests."""
    reviews = await repo.list_pending_reviews(db)
    return templates.TemplateResponse(
        "reviews_list.html",
        {"request": request, "reviews": reviews},
    )


@router.get("/{review_id}", response_class=HTMLResponse)
async def review_detail(
    request: Request,
    review_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
) -> HTMLResponse:
    """Show detail view for a single review request."""
    review = await repo.get_review_by_id(db, review_id)
    if not review:
        return HTMLResponse("Review not found", status_code=404)

    protocol_row = await repo.get_protocol_by_id(db, review.protocol_id)
    if not protocol_row:
        return HTMLResponse("Protocol not found", status_code=404)

    protocol = row_to_protocol(protocol_row)
    diagram = render_read_diagram(protocol)

    return templates.TemplateResponse(
        "review_detail.html",
        {
            "request": request,
            "review": review,
            "protocol": protocol,
            "read_diagram": diagram,
        },
    )


@router.post("/{review_id}/decide")
async def decide_review(
    review_id: uuid.UUID,
    decision: str = Form(...),
    comments: str = Form(""),
    db: AsyncSession = Depends(get_db),
) -> RedirectResponse:
    """Process a reviewer's decision (approve or reject)."""
    publish = decision == "approved"
    await repo.update_review_status(
        db,
        review_id,
        decision,
        protocol_published=publish,
        comments=comments,
        reviewer="jinja-review",
    )
    await db.commit()
    return RedirectResponse(url="/reviews", status_code=303)
