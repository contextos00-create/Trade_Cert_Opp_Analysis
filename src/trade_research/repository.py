"""Idempotent persistence of source versions, evidence and coverage outcomes."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from trade_research.db import (
    ClaimEvidenceRow,
    ClaimRow,
    CoverageRecordRow,
    DocumentRow,
    EvidenceSpanRow,
    JurisdictionRow,
    RequirementVersionRow,
    ResearchRunRow,
    RetrievalEventRow,
    SourceRow,
    TradeRow,
    ValidationResultRow,
    utcnow,
)
from trade_research.models import CoverageStatus, ResearchResult
from trade_research.registry import JURISDICTIONS


def save_research_result(
    session: Session,
    result: ResearchResult,
    request_json: dict,
    documents: list[dict],
    failed_sources: list[dict],
    errors: list[str],
    graph_version: str,
) -> None:
    """Persist once per run ID. A replay from a graph checkpoint is harmless."""
    if session.get(ResearchRunRow, result.research_run_id) is not None:
        return
    requirement = result.requirement
    code = requirement.state_code
    if session.get(JurisdictionRow, code) is None:
        session.add(JurisdictionRow(code=code, name=JURISDICTIONS[code]))
    if session.get(TradeRow, requirement.trade) is None:
        session.add(TradeRow(name=requirement.trade, aliases=[]))
    session.flush()

    now = utcnow()
    session.add(
        ResearchRunRow(
            id=result.research_run_id,
            request_json=request_json,
            graph_version=graph_version,
            status=requirement.research_status.value,
            started_at=now,
            completed_at=now,
            errors=errors,
        )
    )
    session.flush()
    version = RequirementVersionRow(
        research_run_id=result.research_run_id,
        snapshot_json=requirement.model_dump(mode="json"),
        research_status=requirement.research_status.value,
        observed_at=now,
    )
    session.add(version)
    session.flush()

    document_ids: dict[tuple[str, str], str] = {}
    for item in documents:
        source = session.scalar(
            select(SourceRow).where(SourceRow.canonical_url == item["source_url"])
        )
        if source is None:
            source = SourceRow(
                canonical_url=item["source_url"],
                publisher=item["publisher"],
                source_type=item["source_type"],
                authority_tier=item["authority_tier"],
            )
            session.add(source)
            session.flush()
        document = session.scalar(
            select(DocumentRow).where(
                DocumentRow.source_id == source.id,
                DocumentRow.content_sha256 == item["content_sha256"],
            )
        )
        retrieved_at = datetime.fromisoformat(item["retrieved_at"])
        if document is None:
            document = DocumentRow(
                source_id=source.id,
                content_sha256=item["content_sha256"],
                raw_artifact_path=item["raw_artifact_path"],
                extracted_text=item["extracted_text"],
                mime_type=item["mime_type"],
                title=item["title"],
                resolved_url=item["resolved_url"],
                etag=item.get("etag"),
                last_modified=item.get("last_modified"),
                first_retrieved_at=retrieved_at,
                last_retrieved_at=retrieved_at,
            )
            session.add(document)
            session.flush()
        else:
            document.last_retrieved_at = retrieved_at
        session.add(
            RetrievalEventRow(
                source_id=source.id,
                document_id=document.id,
                retrieved_at=retrieved_at,
                status_code=item["status_code"],
            )
        )
        document_ids[(item["source_url"], item["content_sha256"])] = document.id

    for item in failed_sources:
        candidate = item["source"]
        url = candidate["url"]
        source = session.scalar(select(SourceRow).where(SourceRow.canonical_url == url))
        if source is None:
            source = SourceRow(
                canonical_url=url,
                publisher=candidate.get("publisher"),
                source_type=candidate["source_type"],
                authority_tier=candidate["authority_tier"],
            )
            session.add(source)
            session.flush()
        session.add(
            RetrievalEventRow(
                source_id=source.id,
                document_id=None,
                retrieved_at=datetime.fromisoformat(item["retrieved_at"]),
                status_code=None,
                error=item["error"],
            )
        )

    for evidence in requirement.source_evidence:
        key = (str(evidence.source_url), evidence.content_sha256)
        document_id = document_ids[key]
        session.add(
            EvidenceSpanRow(
                id=evidence.evidence_id,
                document_id=document_id,
                field_path=evidence.field_path,
                quoted_text=evidence.quoted_text,
                text_start=evidence.text_start,
                text_end=evidence.text_end,
                page_number=evidence.page_number,
                section=evidence.section,
                asserted_value_json=evidence.asserted_value,
                effective_from=evidence.effective_from,
                effective_to=evidence.effective_to,
            )
        )
    session.flush()
    for claim in requirement.field_claims:
        row = ClaimRow(
            requirement_version_id=version.id,
            field_path=claim.field_path,
            value_json=claim.value,
            status=claim.status,
            confidence=claim.confidence,
        )
        session.add(row)
        session.flush()
        for evidence_id in claim.evidence_ids:
            session.add(ClaimEvidenceRow(claim_id=row.id, evidence_id=evidence_id))
        session.add(
            ValidationResultRow(
                research_run_id=result.research_run_id,
                check_name="quote_hash_and_offset",
                passed=bool(claim.evidence_ids),
                detail=claim.field_path,
            )
        )

    key = {
        "primary_jurisdiction": code,
        "locality_key": requirement.locality or "",
        "trade": requirement.trade,
        "credential_key": requirement.credential_level or "",
        "effective_date_key": request_json.get("as_of_date") or "current",
    }
    coverage = session.scalar(select(CoverageRecordRow).filter_by(**key))
    if coverage is None:
        coverage = CoverageRecordRow(**key)
        session.add(coverage)
    coverage.status = result.coverage_status.value
    coverage.research_run_id = result.research_run_id
    coverage.source_count = len(documents)
    coverage.authoritative_source_count = sum(d["authority_tier"] <= 5 for d in documents)
    coverage.unresolved_field_count = len(requirement.missing_fields)
    coverage.last_attempted_at = now
    coverage.review_reason = result.review_reason
    if result.coverage_status in (
        CoverageStatus.VALIDATED,
        CoverageStatus.VALIDATED_NOT_APPLICABLE,
    ):
        coverage.last_validated_at = now
    session.commit()
