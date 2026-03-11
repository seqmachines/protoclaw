from __future__ import annotations

import re
import uuid
from dataclasses import dataclass
from datetime import datetime
from typing import Awaitable, Callable

from protoclaw.agents.formatter.tools import (
    format_protocol,
    generate_seqspec_json,
    generate_seqspec_yaml,
)
from protoclaw.agents.normalizer.tools import seqspec_to_protocol
from protoclaw.agents.parser.tools import (
    extract_seqspec,
)
from protoclaw.agents.publisher.tools import publish_protocol
from protoclaw.agents.source_scout.tools import fetch_page_text
from protoclaw.db.engine import async_session
from protoclaw.db import repositories as repo
from protoclaw.models import (
    FieldEvidence,
    IngestionRun,
    IngestionStatus,
    Protocol,
    ProtocolSubmission,
    SeqSpec,
    SourceDocument,
)


Fetcher = Callable[[str], Awaitable[SourceDocument | dict]]
SeqSpecExtractor = Callable[[str, list[str] | None], Awaitable[SeqSpec]]
Publisher = Callable[..., Awaitable[dict]]

_FORCE_DUPLICATE_REVIEW_MARKER = "[force-duplicate-review]"


@dataclass(slots=True)
class IngestionToolkit:
    fetch_source: Fetcher = fetch_page_text
    extract_seqspec: SeqSpecExtractor = extract_seqspec
    publish_protocol: Publisher = publish_protocol


def _encode_submission_notes(
    notes: str | None, *, force_duplicate_review: bool = False
) -> str | None:
    cleaned = (notes or "").strip()
    if not force_duplicate_review:
        return cleaned or None
    if cleaned:
        return f"{_FORCE_DUPLICATE_REVIEW_MARKER}\n{cleaned}"
    return _FORCE_DUPLICATE_REVIEW_MARKER


def _decode_submission_notes(notes: str | None) -> str | None:
    if not notes:
        return None
    cleaned = notes.replace(_FORCE_DUPLICATE_REVIEW_MARKER, "").strip()
    return cleaned or None


def _submission_force_duplicate_review(notes: str | None) -> bool:
    return bool(notes and _FORCE_DUPLICATE_REVIEW_MARKER in notes)


def serialize_run(run: repo.IngestionRunRow) -> dict:
    return {
        "id": str(run.id),
        "status": run.status,
        "stage": run.stage,
        "results": run.results,
        "errors": run.errors,
        "created_at": run.created_at.isoformat(),
        "completed_at": run.completed_at.isoformat() if run.completed_at else None,
    }


def serialize_submission(submission: repo.ProtocolSubmissionRow) -> dict:
    latest_run = submission.runs[0] if submission.runs else None
    protocol_slug = submission.protocol.slug if submission.protocol else None
    return {
        "id": str(submission.id),
        "source_url": submission.source_url,
        "notes": _decode_submission_notes(submission.notes),
        "submitted_by": submission.submitted_by,
        "status": submission.status,
        "source_document_id": (
            str(submission.source_document_id) if submission.source_document_id else None
        ),
        "protocol_id": str(submission.protocol_id) if submission.protocol_id else None,
        "protocol_slug": protocol_slug,
        "review_request_id": (
            str(submission.review_request_id) if submission.review_request_id else None
        ),
        "error_message": submission.error_message,
        "created_at": submission.created_at.isoformat(),
        "updated_at": submission.updated_at.isoformat(),
        "latest_run": serialize_run(latest_run) if latest_run else None,
    }


async def create_submission(
    source_url: str,
    *,
    notes: str | None = None,
    submitted_by: str = "api",
    force_duplicate_review: bool = False,
) -> dict:
    submission = ProtocolSubmission(
        source_url=source_url,
        notes=_encode_submission_notes(
            notes,
            force_duplicate_review=force_duplicate_review,
        ),
        submitted_by=submitted_by,
    )
    async with async_session() as session:
        await repo.create_protocol_submission(session, submission)
        await session.commit()
        row = await repo.get_submission_by_id(session, submission.id)
        assert row is not None
        return serialize_submission(row)


async def create_submission_and_ingest(
    source_url: str,
    *,
    notes: str | None = None,
    submitted_by: str = "api",
    toolkit: IngestionToolkit | None = None,
    draft_payload: dict | None = None,
    force_duplicate_review: bool = False,
) -> dict:
    submission = await create_submission(
        source_url,
        notes=notes,
        submitted_by=submitted_by,
        force_duplicate_review=force_duplicate_review,
    )
    return await ingest_submission(
        uuid.UUID(submission["id"]),
        toolkit=toolkit,
        draft_payload=draft_payload,
    )


async def build_protocol_draft(
    *,
    source_ref: str | None = None,
    source_text: str | None = None,
    toolkit: IngestionToolkit | None = None,
) -> dict:
    if bool(source_ref) == bool(source_text):
        raise ValueError("Provide exactly one of source_ref or source_text.")

    tools = toolkit or IngestionToolkit()
    if source_text is not None:
        source_doc = SourceDocument(
            url="inline://text",
            title="Inline text",
            source_type="inline_text",
            raw_text=source_text,
            fetched_at=datetime.utcnow(),
        )
    else:
        source_result = await tools.fetch_source(source_ref or "")
        if isinstance(source_result, SourceDocument):
            source_doc = source_result
        else:
            source_result.setdefault("url", source_ref)
            source_result.setdefault("source_type", "vendor_docs")
            source_result.setdefault("fetched_at", datetime.utcnow().isoformat())
            source_doc = SourceDocument.model_validate(source_result)

    raw_text = source_doc.raw_text or ""
    if not raw_text.strip():
        raise ValueError("Source did not yield readable text.")

    source_url = source_doc.url
    seqspec = await tools.extract_seqspec(raw_text, [source_url] if source_url else None)
    normalized = _enrich_normalized_protocol(
        seqspec_to_protocol(seqspec),
        seqspec=seqspec,
        source_text=raw_text,
        source_url=source_url,
    )
    return {
        "source_document": source_doc.model_dump(mode="json"),
        "seqspec": seqspec.model_dump(mode="json"),
        "protocol": normalized.model_dump(mode="json"),
        "formatted": format_protocol(normalized).model_dump(mode="json"),
    }


async def ingest_submission(
    submission_id: uuid.UUID,
    *,
    toolkit: IngestionToolkit | None = None,
    draft_payload: dict | None = None,
) -> dict:
    tools = toolkit or IngestionToolkit()
    run = IngestionRun(submission_id=submission_id)

    async with async_session() as session:
        await repo.create_ingestion_run(session, run)
        await repo.update_submission(
            session,
            submission_id,
            status=IngestionStatus.RUNNING.value,
            error_message=None,
        )
        await repo.update_ingestion_run(
            session,
            run.id,
            status=IngestionStatus.RUNNING.value,
            stage="fetching_source",
            results={},
            errors=[],
        )
        await session.commit()

    stage_results: dict = {}

    try:
        async with async_session() as session:
            submission = await repo.get_submission_by_id(session, submission_id)
            if submission is None:
                raise ValueError(f"Submission {submission_id} not found")
            source_url = submission.source_url
            force_duplicate_review = _submission_force_duplicate_review(
                submission.notes
            )

        if draft_payload is not None:
            source_doc = SourceDocument.model_validate(draft_payload["source_document"])
            seqspec = SeqSpec.model_validate(draft_payload["seqspec"])
            normalized = Protocol.model_validate(draft_payload["protocol"])
            stage_results["source_document"] = source_doc.model_dump(mode="json")
            stage_results["seqspec"] = seqspec.model_dump(mode="json")
            stage_results["seqspec_json"] = generate_seqspec_json(seqspec)
            stage_results["seqspec_yaml"] = generate_seqspec_yaml(seqspec)
            stage_results["normalized"] = normalized.model_dump(mode="json")
            stage_results["formatted"] = draft_payload.get("formatted") or format_protocol(normalized).model_dump(mode="json")
        else:
            source_result = await tools.fetch_source(source_url)
            if isinstance(source_result, SourceDocument):
                source_doc = source_result
            else:
                source_result.setdefault("url", source_url)
                source_result.setdefault("source_type", "vendor_docs")
                source_result.setdefault("fetched_at", datetime.utcnow().isoformat())
                source_doc = SourceDocument.model_validate(source_result)
            stage_results["source_document"] = source_doc.model_dump(mode="json")

        async with async_session() as session:
            stored_source = await repo.create_source_document(session, source_doc)
            await repo.update_submission(
                session,
                submission_id,
                source_document_id=stored_source.id,
            )
            await repo.update_ingestion_run(
                session,
                run.id,
                stage="parsing",
                results=stage_results,
            )
            await session.commit()

        source_text = source_doc.raw_text or ""
        if not source_text.strip():
            raise ValueError(f"Source {source_url} did not yield readable text")

        if draft_payload is None:
            seqspec = await tools.extract_seqspec(source_text, [source_url])
            stage_results["seqspec"] = seqspec.model_dump(mode="json")
            stage_results["seqspec_json"] = generate_seqspec_json(seqspec)
            stage_results["seqspec_yaml"] = generate_seqspec_yaml(seqspec)

            normalized = _enrich_normalized_protocol(
                seqspec_to_protocol(seqspec),
                seqspec=seqspec,
                source_text=source_text,
                source_url=source_url,
            )
            normalized_data = normalized.model_dump(mode="json")
            stage_results["normalized"] = normalized_data
            stage_results["formatted"] = format_protocol(normalized).model_dump(mode="json")
        else:
            normalized = Protocol.model_validate(stage_results["normalized"])
            seqspec = SeqSpec.model_validate(stage_results["seqspec"])

        async with async_session() as session:
            await repo.update_ingestion_run(
                session,
                run.id,
                stage="publishing",
                results=stage_results,
            )
            await session.commit()

        publish_result = await tools.publish_protocol(
            normalized.model_dump_json(),
            allow_duplicate_review=force_duplicate_review,
        )
        stage_results["publish_result"] = publish_result

        async with async_session() as session:
            protocol = await repo.get_protocol_by_slug(session, normalized.slug)
            review_request_id = publish_result.get("review_request_id")
            await repo.update_submission(
                session,
                submission_id,
                status=IngestionStatus.COMPLETED.value,
                protocol_id=protocol.id if protocol else None,
                review_request_id=(
                    uuid.UUID(review_request_id) if review_request_id else None
                ),
                error_message=None,
            )
            if protocol is not None:
                await repo.upsert_protocol_seqspec(
                    session,
                    protocol_id=protocol.id,
                    submission_id=submission_id,
                    content_json=seqspec.model_dump(mode="json"),
                    content_yaml=stage_results["seqspec_yaml"],
                )
            await repo.update_ingestion_run(
                session,
                run.id,
                status=IngestionStatus.COMPLETED.value,
                stage="completed",
                results=stage_results,
                completed_at=datetime.utcnow(),
            )
            await session.commit()
            refreshed = await repo.get_submission_by_id(session, submission_id)
            assert refreshed is not None
            return serialize_submission(refreshed)
    except Exception as exc:
        error_message = str(exc)
        async with async_session() as session:
            await repo.update_submission(
                session,
                submission_id,
                status=IngestionStatus.FAILED.value,
                error_message=error_message,
            )
            await repo.update_ingestion_run(
                session,
                run.id,
                status=IngestionStatus.FAILED.value,
                stage="failed",
                results=stage_results,
                errors=[error_message],
                completed_at=datetime.utcnow(),
            )
            await session.commit()
            refreshed = await repo.get_submission_by_id(session, submission_id)
            if refreshed is None:
                raise
            return serialize_submission(refreshed)


def _enrich_normalized_protocol(protocol, *, seqspec: SeqSpec, source_text: str, source_url: str):
    protocol.chemistry_version = seqspec.version
    protocol.compatible_instruments = [protocol.platform] if protocol.platform else []
    protocol.parser_config = {
        "generator": "protoclaw.agents.parser.tools.extract_seqspec",
        "normalizer": "protoclaw.agents.normalizer.tools.seqspec_to_protocol",
        "schema": "SeqSpec",
        "source_document_url": source_url,
    }
    protocol.field_evidence = _build_field_evidence(
        protocol,
        source_text=source_text,
        source_url=source_url,
    )
    return protocol


def _build_field_evidence(protocol, *, source_text: str, source_url: str) -> list[FieldEvidence]:
    evidence: list[FieldEvidence] = []
    evidence.extend(
        filter(
            None,
            [
                _evidence_for_value(
                    "name",
                    "Assay name",
                    protocol.name,
                    source_text=source_text,
                    source_url=source_url,
                ),
                _evidence_for_value(
                    "version",
                    "Chemistry version",
                    protocol.chemistry_version or protocol.version,
                    source_text=source_text,
                    source_url=source_url,
                ),
                _evidence_for_value(
                    "vendor",
                    "Vendor",
                    protocol.vendor,
                    source_text=source_text,
                    source_url=source_url,
                ),
                _evidence_for_value(
                    "platform",
                    "Platform",
                    protocol.platform,
                    source_text=source_text,
                    source_url=source_url,
                ),
            ],
        )
    )

    for index, segment in enumerate(protocol.read_geometry.segments, start=1):
        label = f"{segment.role.value.replace('_', ' ')} {segment.length or 'variable'} bp"
        segment_id = f"read-seg-{index}"
        match = _find_excerpt(
            source_text,
            [
                f"{segment.length or ''}bp {segment.role.value.replace('_', ' ')}",
                f"{segment.length or ''} bp {segment.role.value.replace('_', ' ')}",
                segment.description or "",
                segment.role.value.replace("_", " "),
            ],
        )
        evidence.append(
            FieldEvidence(
                field_path=f"read_geometry.segments[{index - 1}]",
                label=_title_case(segment.role.value),
                value=label,
                segment_id=segment_id,
                source_url=source_url,
                excerpt=match,
                extraction_mode="extracted" if match else "inferred",
                confidence_score=protocol.confidence_score if match else max(protocol.confidence_score - 0.15, 0.0),
                parser_stage="normalization",
                parser_source="seqspec_to_protocol",
                notes=None if match else "Derived from seqspec region ordering and read layout.",
            )
        )

    return evidence


def _evidence_for_value(
    field_path: str,
    label: str,
    value: str | None,
    *,
    source_text: str,
    source_url: str,
) -> FieldEvidence | None:
    if not value:
        return None
    excerpt = _find_excerpt(source_text, [value])
    return FieldEvidence(
        field_path=field_path,
        label=label,
        value=value,
        source_url=source_url,
        excerpt=excerpt,
        extraction_mode="extracted" if excerpt else "inferred",
        confidence_score=0.95 if excerpt else 0.7,
        parser_stage="parsing",
        parser_source="extract_seqspec",
        notes=None if excerpt else "Value preserved after normalization but not matched verbatim in source text.",
    )


def _find_excerpt(source_text: str, patterns: list[str]) -> str | None:
    for pattern in patterns:
        if not pattern:
            continue
        match = re.search(re.escape(pattern), source_text, re.IGNORECASE)
        if not match:
            continue
        start = max(match.start() - 120, 0)
        end = min(match.end() + 120, len(source_text))
        excerpt = source_text[start:end].strip().replace("\n", " ")
        return excerpt
    return None


def _title_case(value: str) -> str:
    return value.replace("_", " ").title()
