# Trade Certification Intelligence Engine — foundation

This repository has started the delivery sequence in
[the nationwide build document](NATIONWIDE_US_TRADE_CERTIFICATION_BUILD_DOC.md).
The current code is an evidence-preserving foundation. It does **not** contain
verified licensing rules or a completed national inventory.

## Local setup

Requires Python 3.12+, `uv`, Docker and Docker Compose. From this repository:

```bash
export UV_CACHE_DIR=/workspace/.uv-cache  # or another writable directory
uv sync --frozen
docker compose up -d --wait
uv run alembic upgrade head
uv run trade-research nationwide seed
uv run trade-research coverage audit
```

The Compose database is bound to `127.0.0.1:55432` and uses PostgreSQL's
`trust` method **only for this isolated local development container**. For a
shared or deployed database, set `DATABASE_URL` to an authenticated PostgreSQL
URL and manage credentials outside this repository. Set
`TRADE_RESEARCH_DATA_DIR` to relocate the content-addressed source store; it
defaults to `.trade_research/`. Raw source bytes and database volumes are local
artifacts, not checked-in research results. `LANGSMITH_*` variables are not
required by this foundation; tracing and evaluations are a later stage.

No server runs for the CLI. Restart PostgreSQL after a machine restart with
`docker compose up -d --wait`; then check `uv run alembic current` and
`uv run trade-research coverage audit`.

## Research a single credential

```bash
uv run trade-research run \
  --state OH --trade electrician --credential journeyman \
  --source-url https://example.gov/official-page --source-tier 2
```

Supply actual official URLs. Search snippets are not evidence. The source
fetcher checks robots.txt, TLS, a 25 MiB size cap and HTTP status; it stores
immutable bytes by SHA-256 and extracts HTML, PDF, or plain text. A source that
cannot be fetched is recorded as a blocker. Pass `--claims-file claims.json`
to attach candidate field values and exact quotations. Each claim must contain
`field_path`, `value`, `quoted_text`, and `source_url`; optional dates are
`effective_from` and `effective_to`. For example:

```json
[
  {
    "field_path": "application_fee",
    "value": "$100",
    "quoted_text": "Application fee: $100",
    "source_url": "https://example.gov/official-page"
  }
]
```

The quote must appear in the extracted source text, the stored bytes must
match their SHA-256, and any declared effective window must cover the requested
date. The pipeline then marks the claim **review required**. Exact text alone
cannot prove the legal meaning, right credential, source currency, or full
jurisdiction scope. It does not populate a material requirement field or mark a
coverage record validated. The result includes explicit unknown fields and
review reasons. Claims with unmatched quotations are rejected.

## Coverage and checks

`nationwide seed` creates 392 `not_started` inventory records: 56 primary
jurisdictions × seven required trades. It is idempotent and does not invent
credential levels. Local authority and federal overlay inventories have not
yet been expanded. These are inspectable with:

```bash
uv run trade-research nationwide manifest
uv run trade-research coverage export --format json --output coverage.json
uv run trade-research coverage audit --fail-on-incomplete
uv run pytest
```

The audit intentionally exits nonzero until the national completion criteria
are met. This is a coverage gate, not a test failure to bypass.

## Current delivery status and next work

Implemented: request/evidence/claim/coverage contracts; 56-jurisdiction
manifest; source retrieval and immutable raw store; exact quote, hash, offset
and date checks; an initial LangGraph; PostgreSQL schema and Alembic migration;
LangGraph PostgreSQL checkpoints; a pending coverage ledger and JSON/CSV export.
The graph has a three-follow-up-round cap and a search adapter interface.

Still required before nationwide use: official-source discovery and LLM
extraction adapters; source-to-jurisdiction and semantic entailment validation;
credential and local-authority inventories; human review decisions and
publication rules; idempotent nationwide dispatch; change detection;
representative gold cases; LangSmith tracing/evaluation; a coverage API and UI;
and actual verified research for every required jurisdiction/trade/credential.
No national completion claim is made while any required record remains pending.
