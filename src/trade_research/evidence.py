"""Deterministic checks for source bytes, quoted passages, and time windows."""

from __future__ import annotations

import hashlib
from bisect import bisect_right
from datetime import date
from pathlib import Path
from uuid import uuid4

from trade_research.documents import RetrievedDocument
from trade_research.models import CuratedClaim, EvidenceSpan


class EvidenceError(ValueError):
    pass


def verify_document(document: RetrievedDocument) -> None:
    raw = Path(document.raw_artifact_path).read_bytes()
    if hashlib.sha256(raw).hexdigest() != document.content_sha256:
        raise EvidenceError(f"Stored source bytes do not match SHA-256: {document.source_url}")


def evidence_for_claim(
    claim: CuratedClaim, document: RetrievedDocument, as_of_date: date | None = None
) -> EvidenceSpan:
    verify_document(document)
    if str(claim.source_url).rstrip("/") != document.source_url.rstrip("/"):
        raise EvidenceError("Claim source URL does not match the fetched source")
    if as_of_date and (
        (claim.effective_from and as_of_date < claim.effective_from)
        or (claim.effective_to and as_of_date > claim.effective_to)
    ):
        raise EvidenceError("Claim effective dates exclude the requested date")
    if not claim.quoted_text.strip():
        raise EvidenceError("An evidence quote cannot be empty")
    first = document.extracted_text.find(claim.quoted_text)
    if first < 0:
        raise EvidenceError("Quoted passage was not found in extracted source text")
    page = bisect_right(document.page_starts, first) if document.page_starts else None
    return EvidenceSpan(
        evidence_id=str(uuid4()),
        field_path=claim.field_path,
        asserted_value=claim.value,
        source_id=document.content_sha256,
        source_url=document.source_url,
        source_title=document.title,
        publisher=document.publisher,
        source_type=document.source_type,
        authority_tier=document.authority_tier,
        quoted_text=claim.quoted_text,
        page_number=page if document.mime_type.startswith("application/pdf") else None,
        text_start=first,
        text_end=first + len(claim.quoted_text),
        retrieved_at=document.retrieved_at,
        effective_from=claim.effective_from,
        effective_to=claim.effective_to,
        content_sha256=document.content_sha256,
    )
