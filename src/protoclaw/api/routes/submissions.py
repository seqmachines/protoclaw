import uuid
from pathlib import Path
from tempfile import NamedTemporaryFile

from fastapi import APIRouter, File, Form, HTTPException, Query, UploadFile
from pydantic import BaseModel, Field

from protoclaw.db import repositories as repo
from protoclaw.db.engine import async_session
from protoclaw.services.ingestion import (
    create_submission_and_ingest,
    ingest_submission,
    serialize_submission,
)

router = APIRouter()


class SubmissionCreateRequest(BaseModel):
    source_url: str = Field(min_length=1)
    notes: str | None = None
    submitted_by: str = "api"
    force: bool = False


@router.post("")
async def create_submission(payload: SubmissionCreateRequest) -> dict:
    return await create_submission_and_ingest(
        payload.source_url,
        notes=payload.notes,
        submitted_by=payload.submitted_by,
        force_duplicate_review=payload.force,
    )


@router.post("/upload")
async def upload_submission(
    file: UploadFile = File(...),
    notes: str | None = Form(None),
    submitted_by: str = Form("api-upload"),
    force: bool = Form(False),
) -> dict:
    suffix = Path(file.filename or "upload.bin").suffix
    temp_path: Path | None = None
    try:
        with NamedTemporaryFile(delete=False, suffix=suffix, prefix="protoclaw-") as temp:
            temp.write(await file.read())
            temp_path = Path(temp.name)

        return await create_submission_and_ingest(
            temp_path.resolve().as_uri(),
            notes=notes or f"Uploaded file: {file.filename}",
            submitted_by=submitted_by,
            force_duplicate_review=force,
        )
    finally:
        await file.close()
        if temp_path is not None and temp_path.exists():
            temp_path.unlink(missing_ok=True)


@router.get("")
async def list_submissions(
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
) -> list[dict]:
    async with async_session() as session:
        rows = await repo.list_submissions(session, limit=limit, offset=offset)
        return [serialize_submission(row) for row in rows]


@router.get("/{submission_id}")
async def get_submission(submission_id: uuid.UUID) -> dict:
    async with async_session() as session:
        row = await repo.get_submission_by_id(session, submission_id)
        if row is None:
            raise HTTPException(status_code=404, detail="Submission not found")
        return serialize_submission(row)


@router.post("/{submission_id}/run")
async def run_submission(submission_id: uuid.UUID) -> dict:
    async with async_session() as session:
        row = await repo.get_submission_by_id(session, submission_id)
        if row is None:
            raise HTTPException(status_code=404, detail="Submission not found")
    return await ingest_submission(submission_id)
