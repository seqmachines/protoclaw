import asyncio
from pathlib import Path

import click
import yaml

from protoclaw.config import settings
from protoclaw.models import Protocol


@click.group()
def cli() -> None:
    """Protoclaw — sequencing protocol knowledge base."""


async def _ensure_schema() -> None:
    from protoclaw.db.engine import engine
    from protoclaw.db.tables import Base

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


@cli.command()
@click.option(
    "--seeds-dir",
    type=click.Path(exists=True, path_type=Path),
    default=Path("seeds/protocols"),
    help="Directory containing seed YAML files.",
)
def seed(seeds_dir: Path) -> None:
    """Load seed protocol YAML files into the database."""
    asyncio.run(_seed(seeds_dir))


async def _seed(seeds_dir: Path) -> None:

    from protoclaw.db.engine import async_session
    from protoclaw.db.repositories import create_protocol, get_protocol_by_slug

    await _ensure_schema()

    yaml_files = sorted(seeds_dir.glob("*.yaml"))
    if not yaml_files:
        click.echo(f"No YAML files found in {seeds_dir}")
        return

    click.echo(f"Found {len(yaml_files)} seed files in {seeds_dir}")

    loaded = 0
    skipped = 0
    errors = 0

    async with async_session() as session:
        for f in yaml_files:
            try:
                data = yaml.safe_load(f.read_text())
                protocol = Protocol(**data)

                existing = await get_protocol_by_slug(session, protocol.slug)
                if existing:
                    click.echo(f"  SKIP: {protocol.slug} (already exists)")
                    skipped += 1
                    continue

                await create_protocol(session, protocol)
                click.echo(f"  OK: {protocol.slug} ({protocol.assay_family})")
                loaded += 1
            except Exception as e:
                click.echo(f"  FAIL: {f.name}: {e}", err=True)
                errors += 1

        await session.commit()

    click.echo(f"\nDone: {loaded} loaded, {skipped} skipped, {errors} errors")


@cli.command()
@click.option("--host", default=settings.api_host)
@click.option("--port", default=settings.api_port, type=int)
def serve(host: str, port: int) -> None:
    """Run the FastAPI API server."""
    import uvicorn

    uvicorn.run("protoclaw.api.app:app", host=host, port=port, reload=True)


@cli.command()
@click.option(
    "--sources",
    type=click.Path(exists=True, path_type=Path),
    default=Path("seeds/sources.yaml"),
    help="YAML file with seed source URLs and keywords.",
)
@click.option("--dry-run", is_flag=True, help="Show what would run without executing.")
def run(sources: Path, dry_run: bool) -> None:
    """Run the full agent pipeline (Source Scout → Publisher)."""
    asyncio.run(_run_pipeline(sources, dry_run))


async def _run_pipeline(sources: Path, dry_run: bool) -> None:
    from protoclaw.agents.source_scout.tools import load_seed_sources

    seed_sources = await load_seed_sources(str(sources))
    click.echo(f"Pipeline sources: {len(seed_sources)} seed URLs from {sources}")

    if dry_run:
        for src in seed_sources:
            click.echo(f"  - {src.url}")
        click.echo("\nDry run — no agents executed.")
        return

    try:
        from protoclaw.agents.root_agent import pipeline_agent

        click.echo("Starting pipeline...")
        # ADK agent invocation — requires an active Gemini API key
        from google.adk.runners import InMemoryRunner

        runner = InMemoryRunner(agent=pipeline_agent, app_name=pipeline_agent.name)
        session = await runner.session_service.create_session(app_name=pipeline_agent.name, user_id="cli")

        from google.genai.types import Content, Part

        user_msg = Content(
            role="user",
            parts=[Part(text=f"Process these source documents: {sources}")],
        )

        async for event in runner.run_async(
            session_id=session.id, user_id="cli", new_message=user_msg
        ):
            if event.content and event.content.parts:
                for part in event.content.parts:
                    if part.text:
                        click.echo(f"[{event.author}] {part.text}")

        click.echo("\nPipeline complete.")
    except ImportError as e:
        click.echo(f"Error: Missing dependency — {e}", err=True)
        click.echo("Install google-adk and google-genai.", err=True)
        raise SystemExit(1)


@cli.command(name="list")
@click.option("--assay", default=None, help="Filter by assay family.")
@click.option("--limit", default=50, type=int)
def list_protocols(assay: str | None, limit: int) -> None:
    """List protocols in the database."""
    asyncio.run(_list_protocols(assay, limit))


async def _list_protocols(assay: str | None, limit: int) -> None:
    from protoclaw.db.engine import async_session
    from protoclaw.db.repositories import list_protocols as db_list

    await _ensure_schema()

    async with async_session() as session:
        rows = await db_list(session, assay_family=assay, limit=limit)

    if not rows:
        click.echo("No protocols found.")
        return

    click.echo(f"{'Slug':<35} {'Assay':<25} {'Score':<8} {'Status'}")
    click.echo("─" * 80)
    for r in rows:
        click.echo(
            f"{r.slug:<35} {r.assay_family:<25} {r.confidence_score:<8.2f} "
            f"{r.review_status}"
        )
    click.echo(f"\n{len(rows)} protocol(s)")


@cli.command()
@click.option("--url", "source_url", default=None, help="Protocol source URL.")
@click.option(
    "--file",
    "source_file",
    type=click.Path(exists=True, dir_okay=False, path_type=Path),
    default=None,
    help="Local protocol file path, including PDF.",
)
@click.option("--notes", default=None, help="Optional submission notes.")
@click.option("--submitted-by", default="cli", help="Submitter identity.")
@click.option("--force", is_flag=True, help="Allow duplicate submissions to create a comparison review.")
def submit(
    source_url: str | None,
    source_file: Path | None,
    notes: str | None,
    submitted_by: str,
    force: bool,
) -> None:
    """Submit a source URL or local file and run ingestion immediately."""
    asyncio.run(_submit(source_url, source_file, notes, submitted_by, force))


async def _submit(
    source_url: str | None,
    source_file: Path | None,
    notes: str | None,
    submitted_by: str,
    force: bool,
) -> None:
    from protoclaw.db.engine import async_session
    from protoclaw.db.repositories import get_protocol_by_slug
    from protoclaw.services.ingestion import (
        build_protocol_draft,
        create_submission_and_ingest,
    )

    if bool(source_url) == bool(source_file):
        raise click.UsageError("Provide exactly one of --url or --file.")

    source_ref = source_url or source_file.resolve().as_uri()
    await _ensure_schema()
    draft_payload = await build_protocol_draft(source_ref=source_ref)

    async with async_session() as session:
        existing = await get_protocol_by_slug(
            session, draft_payload["protocol"]["slug"]
        )

    if existing is not None and not force:
        click.echo(
            "Duplicate protocol detected for existing slug "
            f"'{draft_payload['protocol']['slug']}'.\n"
            "Re-run with `--force` to create a draft comparison review instead of skipping."
        )
        return

    result = await create_submission_and_ingest(
        source_ref,
        notes=notes,
        submitted_by=submitted_by,
        draft_payload=draft_payload,
        force_duplicate_review=force,
    )
    click.echo(yaml.safe_dump(result, sort_keys=False))


@cli.command(name="submissions")
@click.option("--limit", default=20, type=int)
def list_submissions(limit: int) -> None:
    """List recent protocol submissions."""
    asyncio.run(_list_submissions(limit))


async def _list_submissions(limit: int) -> None:
    from protoclaw.db.engine import async_session
    from protoclaw.db.repositories import list_submissions as db_list_submissions
    from protoclaw.services.ingestion import serialize_submission

    await _ensure_schema()

    async with async_session() as session:
        rows = await db_list_submissions(session, limit=limit)

    if not rows:
        click.echo("No submissions found.")
        return

    for row in rows:
        submission = serialize_submission(row)
        click.echo(
            f"{submission['id']} {submission['status']:<10} "
            f"{submission['source_url']}"
        )


@cli.command(name="prune")
@click.option("--keep-slug", default=None, help="Protocol slug to keep.")
@click.option("--keep-name", default=None, help="Exact protocol name to keep.")
def prune_protocols(keep_slug: str | None, keep_name: str | None) -> None:
    """Delete all protocols except one retained record."""
    asyncio.run(_prune_protocols(keep_slug, keep_name))


async def _prune_protocols(
    keep_slug: str | None,
    keep_name: str | None,
) -> None:
    from protoclaw.db.engine import async_session
    from protoclaw.db.repositories import (
        get_protocol_by_name,
        get_protocol_by_slug,
        prune_database_to_protocol,
    )

    if bool(keep_slug) == bool(keep_name):
        raise click.UsageError("Provide exactly one of --keep-slug or --keep-name.")

    await _ensure_schema()

    async with async_session() as session:
        keep_row = (
            await get_protocol_by_slug(session, keep_slug)
            if keep_slug
            else await get_protocol_by_name(session, keep_name or "")
        )
        if keep_row is None:
            label = keep_slug or keep_name
            raise click.ClickException(f"Protocol not found: {label}")

        result = await prune_database_to_protocol(session, keep_protocol_id=keep_row.id)
        await session.commit()

    click.echo(yaml.safe_dump(result, sort_keys=False))


@cli.command(name="draft")
@click.option("--url", "source_url", default=None, help="Protocol source URL.")
@click.option(
    "--file",
    "source_file",
    type=click.Path(exists=True, dir_okay=False, path_type=Path),
    default=None,
    help="Local protocol file path, including PDF.",
)
@click.option("--text", "source_text", default=None, help="Inline source text.")
def draft_protocol(
    source_url: str | None,
    source_file: Path | None,
    source_text: str | None,
) -> None:
    """Extract a structured protocol draft with Gemini without writing to the database."""
    asyncio.run(_draft_protocol(source_url, source_file, source_text))


async def _draft_protocol(
    source_url: str | None,
    source_file: Path | None,
    source_text: str | None,
) -> None:
    from protoclaw.services.ingestion import build_protocol_draft

    choices = [bool(source_url), bool(source_file), bool(source_text)]
    if sum(choices) != 1:
        raise click.UsageError("Provide exactly one of --url, --file, or --text.")

    if source_text is not None:
        result = await build_protocol_draft(source_text=source_text)
    else:
        source_ref = source_url or source_file.resolve().as_uri()
        result = await build_protocol_draft(source_ref=source_ref)

    click.echo(yaml.safe_dump(result, sort_keys=False, allow_unicode=False))


if __name__ == "__main__":
    cli()
