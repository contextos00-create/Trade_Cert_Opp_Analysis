from __future__ import annotations

import hashlib
from datetime import UTC, date, datetime
from pathlib import Path

import httpx
import pytest
from langgraph.checkpoint.memory import MemorySaver
from sqlalchemy import create_engine, event, func, select
from sqlalchemy.orm import sessionmaker

from trade_research.db import (
    Base,
    CoverageRecordRow,
    DocumentRow,
    EvidenceSpanRow,
    ResearchRunRow,
    RetrievalEventRow,
    audit_coverage,
    seed_primary_inventory,
)
from trade_research.documents import (
    RetrievedDocument,
    SourceUnavailable,
    fetch_document,
    save_raw,
)
from trade_research.evidence import EvidenceError, evidence_for_claim
from trade_research.graph import ResearchPipeline
from trade_research.models import (
    CoverageStatus,
    CuratedClaim,
    ResearchRequest,
    SourceCandidate,
)
from trade_research.registry import JURISDICTIONS, REQUIRED_TRADES, normalize_jurisdiction


def _fixture_document(tmp_path, url="https://ohio.gov/board/license"):
    text = "Ohio Board says: Application fee: $100."
    raw = f"<html><title>Ohio Board</title><body>{text}</body></html>".encode()
    digest, path = save_raw(raw, tmp_path)
    return RetrievedDocument(
        source_url=url,
        resolved_url=url,
        authority_tier=2,
        source_type="official_page",
        publisher="Ohio Board",
        title="Ohio Board",
        mime_type="text/html",
        content_sha256=digest,
        raw_artifact_path=path,
        extracted_text=text,
        page_starts=[0],
        retrieved_at=datetime.now(UTC),
        status_code=200,
    )


def _database():
    engine = create_engine("sqlite+pysqlite:///:memory:")

    @event.listens_for(engine, "connect")
    def _foreign_keys(connection, _record):
        connection.execute("PRAGMA foreign_keys=ON")

    Base.metadata.create_all(engine)
    return sessionmaker(engine)


def test_manifest_and_idempotent_pending_inventory():
    assert len(JURISDICTIONS) == 56
    assert {"DC", "PR", "GU", "VI", "AS", "MP"}.issubset(JURISDICTIONS)
    assert len(REQUIRED_TRADES) == 7
    assert normalize_jurisdiction("Northern Mariana Islands")[0] == "MP"
    factory = _database()
    with factory() as session:
        assert seed_primary_inventory(session) == 392
        session.commit()
        assert seed_primary_inventory(session) == 0
        session.commit()
        audit = audit_coverage(session)
    assert audit["present_primary_inventories"] == 392
    assert audit["status_counts"][CoverageStatus.NOT_STARTED.value] == 392
    assert audit["national_complete"] is False
    with factory() as session:
        for row in session.scalars(select(CoverageRecordRow)):
            row.status = CoverageStatus.VALIDATED.value
        session.commit()
        audit = audit_coverage(session)
    assert audit["scope_audited"] is False
    assert audit["national_complete"] is False


def test_https_fetch_checks_robots_and_preserves_source_bytes(tmp_path):
    page = b"<html><title>License</title><body>Application fee: $100</body></html>"

    def respond(request):
        if request.url.path == "/robots.txt":
            return httpx.Response(200, text="User-agent: *\nAllow: /\n")
        return httpx.Response(200, content=page, headers={"content-type": "text/html"})

    with httpx.Client(transport=httpx.MockTransport(respond)) as client:
        document = fetch_document(
            SourceCandidate(url="https://ohio.gov/board/license", authority_tier=2),
            tmp_path,
            client,
        )
    assert document.extracted_text == "License Application fee: $100"
    assert Path(document.raw_artifact_path).read_bytes() == page

    def disallow(request):
        return httpx.Response(200, text="User-agent: *\nDisallow: /board/\n")

    with (
        httpx.Client(transport=httpx.MockTransport(disallow)) as client,
        pytest.raises(SourceUnavailable, match="robots.txt disallows"),
    ):
        fetch_document(
            SourceCandidate(url="https://ohio.gov/board/license", authority_tier=2),
            tmp_path,
            client,
        )


def test_quote_hash_offsets_and_effective_window(tmp_path):
    document = _fixture_document(tmp_path)
    claim = CuratedClaim(
        field_path="application_fee",
        value="$100",
        quoted_text="Application fee: $100",
        source_url=document.source_url,
        effective_from=date(2026, 1, 1),
        effective_to=date(2026, 12, 31),
    )
    span = evidence_for_claim(claim, document, date(2026, 10, 3))
    assert document.extracted_text[span.text_start : span.text_end] == span.quoted_text
    assert (
        span.content_sha256
        == hashlib.sha256(Path(document.raw_artifact_path).read_bytes()).hexdigest()
    )
    with pytest.raises(EvidenceError, match="effective dates"):
        evidence_for_claim(claim, document, date(2027, 1, 1))
    with open(document.raw_artifact_path, "ab") as stream:
        stream.write(b"tampered")
    with pytest.raises(EvidenceError, match="SHA-256"):
        evidence_for_claim(claim, document)


def test_graph_persists_reviewable_claim_without_asserting_rule(tmp_path):
    factory = _database()
    document = _fixture_document(tmp_path)
    pipeline = ResearchPipeline(factory, tmp_path, retriever=lambda _candidate, _dir: document)
    result = pipeline.run(
        ResearchRequest(state="OH", trade="electrician", credential_level="contractor"),
        sources=[SourceCandidate(url=document.source_url, authority_tier=2)],
        claims=[
            CuratedClaim(
                field_path="application_fee",
                value="$100",
                quoted_text="Application fee: $100",
                source_url=document.source_url,
            )
        ],
        checkpointer=MemorySaver(),
    )
    assert result.coverage_status == CoverageStatus.PARTIAL_NEEDS_REVIEW
    assert result.requirement.application_fee is None
    assert result.requirement.field_claims[0].status == "review_required"
    assert len(result.requirement.source_evidence) == 1
    with factory() as session:
        assert session.scalar(select(func.count()).select_from(ResearchRunRow)) == 1
        assert session.scalar(select(func.count()).select_from(DocumentRow)) == 1
        assert session.scalar(select(func.count()).select_from(EvidenceSpanRow)) == 1
        row = session.scalar(select(CoverageRecordRow))
        assert row.credential_key == "contractor"
        assert row.status == CoverageStatus.PARTIAL_NEEDS_REVIEW.value


def test_graph_rejects_unmatched_quote_and_bounds_followups(tmp_path):
    factory = _database()
    document = _fixture_document(tmp_path)

    class Discovery:
        def __init__(self):
            self.rounds = []

        def discover(self, _request, _missing, round_number):
            self.rounds.append(round_number)
            return [
                SourceCandidate(url=f"https://ohio.gov/source-{round_number}", authority_tier=2)
            ]

    discovery = Discovery()
    pipeline = ResearchPipeline(
        factory,
        tmp_path,
        search_adapter=discovery,
        retriever=lambda candidate, _dir: RetrievedDocument(
            **{
                **document.__dict__,
                "source_url": str(candidate.url),
                "resolved_url": str(candidate.url),
            }
        ),
    )
    result = pipeline.run(
        ResearchRequest(state="Ohio", trade="electrical", credential_level="journeyman"),
        claims=[
            CuratedClaim(
                field_path="exam.required",
                value=True,
                quoted_text="Not in this page",
                source_url="https://ohio.gov/source-0",
            )
        ],
    )
    assert discovery.rounds == [0, 1, 2, 3]
    assert len(result.requirement.field_claims) == 0
    assert any("Quoted passage was not found" in reason for reason in result.review_reason)
    assert result.coverage_status == CoverageStatus.PARTIAL_NEEDS_REVIEW


def test_inaccessible_source_is_recorded_as_blocked(tmp_path):
    factory = _database()

    def unavailable(_candidate, _dir):
        raise SourceUnavailable("Official site denied the request")

    pipeline = ResearchPipeline(factory, tmp_path, retriever=unavailable)
    result = pipeline.run(
        ResearchRequest(state="TX", trade="plumbing", credential_level="journeyman"),
        sources=[SourceCandidate(url="https://texas.gov/license", authority_tier=2)],
    )
    assert result.coverage_status == CoverageStatus.BLOCKED_SOURCE
    with factory() as session:
        event = session.scalar(select(RetrievalEventRow))
        assert event.document_id is None
        assert "denied" in event.error
