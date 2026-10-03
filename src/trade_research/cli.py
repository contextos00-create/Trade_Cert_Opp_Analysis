"""Local CLI for a conservative, reviewable research workflow."""

from __future__ import annotations

import csv
import json
import os
from contextlib import nullcontext
from datetime import date
from pathlib import Path

import typer
from langgraph.checkpoint.postgres import PostgresSaver
from sqlalchemy import select
from sqlalchemy.engine import make_url
from sqlalchemy.orm import sessionmaker

from trade_research.db import (
    CoverageRecordRow,
    audit_coverage,
    database_url,
    engine_for,
    seed_primary_inventory,
)
from trade_research.graph import ResearchPipeline
from trade_research.models import CuratedClaim, ResearchRequest, SourceCandidate
from trade_research.registry import JURISDICTIONS, REQUIRED_TRADES

app = typer.Typer(help="Evidence-first US trade certification research")
nationwide_app = typer.Typer(help="National coverage ledger")
coverage_app = typer.Typer(help="Coverage exports and completion gate")
app.add_typer(nationwide_app, name="nationwide")
app.add_typer(coverage_app, name="coverage")


def _artifact_dir() -> Path:
    return Path(os.environ.get("TRADE_RESEARCH_DATA_DIR", ".trade_research")).resolve()


def _checkpointer_context():
    url = make_url(database_url())
    if url.get_backend_name() != "postgresql":
        return nullcontext(None)
    psycopg_url = url.set(drivername="postgresql").render_as_string(hide_password=False)
    return PostgresSaver.from_conn_string(psycopg_url)


@app.command("run")
def run(
    state: str = typer.Option(..., help="State or territory name/code"),
    trade: str = typer.Option(..., help="Required trade or alias"),
    credential: str | None = typer.Option(None, help="Official or canonical credential level"),
    locality: str | None = typer.Option(None),
    as_of_date: str | None = typer.Option(None, help="ISO date, YYYY-MM-DD"),
    source_url: list[str] | None = typer.Option(None, help="Official HTTPS source URL; repeatable"),
    source_tier: int = typer.Option(7, min=1, max=7, help="Declared source tier; review required"),
    claims_file: Path | None = typer.Option(
        None, help="JSON array of human-curated candidate claims"
    ),
) -> None:
    """Retrieve supplied sources and retain only verifiable candidate passages."""
    try:
        parsed_date = date.fromisoformat(as_of_date) if as_of_date else None
    except ValueError as exc:
        raise typer.BadParameter("as-of-date must be YYYY-MM-DD") from exc
    request = ResearchRequest(
        state=state,
        trade=trade,
        credential_level=credential,
        locality=locality,
        as_of_date=parsed_date,
    )
    sources = [SourceCandidate(url=url, authority_tier=source_tier) for url in source_url or []]
    claims = []
    if claims_file is not None:
        payload = json.loads(claims_file.read_text())
        if not isinstance(payload, list):
            raise typer.BadParameter("Claims file must contain a JSON array")
        claims = [CuratedClaim.model_validate(item) for item in payload]
    engine = engine_for()
    pipeline = ResearchPipeline(sessionmaker(engine), _artifact_dir())
    with _checkpointer_context() as checkpointer:
        if checkpointer is not None:
            checkpointer.setup()
        result = pipeline.run(request, sources, claims, checkpointer=checkpointer)
    typer.echo(result.model_dump_json(indent=2))


@nationwide_app.command("manifest")
def manifest() -> None:
    """Show the required primary jurisdictions and trades."""
    typer.echo(
        json.dumps(
            {
                "jurisdictions": JURISDICTIONS,
                "required_trades": REQUIRED_TRADES,
                "expected_primary_inventories": len(JURISDICTIONS) * len(REQUIRED_TRADES),
            },
            indent=2,
        )
    )


@nationwide_app.command("seed")
def seed() -> None:
    """Seed pending inventory work; this performs no regulatory research."""
    engine = engine_for()
    with sessionmaker(engine)() as session:
        created = seed_primary_inventory(session)
        session.commit()
    typer.echo(f"Created {created} pending jurisdiction/trade inventories")


@coverage_app.command("audit")
def audit(fail_on_incomplete: bool = typer.Option(False)) -> None:
    """Fail the national completion gate if any expected work is unresolved."""
    engine = engine_for()
    with sessionmaker(engine)() as session:
        result = audit_coverage(session)
    typer.echo(json.dumps(result, indent=2))
    if fail_on_incomplete and not result["national_complete"]:
        raise typer.Exit(code=1)


@coverage_app.command("export")
def export(
    format: str = typer.Option("json", help="json or csv"),
    output: Path = typer.Option(..., help="Output path"),
) -> None:
    """Export the current coverage ledger without implying completion."""
    if format not in {"json", "csv"}:
        raise typer.BadParameter("Format must be json or csv")
    engine = engine_for()
    with sessionmaker(engine)() as session:
        rows = list(
            session.scalars(
                select(CoverageRecordRow).order_by(
                    CoverageRecordRow.primary_jurisdiction,
                    CoverageRecordRow.trade,
                    CoverageRecordRow.locality_key,
                    CoverageRecordRow.credential_key,
                )
            )
        )
        records = [
            {
                "primary_jurisdiction": r.primary_jurisdiction,
                "locality": r.locality_key or None,
                "trade": r.trade,
                "credential_level": r.credential_key or None,
                "effective_date": r.effective_date_key,
                "status": r.status,
                "research_run_id": r.research_run_id,
                "source_count": r.source_count,
                "authoritative_source_count": r.authoritative_source_count,
                "unresolved_field_count": r.unresolved_field_count,
                "last_attempted_at": r.last_attempted_at.isoformat()
                if r.last_attempted_at
                else None,
                "review_reason": r.review_reason,
            }
            for r in rows
        ]
    output.parent.mkdir(parents=True, exist_ok=True)
    if format == "json":
        output.write_text(json.dumps(records, indent=2) + "\n")
    else:
        with output.open("w", newline="") as stream:
            writer = csv.DictWriter(
                stream,
                fieldnames=list(records[0])
                if records
                else ["primary_jurisdiction", "locality", "trade", "credential_level", "status"],
            )
            writer.writeheader()
            for record in records:
                writer.writerow(record)
    typer.echo(f"Exported {len(records)} coverage records to {output}")


if __name__ == "__main__":
    app()
