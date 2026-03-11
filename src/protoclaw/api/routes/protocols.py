from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import PlainTextResponse
from sqlalchemy.ext.asyncio import AsyncSession

from protoclaw.agents.formatter.tools import generate_seqspec_yaml
from protoclaw.api.dependencies import get_db
from protoclaw.db import repositories as repo
from protoclaw.services.protocols import (
    protocol_to_seqspec,
    protocol_to_explorer,
    protocol_tsv_summary,
    row_to_protocol,
)

router = APIRouter()

@router.get("")
async def list_protocols(
    assay_family: str | None = Query(None),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
) -> list[dict]:
    rows = await repo.list_protocols(
        db, assay_family=assay_family, limit=limit, offset=offset
    )
    return [
        row_to_protocol(r).model_dump(
            mode="json",
            include={
                "id",
                "slug",
                "name",
                "version",
                "assay_family",
                "molecule_type",
                "vendor",
                "description",
                "confidence_score",
                "review_status",
            },
        )
        for r in rows
    ]


@router.get("/{slug}")
async def get_protocol(
    slug: str,
    db: AsyncSession = Depends(get_db),
) -> dict:
    row = await repo.get_protocol_by_slug(db, slug)
    if not row:
        raise HTTPException(status_code=404, detail="Protocol not found")
    return row_to_protocol(row).model_dump(mode="json")


@router.get("/{slug}/read-geometry")
async def get_read_geometry(
    slug: str,
    db: AsyncSession = Depends(get_db),
) -> dict:
    row = await repo.get_protocol_by_slug(db, slug)
    if not row:
        raise HTTPException(status_code=404, detail="Protocol not found")
    protocol = row_to_protocol(row)
    return protocol.read_geometry.model_dump(mode="json")


@router.get("/{slug}/explorer")
async def get_protocol_explorer(
    slug: str,
    db: AsyncSession = Depends(get_db),
) -> dict:
    row = await repo.get_protocol_by_slug(db, slug)
    if not row:
        raise HTTPException(status_code=404, detail="Protocol not found")
    protocol = row_to_protocol(row)
    return protocol_to_explorer(protocol).model_dump(mode="json")


@router.get("/{slug}/seqspec")
async def get_seqspec(
    slug: str,
    format: str = Query("json", pattern="^(json|yaml)$"),
    db: AsyncSession = Depends(get_db),
):
    row = await repo.get_protocol_by_slug(db, slug)
    if not row:
        raise HTTPException(status_code=404, detail="Protocol not found")

    protocol = row_to_protocol(row)
    seqspec_row = await repo.get_protocol_seqspec(db, row.id)
    if seqspec_row:
        if format == "yaml":
            return PlainTextResponse(seqspec_row.content_yaml, media_type="application/x-yaml")
        return seqspec_row.content_json

    seqspec = protocol_to_seqspec(protocol)
    if format == "yaml":
        return PlainTextResponse(generate_seqspec_yaml(seqspec), media_type="application/x-yaml")
    return seqspec.model_dump(mode="json")


@router.get("/{slug}/exports/parser-config")
async def get_parser_config(
    slug: str,
    db: AsyncSession = Depends(get_db),
) -> dict:
    row = await repo.get_protocol_by_slug(db, slug)
    if not row:
        raise HTTPException(status_code=404, detail="Protocol not found")
    protocol = row_to_protocol(row)
    return protocol.parser_config or {
        "generator": "protoclaw.agents.parser.tools.extract_seqspec",
        "normalizer": "protoclaw.agents.normalizer.tools.seqspec_to_protocol",
        "schema": "SeqSpec",
        "notes": "No protocol-specific parser config stored.",
    }


@router.get("/{slug}/exports/tsv")
async def get_protocol_tsv(
    slug: str,
    db: AsyncSession = Depends(get_db),
):
    row = await repo.get_protocol_by_slug(db, slug)
    if not row:
        raise HTTPException(status_code=404, detail="Protocol not found")
    protocol = row_to_protocol(row)
    return PlainTextResponse(protocol_tsv_summary(protocol), media_type="text/tab-separated-values")


@router.get("/{slug}/versions")
async def list_versions(
    slug: str,
    db: AsyncSession = Depends(get_db),
) -> list[dict]:
    row = await repo.get_protocol_by_slug(db, slug)
    if not row:
        raise HTTPException(status_code=404, detail="Protocol not found")
    versions = await repo.list_protocol_versions(db, row.id)
    return [
        {
            "version_number": v.version_number,
            "change_summary": v.change_summary,
            "created_at": v.created_at.isoformat(),
            "created_by": v.created_by,
        }
        for v in versions
    ]
