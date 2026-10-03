"""Relational store for immutable source versions and reviewable research runs."""

from __future__ import annotations

import os
from datetime import UTC, datetime
from uuid import uuid4

from sqlalchemy import (
    JSON,
    Date,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
    create_engine,
    select,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, Session, mapped_column

from trade_research.models import CoverageStatus
from trade_research.registry import JURISDICTIONS, REQUIRED_TRADES


def utcnow() -> datetime:
    return datetime.now(UTC)


def new_id() -> str:
    return str(uuid4())


class Base(DeclarativeBase):
    pass


class JurisdictionRow(Base):
    __tablename__ = "jurisdictions"
    code: Mapped[str] = mapped_column(String(8), primary_key=True)
    name: Mapped[str] = mapped_column(String(100))
    kind: Mapped[str] = mapped_column(String(24), default="primary")


class TradeRow(Base):
    __tablename__ = "trades"
    name: Mapped[str] = mapped_column(String(64), primary_key=True)
    aliases: Mapped[list] = mapped_column(JSON, default=list)


class AuthorityRow(Base):
    __tablename__ = "regulatory_authorities"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    name: Mapped[str] = mapped_column(String(255))
    role: Mapped[str] = mapped_column(String(64))
    official_url: Mapped[str | None] = mapped_column(Text)
    jurisdiction_code: Mapped[str | None] = mapped_column(ForeignKey("jurisdictions.code"))


class CredentialRow(Base):
    __tablename__ = "credentials"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    jurisdiction_code: Mapped[str] = mapped_column(ForeignKey("jurisdictions.code"))
    locality: Mapped[str | None] = mapped_column(String(255))
    trade: Mapped[str] = mapped_column(ForeignKey("trades.name"))
    official_title: Mapped[str] = mapped_column(String(255))
    canonical_level: Mapped[str | None] = mapped_column(String(80))
    authority_id: Mapped[str | None] = mapped_column(ForeignKey("regulatory_authorities.id"))
    scope: Mapped[str] = mapped_column(String(32))


class SourceRow(Base):
    __tablename__ = "sources"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    canonical_url: Mapped[str] = mapped_column(Text, unique=True)
    publisher: Mapped[str | None] = mapped_column(String(255))
    source_type: Mapped[str] = mapped_column(String(64))
    authority_tier: Mapped[int] = mapped_column(Integer)
    first_seen_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class DocumentRow(Base):
    __tablename__ = "documents"
    __table_args__ = (UniqueConstraint("source_id", "content_sha256"),)
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    source_id: Mapped[str] = mapped_column(ForeignKey("sources.id"))
    content_sha256: Mapped[str] = mapped_column(String(64))
    raw_artifact_path: Mapped[str] = mapped_column(Text)
    extracted_text: Mapped[str] = mapped_column(Text)
    mime_type: Mapped[str] = mapped_column(String(128))
    title: Mapped[str] = mapped_column(Text)
    resolved_url: Mapped[str] = mapped_column(Text)
    etag: Mapped[str | None] = mapped_column(Text)
    last_modified: Mapped[str | None] = mapped_column(Text)
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    first_retrieved_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    last_retrieved_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class RetrievalEventRow(Base):
    __tablename__ = "retrieval_events"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    source_id: Mapped[str] = mapped_column(ForeignKey("sources.id"))
    document_id: Mapped[str | None] = mapped_column(ForeignKey("documents.id"))
    retrieved_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    status_code: Mapped[int | None] = mapped_column(Integer)
    error: Mapped[str | None] = mapped_column(Text)


class ResearchRunRow(Base):
    __tablename__ = "research_runs"
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    request_json: Mapped[dict] = mapped_column(JSON)
    graph_version: Mapped[str] = mapped_column(String(40))
    status: Mapped[str] = mapped_column(String(32))
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    errors: Mapped[list] = mapped_column(JSON, default=list)


class RequirementVersionRow(Base):
    __tablename__ = "requirement_versions"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    research_run_id: Mapped[str] = mapped_column(ForeignKey("research_runs.id"), unique=True)
    snapshot_json: Mapped[dict] = mapped_column(JSON)
    research_status: Mapped[str] = mapped_column(String(32))
    observed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    valid_from: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    valid_to: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    superseded_by: Mapped[str | None] = mapped_column(String(36))


class ClaimRow(Base):
    __tablename__ = "claims"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    requirement_version_id: Mapped[str] = mapped_column(ForeignKey("requirement_versions.id"))
    field_path: Mapped[str] = mapped_column(String(255))
    value_json: Mapped[object | None] = mapped_column(JSON)
    status: Mapped[str] = mapped_column(String(32))
    confidence: Mapped[float | None] = mapped_column(Float)


class EvidenceSpanRow(Base):
    __tablename__ = "evidence_spans"
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    document_id: Mapped[str] = mapped_column(ForeignKey("documents.id"))
    field_path: Mapped[str] = mapped_column(String(255))
    quoted_text: Mapped[str] = mapped_column(Text)
    text_start: Mapped[int | None] = mapped_column(Integer)
    text_end: Mapped[int | None] = mapped_column(Integer)
    page_number: Mapped[int | None] = mapped_column(Integer)
    section: Mapped[str | None] = mapped_column(String(255))
    asserted_value_json: Mapped[object] = mapped_column(JSON)
    effective_from: Mapped[datetime | None] = mapped_column(Date)
    effective_to: Mapped[datetime | None] = mapped_column(Date)


class ClaimEvidenceRow(Base):
    __tablename__ = "claim_evidence"
    claim_id: Mapped[str] = mapped_column(ForeignKey("claims.id"), primary_key=True)
    evidence_id: Mapped[str] = mapped_column(ForeignKey("evidence_spans.id"), primary_key=True)


class ConflictRow(Base):
    __tablename__ = "conflicts"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    requirement_version_id: Mapped[str] = mapped_column(ForeignKey("requirement_versions.id"))
    field_path: Mapped[str] = mapped_column(String(255))
    competing_claims: Mapped[list] = mapped_column(JSON)
    rationale: Mapped[str | None] = mapped_column(Text)
    review_status: Mapped[str] = mapped_column(String(32), default="open")


class ValidationResultRow(Base):
    __tablename__ = "validation_results"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    research_run_id: Mapped[str] = mapped_column(ForeignKey("research_runs.id"))
    check_name: Mapped[str] = mapped_column(String(80))
    passed: Mapped[bool] = mapped_column()
    detail: Mapped[str | None] = mapped_column(Text)


class ChangeEventRow(Base):
    __tablename__ = "change_events"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    previous_version_id: Mapped[str | None] = mapped_column(ForeignKey("requirement_versions.id"))
    new_version_id: Mapped[str] = mapped_column(ForeignKey("requirement_versions.id"))
    field_path: Mapped[str] = mapped_column(String(255))
    old_value: Mapped[object | None] = mapped_column(JSON)
    new_value: Mapped[object | None] = mapped_column(JSON)
    observed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class ReviewActionRow(Base):
    __tablename__ = "review_actions"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    research_run_id: Mapped[str] = mapped_column(ForeignKey("research_runs.id"))
    action: Mapped[str] = mapped_column(String(32))
    reviewer: Mapped[str] = mapped_column(String(255))
    rationale: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class NationwideRunRow(Base):
    __tablename__ = "nationwide_runs"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    manifest: Mapped[str] = mapped_column(String(40))
    status: Mapped[str] = mapped_column(String(32))
    primary_inventory_audited: Mapped[bool] = mapped_column(default=False, server_default="false")
    credential_levels_audited: Mapped[bool] = mapped_column(default=False, server_default="false")
    locality_expansion_audited: Mapped[bool] = mapped_column(default=False, server_default="false")
    federal_overlays_audited: Mapped[bool] = mapped_column(default=False, server_default="false")
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class CoverageRecordRow(Base):
    __tablename__ = "coverage_records"
    __table_args__ = (
        UniqueConstraint(
            "primary_jurisdiction", "locality_key", "trade", "credential_key", "effective_date_key"
        ),
    )
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    primary_jurisdiction: Mapped[str] = mapped_column(ForeignKey("jurisdictions.code"))
    locality_key: Mapped[str] = mapped_column(String(255), default="")
    trade: Mapped[str] = mapped_column(ForeignKey("trades.name"))
    credential_key: Mapped[str] = mapped_column(String(80), default="")
    effective_date_key: Mapped[str] = mapped_column(String(32), default="current")
    status: Mapped[str] = mapped_column(String(32), default=CoverageStatus.NOT_STARTED.value)
    research_run_id: Mapped[str | None] = mapped_column(ForeignKey("research_runs.id"))
    source_count: Mapped[int] = mapped_column(Integer, default=0)
    authoritative_source_count: Mapped[int] = mapped_column(Integer, default=0)
    unresolved_field_count: Mapped[int] = mapped_column(Integer, default=0)
    last_attempted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    last_validated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    review_reason: Mapped[list] = mapped_column(JSON, default=list)


def database_url() -> str:
    return os.environ.get("DATABASE_URL", "postgresql+psycopg://postgres@127.0.0.1:55432/postgres")


def engine_for(url: str | None = None):
    return create_engine(url or database_url(), pool_pre_ping=True)


def seed_primary_inventory(session: Session) -> int:
    """Create pending jurisdiction/trade inventories; assert no credentials exist yet."""
    created = 0
    for code, name in JURISDICTIONS.items():
        if session.get(JurisdictionRow, code) is None:
            session.add(JurisdictionRow(code=code, name=name))
    for name in REQUIRED_TRADES:
        if session.get(TradeRow, name) is None:
            session.add(TradeRow(name=name, aliases=[]))
    session.flush()
    existing = {
        (row.primary_jurisdiction, row.trade)
        for row in session.scalars(
            select(CoverageRecordRow).where(
                CoverageRecordRow.locality_key == "", CoverageRecordRow.credential_key == ""
            )
        )
    }
    for code in JURISDICTIONS:
        for trade in REQUIRED_TRADES:
            if (code, trade) not in existing:
                session.add(
                    CoverageRecordRow(
                        primary_jurisdiction=code,
                        trade=trade,
                        locality_key="",
                        credential_key="",
                        effective_date_key="current",
                        status=CoverageStatus.NOT_STARTED.value,
                        review_reason=[
                            "Official authority and credential inventory not yet researched"
                        ],
                    )
                )
                created += 1
    return created


def audit_coverage(session: Session) -> dict:
    rows = list(session.scalars(select(CoverageRecordRow)))
    inventory = [r for r in rows if not r.locality_key and not r.credential_key]
    expected = {(code, trade) for code in JURISDICTIONS for trade in REQUIRED_TRADES}
    found = {(r.primary_jurisdiction, r.trade) for r in inventory}
    counts = {
        status.value: sum(r.status == status.value for r in rows) for status in CoverageStatus
    }
    scope_audited = any(
        run.status == "validated"
        and run.primary_inventory_audited
        and run.credential_levels_audited
        and run.locality_expansion_audited
        and run.federal_overlays_audited
        for run in session.scalars(select(NationwideRunRow))
    )
    complete = (
        scope_audited
        and found == expected
        and len(inventory) == len(expected)
        and all(
            r.status
            in (CoverageStatus.VALIDATED.value, CoverageStatus.VALIDATED_NOT_APPLICABLE.value)
            for r in rows
        )
    )
    return {
        "expected_primary_inventories": len(expected),
        "present_primary_inventories": len(found & expected),
        "missing_primary_inventories": len(expected - found),
        "coverage_records": len(rows),
        "status_counts": counts,
        "scope_audited": scope_audited,
        "national_complete": complete,
    }
