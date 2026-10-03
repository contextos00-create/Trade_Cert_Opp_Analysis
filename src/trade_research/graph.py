"""Bounded LangGraph pipeline. Candidate claims require a separate review decision."""

from __future__ import annotations

from collections import defaultdict
from collections.abc import Callable
from datetime import UTC, datetime
from pathlib import Path
from typing import Protocol, TypedDict
from uuid import uuid4

from langgraph.graph import END, START, StateGraph
from sqlalchemy.orm import Session

from trade_research.documents import RetrievedDocument, SourceUnavailable, fetch_document
from trade_research.evidence import EvidenceError, evidence_for_claim
from trade_research.models import (
    CertificationRequirement,
    CoverageStatus,
    CuratedClaim,
    FieldClaim,
    ResearchRequest,
    ResearchResult,
    ResearchStatus,
    SourceCandidate,
)
from trade_research.registry import normalize_jurisdiction, normalize_trade
from trade_research.repository import save_research_result

GRAPH_VERSION = "0.1.0"
CORE_FIELDS = ("regulation_scope", "statewide_license_required", "exam.required")
EXCLUDED_CLAIM_FIELDS = {
    "state",
    "state_code",
    "locality",
    "trade",
    "field_claims",
    "source_evidence",
    "missing_fields",
    "unresolved_conflicts",
    "last_verified_at",
    "confidence_score",
    "research_status",
}


class SearchAdapter(Protocol):
    def discover(
        self, request: ResearchRequest, missing_fields: list[str], round_number: int
    ) -> list[SourceCandidate]: ...


class ResearchState(TypedDict, total=False):
    request: dict
    research_run_id: str
    state_code: str
    state_name: str
    trade: str
    seed_sources: list[dict]
    curated_claims: list[dict]
    pending_sources: list[dict]
    seen_urls: list[str]
    documents: list[dict]
    failed_sources: list[dict]
    errors: list[str]
    missing_fields: list[str]
    field_claims: list[dict]
    evidence: list[dict]
    conflicts: list[dict]
    research_iterations: int
    result: dict


def _document_from_state(item: dict) -> RetrievedDocument:
    return RetrievedDocument(
        **{**item, "retrieved_at": datetime.fromisoformat(item["retrieved_at"])}
    )


def _claim_path_allowed(path: str) -> bool:
    if path.startswith("exam."):
        from trade_research.models import ExamDetails

        return path.split(".", 1)[1] in ExamDetails.model_fields
    return path in CertificationRequirement.model_fields and path not in EXCLUDED_CLAIM_FIELDS


class ResearchPipeline:
    def __init__(
        self,
        session_factory: Callable[[], Session],
        artifact_dir: Path,
        search_adapter: SearchAdapter | None = None,
        retriever: Callable[[SourceCandidate, Path], RetrievedDocument] = fetch_document,
    ):
        self.session_factory = session_factory
        self.artifact_dir = artifact_dir
        self.search_adapter = search_adapter
        self.retriever = retriever

    def _normalize(self, state: ResearchState) -> dict:
        request = ResearchRequest.model_validate(state["request"])
        code, name = normalize_jurisdiction(request.state)
        trade = normalize_trade(request.trade)
        return {
            "state_code": code,
            "state_name": name,
            "trade": trade,
            "seen_urls": [],
            "documents": [],
            "failed_sources": [],
            "errors": [],
            "missing_fields": list(CORE_FIELDS),
            "research_iterations": 0,
        }

    def _discover(self, state: ResearchState) -> dict:
        round_number = state["research_iterations"]
        candidates = []
        if round_number == 0:
            candidates.extend(SourceCandidate.model_validate(x) for x in state["seed_sources"])
        if self.search_adapter is not None:
            candidates.extend(
                self.search_adapter.discover(
                    ResearchRequest.model_validate(state["request"]),
                    state["missing_fields"],
                    round_number,
                )
            )
        seen = set(state["seen_urls"])
        fresh = []
        for candidate in candidates:
            url = str(candidate.url)
            if url not in seen:
                fresh.append(candidate.model_dump(mode="json"))
                seen.add(url)
        return {
            "pending_sources": fresh,
            "seen_urls": sorted(seen),
            "research_iterations": round_number + 1,
        }

    @staticmethod
    def _after_discovery(state: ResearchState) -> str:
        return "fetch" if state["pending_sources"] else "persist"

    def _fetch(self, state: ResearchState) -> dict:
        documents = list(state["documents"])
        failed_sources = list(state["failed_sources"])
        errors = list(state["errors"])
        for item in state["pending_sources"]:
            candidate = SourceCandidate.model_validate(item)
            try:
                documents.append(self.retriever(candidate, self.artifact_dir).as_state())
            except (SourceUnavailable, OSError) as exc:
                errors.append(str(exc))
                failed_sources.append(
                    {
                        "source": item,
                        "error": str(exc),
                        "retrieved_at": datetime.now(UTC).isoformat(),
                    }
                )
        return {
            "documents": documents,
            "failed_sources": failed_sources,
            "errors": errors,
            "pending_sources": [],
        }

    def _validate(self, state: ResearchState) -> dict:
        request = ResearchRequest.model_validate(state["request"])
        documents = {
            _document_from_state(item).source_url: _document_from_state(item)
            for item in state["documents"]
        }
        evidence = []
        claims = []
        errors = list(state["errors"])
        values = defaultdict(list)
        for item in state["curated_claims"]:
            claim = CuratedClaim.model_validate(item)
            if not _claim_path_allowed(claim.field_path):
                errors.append(f"Unsupported claim field: {claim.field_path}")
                continue
            document = documents.get(str(claim.source_url))
            if document is None:
                errors.append(f"Claim source has not been retrieved: {claim.source_url}")
                continue
            try:
                span = evidence_for_claim(claim, document, request.as_of_date)
            except EvidenceError as exc:
                errors.append(f"{claim.field_path}: {exc}")
                continue
            evidence.append(span.model_dump(mode="json"))
            claims.append(
                FieldClaim(
                    field_path=claim.field_path,
                    value=claim.value,
                    evidence_ids=[span.evidence_id],
                    status="review_required",
                ).model_dump(mode="json")
            )
            values[claim.field_path].append(claim.value)
        conflicts = [
            {"field_path": path, "competing_values": distinct, "review_status": "open"}
            for path, items in values.items()
            if len(distinct := list(dict.fromkeys(map(repr, items)))) > 1
        ]
        return {
            "evidence": evidence,
            "field_claims": claims,
            "conflicts": conflicts,
            "errors": list(dict.fromkeys(errors)),
            "missing_fields": list(CORE_FIELDS),
        }

    @staticmethod
    def _after_validation(state: ResearchState) -> str:
        # One initial discovery plus at most three targeted follow-up rounds.
        return "discover" if state["research_iterations"] < 4 else "persist"

    def _persist(self, state: ResearchState) -> dict:
        request = ResearchRequest.model_validate(state["request"])
        errors = state["errors"]
        documents = state["documents"]
        claims = [FieldClaim.model_validate(x) for x in state.get("field_claims", [])]
        reasons = [
            "Official authority, credential scope, and material claims require human verification"
        ]
        if claims:
            reasons.append("Passage and hash checks passed; semantic support has not been reviewed")
        reasons.extend(errors)
        if state.get("conflicts"):
            reasons.append("Candidate claims conflict")
        status = ResearchStatus.NEEDS_REVIEW if claims else ResearchStatus.PARTIAL
        coverage_status = CoverageStatus.PARTIAL_NEEDS_REVIEW
        if errors and not documents and state["seed_sources"]:
            status = ResearchStatus.FAILED
            coverage_status = CoverageStatus.BLOCKED_SOURCE
        requirement = CertificationRequirement(
            state=state["state_name"],
            state_code=state["state_code"],
            locality=request.locality,
            trade=state["trade"],
            credential_level=request.credential_level,
            field_claims=claims,
            source_evidence=state.get("evidence", []),
            missing_fields=state.get("missing_fields", list(CORE_FIELDS)),
            unresolved_conflicts=state.get("conflicts", []),
            last_verified_at=datetime.now(UTC),
            research_status=status,
        )
        result = ResearchResult(
            research_run_id=state["research_run_id"],
            requirement=requirement,
            coverage_status=coverage_status,
            review_reason=reasons,
        )
        with self.session_factory() as session:
            save_research_result(
                session,
                result,
                request.model_dump(mode="json"),
                documents,
                state["failed_sources"],
                errors,
                GRAPH_VERSION,
            )
        return {"result": result.model_dump(mode="json")}

    def build_graph(self, checkpointer=None):
        graph = StateGraph(ResearchState)
        graph.add_node("normalize", self._normalize)
        graph.add_node("discover", self._discover)
        graph.add_node("fetch", self._fetch)
        graph.add_node("validate", self._validate)
        graph.add_node("persist", self._persist)
        graph.add_edge(START, "normalize")
        graph.add_edge("normalize", "discover")
        graph.add_conditional_edges(
            "discover",
            self._after_discovery,
            {
                "fetch": "fetch",
                "persist": "persist",
            },
        )
        graph.add_edge("fetch", "validate")
        graph.add_conditional_edges(
            "validate",
            self._after_validation,
            {
                "discover": "discover",
                "persist": "persist",
            },
        )
        graph.add_edge("persist", END)
        return graph.compile(checkpointer=checkpointer)

    def run(
        self,
        request: ResearchRequest,
        sources: list[SourceCandidate] | None = None,
        claims: list[CuratedClaim] | None = None,
        checkpointer=None,
        run_id: str | None = None,
    ) -> ResearchResult:
        run_id = run_id or str(uuid4())
        state = self.build_graph(checkpointer).invoke(
            {
                "request": request.model_dump(mode="json"),
                "research_run_id": run_id,
                "seed_sources": [x.model_dump(mode="json") for x in (sources or [])],
                "curated_claims": [x.model_dump(mode="json") for x in (claims or [])],
            },
            config={"configurable": {"thread_id": run_id}},
        )
        return ResearchResult.model_validate(state["result"])
