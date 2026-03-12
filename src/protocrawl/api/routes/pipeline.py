from pathlib import Path
from tempfile import NamedTemporaryFile

from fastapi import APIRouter, File, Form, HTTPException, Query, UploadFile
from pydantic import BaseModel, Field

from protocrawl.agents.source_scout.tools import load_seed_sources
from protocrawl.services.ingestion import build_protocol_draft, create_submission_and_ingest

router = APIRouter()


class DraftRequest(BaseModel):
    source_url: str | None = Field(default=None, min_length=1)
    source_text: str | None = Field(default=None, min_length=1)


@router.post("/run")
async def run_pipeline(
    dry_run: bool = Query(False),
    limit: int = Query(10, ge=1, le=100),
    seeds_path: str = Query("seeds/sources.yaml"),
    submitted_by: str = Query("scheduler"),
) -> dict:
    sources = await load_seed_sources(seeds_path)
    selected = sources[:limit]

    if dry_run:
        return {
            "count": len(selected),
            "sources": [source.url for source in selected],
        }

    results = []
    for source in selected:
        results.append(
            await create_submission_and_ingest(
                source.url,
                notes=f"Seed source from {seeds_path}",
                submitted_by=submitted_by,
            )
        )

    return {
        "count": len(results),
        "submissions": results,
    }


@router.post("/draft")
async def draft_protocol(payload: DraftRequest) -> dict:
    if bool(payload.source_url) == bool(payload.source_text):
        raise HTTPException(
            status_code=400,
            detail="Provide exactly one of source_url or source_text.",
        )
    if payload.source_text:
        return await build_protocol_draft(source_text=payload.source_text)
    return await build_protocol_draft(source_ref=payload.source_url)


@router.post("/draft/upload")
async def draft_protocol_upload(
    file: UploadFile = File(...),
    notes: str | None = Form(None),
) -> dict:
    suffix = Path(file.filename or "upload.bin").suffix
    temp_path: Path | None = None
    try:
        with NamedTemporaryFile(delete=False, suffix=suffix, prefix="protocrawl-draft-") as temp:
            temp.write(await file.read())
            temp_path = Path(temp.name)

        result = await build_protocol_draft(source_ref=temp_path.resolve().as_uri())
        if notes:
            result["notes"] = notes
        return result
    finally:
        await file.close()
        if temp_path is not None and temp_path.exists():
            temp_path.unlink(missing_ok=True)
