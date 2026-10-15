"""Typed external contracts. Unsupported material values remain null."""

from __future__ import annotations

from datetime import date, datetime
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, Field, HttpUrl


class RegulationScope(StrEnum):
    STATEWIDE = "statewide"
    LOCAL = "local"
    MIXED = "mixed"
    FEDERAL_OVERLAY = "federal_overlay"
    VERIFIED_NOT_REQUIRED = "verified_not_required"
    UNKNOWN = "unknown"


class CoverageStatus(StrEnum):
    VALIDATED = "validated"
    VALIDATED_NOT_APPLICABLE = "validated_not_applicable"
    PARTIAL_NEEDS_REVIEW = "partial_needs_review"
    BLOCKED_SOURCE = "blocked_source"
    NOT_STARTED = "not_started"


class ResearchStatus(StrEnum):
    VALIDATED = "validated"
    PARTIAL = "partial"
    NEEDS_REVIEW = "needs_review"
    FAILED = "failed"


class ResearchRequest(BaseModel):
    state: str
    trade: str
    credential_level: str | None = None
    locality: str | None = None
    as_of_date: date | None = None
    force_refresh: bool = False


class CoverageRecord(BaseModel):
    primary_jurisdiction: str
    locality: str | None = None
    trade: str
    credential_level: str | None = None
    status: CoverageStatus = CoverageStatus.NOT_STARTED
    research_run_id: str | None = None
    source_count: int = 0
    authoritative_source_count: int = 0
    unresolved_field_count: int = 0
    last_attempted_at: datetime | None = None
    last_validated_at: datetime | None = None
    review_reason: list[str] = Field(default_factory=list)


class Authority(BaseModel):
    name: str
    agency: str | None = None
    division: str | None = None
    role: str
    official_url: HttpUrl | None = None


class EvidenceSpan(BaseModel):
    evidence_id: str
    field_path: str
    asserted_value: Any
    source_id: str
    source_url: HttpUrl
    source_title: str
    publisher: str | None = None
    source_type: str
    authority_tier: int
    quoted_text: str
    page_number: int | None = None
    section: str | None = None
    text_start: int | None = None
    text_end: int | None = None
    retrieved_at: datetime
    published_at: date | None = None
    effective_from: date | None = None
    effective_to: date | None = None
    content_sha256: str


class FieldClaim(BaseModel):
    field_path: str
    value: Any | None = None
    evidence_ids: list[str] = Field(default_factory=list)
    confidence: float | None = None
    status: str = "unknown"  # supported | conflicting | unknown | review_required


class ExamDetails(BaseModel):
    required: bool | None = None
    name: str | None = None
    owner: str | None = None
    administrator: str | None = None
    vendor: str | None = None
    candidate_bulletin_url: HttpUrl | None = None
    number_of_exams: int | None = None
    sections: list[str] = Field(default_factory=list)
    question_count: int | None = None
    time_limit_minutes: int | None = None
    passing_score: str | None = None
    open_book: bool | None = None
    allowed_references: list[str] = Field(default_factory=list)
    code_editions: list[str] = Field(default_factory=list)
    exam_fee: str | None = None


class CertificationRequirement(BaseModel):
    state: str
    state_code: str
    locality: str | None = None
    trade: str
    credential_name: str | None = None
    credential_level: str | None = None
    regulation_scope: RegulationScope = RegulationScope.UNKNOWN
    statewide_license_required: bool | None = None
    regulatory_authorities: list[Authority] = Field(default_factory=list)
    statutory_authority: list[str] = Field(default_factory=list)
    administrative_rules: list[str] = Field(default_factory=list)
    minimum_age: int | None = None
    education_requirements: list[str] = Field(default_factory=list)
    experience_hours: int | None = None
    experience_years: float | None = None
    apprenticeship_requirements: list[str] = Field(default_factory=list)
    alternative_qualification_paths: list[str] = Field(default_factory=list)
    exam: ExamDetails = Field(default_factory=ExamDetails)
    application_url: HttpUrl | None = None
    application_fee: str | None = None
    background_check_required: bool | None = None
    insurance_required: bool | None = None
    bond_required: bool | None = None
    renewal_period: str | None = None
    renewal_fee: str | None = None
    continuing_education_hours: float | None = None
    continuing_education_requirements: list[str] = Field(default_factory=list)
    reciprocity_available: bool | None = None
    reciprocity_states: list[str] = Field(default_factory=list)
    reciprocity_requirements: list[str] = Field(default_factory=list)
    field_claims: list[FieldClaim] = Field(default_factory=list)
    source_evidence: list[EvidenceSpan] = Field(default_factory=list)
    missing_fields: list[str] = Field(default_factory=list)
    unresolved_conflicts: list[dict[str, Any]] = Field(default_factory=list)
    last_verified_at: datetime
    confidence_score: float | None = None
    research_status: ResearchStatus


class SourceCandidate(BaseModel):
    url: HttpUrl
    authority_tier: int = Field(ge=1, le=7)
    source_type: str = "official_page"
    publisher: str | None = None


class CuratedClaim(BaseModel):
    """Human supplied candidate. A matching quote alone does not prove legal meaning."""

    field_path: str
    value: Any
    quoted_text: str
    source_url: HttpUrl
    effective_from: date | None = None
    effective_to: date | None = None


class ResearchResult(BaseModel):
    research_run_id: str
    requirement: CertificationRequirement
    coverage_status: CoverageStatus
    review_reason: list[str] = Field(default_factory=list)
