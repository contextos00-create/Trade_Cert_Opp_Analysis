"""Restartable national queue, Scrapy crawl, and review-first child research graph."""

from __future__ import annotations

import json
import os
import subprocess
import sys
from collections import Counter, defaultdict
from collections.abc import Callable
from datetime import timedelta
from pathlib import Path
from typing import TypedDict

from langgraph.graph import END, START, StateGraph
from sqlalchemy import select
from sqlalchemy.orm import Session

from trade_research.adapters import BraveSearchAdapter, OpenAIClaimExtractor, ProviderUnavailable
from trade_research.db import (
    CoverageRecordRow,
    NationalJobRow,
    NationwideRunRow,
    audit_coverage,
    new_id,
    seed_national_jobs,
    utcnow,
)
from trade_research.graph import ResearchPipeline
from trade_research.models import ResearchRequest, SourceCandidate
from trade_research.registry import normalize_jurisdiction, normalize_trade


class NationalState(TypedDict, total=False):
    run_id: str
    resume: bool
    targets_file: str | None
    max_jobs: int
    max_pages: int
    job_ids: list[str]
    targets: list[dict]
    crawl_items: list[dict]
    errors: list[str]
    result: dict


def _job_key(code: str, trade: str, locality: str | None, credential: str | None) -> tuple:
    return code, trade, locality or "", credential or ""


def _crawl_document(item: dict) -> dict:
    keys = (
        "source_url",
        "resolved_url",
        "authority_tier",
        "source_type",
        "publisher",
        "title",
        "mime_type",
        "content_sha256",
        "raw_artifact_path",
        "extracted_text",
        "page_starts",
        "retrieved_at",
        "status_code",
        "etag",
        "last_modified",
    )
    return {key: item.get(key) for key in keys}


class NationwideTradeCertificationGraph:
    def __init__(self, session_factory: Callable[[], Session], artifact_dir: Path):
        self.session_factory = session_factory
        self.artifact_dir = artifact_dir.resolve()
        self.project_root = Path(__file__).resolve().parents[2]

    def _seed(self, state: NationalState) -> dict:
        with self.session_factory() as session:
            run = None
            if state.get("resume", True):
                run = session.scalar(
                    select(NationwideRunRow)
                    .where(
                        NationwideRunRow.manifest == "us-56",
                        NationwideRunRow.status != "validated",
                    )
                    .order_by(NationwideRunRow.started_at.desc())
                )
            if run is None:
                run = NationwideRunRow(
                    id=new_id(),
                    manifest="us-56",
                    status="running",
                )
                session.add(run)
                session.flush()
            seed_national_jobs(session, run.id)
            session.commit()
            return {"run_id": run.id, "errors": []}

    def _select(self, state: NationalState) -> dict:
        target_map: dict[tuple, list[dict]] = defaultdict(list)
        if state.get("targets_file"):
            for line in Path(state["targets_file"]).read_text().splitlines():
                if not line.strip():
                    continue
                target = json.loads(line)
                code, _ = normalize_jurisdiction(target["jurisdiction"])
                trade = normalize_trade(target["trade"])
                candidate = SourceCandidate(
                    url=target["url"],
                    authority_tier=int(target.get("authority_tier", 7)),
                    source_type=target.get("source_type", "manual_discovery"),
                    publisher=target.get("publisher"),
                )
                normalized = {
                    **candidate.model_dump(mode="json"),
                    "jurisdiction": code,
                    "trade": trade,
                    "locality": target.get("locality"),
                    "credential_level": target.get("credential_level"),
                }
                target_map[
                    _job_key(code, trade, target.get("locality"), target.get("credential_level"))
                ].append(normalized)
            if not target_map:
                raise ValueError("The targets file contains no official HTTPS sources")
        elif not os.environ.get("TRADE_SEARCH_API_KEY"):
            return {
                "job_ids": [],
                "targets": [],
                "errors": [
                    "National discovery needs TRADE_SEARCH_API_KEY or an official targets file"
                ],
            }
        with self.session_factory() as session:
            stale_before = utcnow() - timedelta(minutes=30)
            status_choices = ["queued", "blocked_source"] if target_map else ["queued"]
            jobs = list(
                session.scalars(
                    select(NationalJobRow)
                    .where(
                        NationalJobRow.nationwide_run_id == state["run_id"],
                        (NationalJobRow.status.in_(status_choices))
                        | (
                            (NationalJobRow.status == "running")
                            & (NationalJobRow.last_attempted_at < stale_before)
                        ),
                    )
                    .order_by(NationalJobRow.jurisdiction_code, NationalJobRow.trade)
                    .with_for_update(skip_locked=True)
                )
            )
            selected = []
            for job in jobs:
                if len(selected) >= state["max_jobs"]:
                    break
                key = _job_key(
                    job.jurisdiction_code, job.trade, job.locality_key, job.credential_key
                )
                if target_map and key not in target_map:
                    continue
                selected.append(job)
                job.status = "running"
                job.attempts += 1
                job.last_attempted_at = utcnow()
            session.commit()
            ids = [job.id for job in selected]
            targets = [
                target
                for job in selected
                for target in target_map.get(
                    _job_key(
                        job.jurisdiction_code, job.trade, job.locality_key, job.credential_key
                    ),
                    [],
                )
            ]
        return {"job_ids": ids, "targets": targets, "errors": []}

    def _discover(self, state: NationalState) -> dict:
        if state["targets"] or not state["job_ids"]:
            return {}
        targets = []
        errors = list(state["errors"])
        try:
            adapter = BraveSearchAdapter()
        except ProviderUnavailable as exc:
            return {"errors": errors + [str(exc)]}
        try:
            with self.session_factory() as session:
                jobs = [session.get(NationalJobRow, ident) for ident in state["job_ids"]]
            for job in jobs:
                request = ResearchRequest(
                    state=job.jurisdiction_code,
                    trade=job.trade,
                    locality=job.locality_key or None,
                    credential_level=job.credential_key or None,
                )
                try:
                    candidates = adapter.discover(request, ["authority", "credential"], 0)
                except ProviderUnavailable as exc:
                    errors.append(f"{job.jurisdiction_code}/{job.trade}: {exc}")
                    continue
                for candidate in candidates:
                    targets.append(
                        {
                            **candidate.model_dump(mode="json"),
                            "jurisdiction": job.jurisdiction_code,
                            "trade": job.trade,
                            "locality": job.locality_key or None,
                            "credential_level": job.credential_key or None,
                        }
                    )
        finally:
            adapter.close()
        return {"targets": targets, "errors": errors}

    def _crawl(self, state: NationalState) -> dict:
        if not state["targets"]:
            return {"crawl_items": []}
        run_dir = self.artifact_dir / "nationwide" / state["run_id"]
        run_dir.mkdir(parents=True, exist_ok=True)
        targets_path = run_dir / "targets.jsonl"
        output_path = run_dir / "crawl.jsonl"
        targets_path.write_text("".join(json.dumps(x) + "\n" for x in state["targets"]))
        env = {**os.environ, "TRADE_RESEARCH_DATA_DIR": str(self.artifact_dir)}
        command = [
            sys.executable,
            "-m",
            "scrapy",
            "crawl",
            "official",
            "-a",
            f"targets_file={targets_path}",
            "-a",
            f"max_pages={state['max_pages']}",
            "-O",
            str(output_path),
        ]
        try:
            completed = subprocess.run(
                command,
                cwd=self.project_root,
                env=env,
                capture_output=True,
                text=True,
                timeout=1800,
                check=False,
            )
        except subprocess.TimeoutExpired:
            return {
                "crawl_items": [],
                "errors": state["errors"] + ["Scrapy crawl timed out after 30 minutes"],
            }
        if completed.returncode != 0:
            return {
                "crawl_items": [],
                "errors": state["errors"]
                + [f"Scrapy exited {completed.returncode}: {completed.stderr[-800:]}"],
            }
        items = [json.loads(line) for line in output_path.read_text().splitlines() if line]
        return {"crawl_items": items}

    def _research(self, state: NationalState) -> dict:
        by_key: dict[tuple, list[dict]] = defaultdict(list)
        for item in state.get("crawl_items", []):
            by_key[
                _job_key(
                    item["jurisdiction"],
                    item["trade"],
                    item.get("locality"),
                    item.get("credential_level"),
                )
            ].append(item)
        extractor = None
        if os.environ.get("TRADE_LLM_API_KEY"):
            try:
                extractor = OpenAIClaimExtractor()
            except ProviderUnavailable:
                pass
        pipeline = ResearchPipeline(
            self.session_factory,
            self.artifact_dir,
            claim_extractor=extractor,
        )
        errors = list(state["errors"])
        for ident in state["job_ids"]:
            with self.session_factory() as session:
                job = session.get(NationalJobRow, ident)
                key = _job_key(
                    job.jurisdiction_code, job.trade, job.locality_key, job.credential_key
                )
                items = by_key.get(key, [])
                docs = [
                    _crawl_document(item) for item in items if item.get("status") == "retrieved"
                ]
                failures = [
                    item.get("error", item["status"])
                    for item in items
                    if item.get("status") != "retrieved"
                ]
                if not docs:
                    reason = "; ".join(failures) or "No official source was retrieved"
                    job.status = "blocked_source"
                    job.last_error = reason[:2000]
                    coverage = session.scalar(
                        select(CoverageRecordRow).where(
                            CoverageRecordRow.primary_jurisdiction == job.jurisdiction_code,
                            CoverageRecordRow.locality_key == job.locality_key,
                            CoverageRecordRow.trade == job.trade,
                            CoverageRecordRow.credential_key == job.credential_key,
                            CoverageRecordRow.effective_date_key == "current",
                        )
                    )
                    if coverage is not None:
                        coverage.status = "blocked_source"
                        coverage.review_reason = [reason]
                        coverage.last_attempted_at = utcnow()
                    session.commit()
                    continue
                request = ResearchRequest(
                    state=job.jurisdiction_code,
                    trade=job.trade,
                    locality=job.locality_key or None,
                    credential_level=job.credential_key or None,
                )
            try:
                result = pipeline.run(request, preloaded_documents=docs)
            except Exception as exc:  # noqa: BLE001 - isolate child failure; keep national run resumable
                with self.session_factory() as session:
                    job = session.get(NationalJobRow, ident)
                    job.status = "blocked_source"
                    job.last_error = f"Research pipeline failed: {type(exc).__name__}: {exc}"[:2000]
                    session.commit()
                errors.append(f"{key}: research pipeline failed: {type(exc).__name__}")
                continue
            with self.session_factory() as session:
                job = session.get(NationalJobRow, ident)
                job.status = "needs_review"
                job.research_run_id = result.research_run_id
                job.last_error = "; ".join(result.review_reason)[:2000]
                session.commit()
        return {"errors": errors}

    def _audit(self, state: NationalState) -> dict:
        with self.session_factory() as session:
            run = session.get(NationwideRunRow, state["run_id"])
            jobs = list(
                session.scalars(
                    select(NationalJobRow).where(NationalJobRow.nationwide_run_id == run.id)
                )
            )
            counts = dict(Counter(job.status for job in jobs))
            coverage = audit_coverage(session)
            if not state["job_ids"] and state["errors"]:
                run.status = "blocked_configuration"
            elif coverage["national_complete"]:
                run.status = "validated"
                run.completed_at = utcnow()
            elif counts.get("queued"):
                run.status = "running"
            else:
                run.status = "needs_review"
            result = {
                "nationwide_run_id": run.id,
                "manifest": run.manifest,
                "status": run.status,
                "job_counts": counts,
                "coverage": coverage,
                "errors": state["errors"],
            }
            session.commit()
        return {"result": result}

    def build_graph(self):
        graph = StateGraph(NationalState)
        for name in ("seed", "select", "discover", "crawl", "research", "audit"):
            graph.add_node(name, getattr(self, f"_{name}"))
        graph.add_edge(START, "seed")
        graph.add_edge("seed", "select")
        graph.add_conditional_edges(
            "select",
            lambda state: "discover" if state["job_ids"] else "audit",
            {"discover": "discover", "audit": "audit"},
        )
        graph.add_edge("discover", "crawl")
        graph.add_edge("crawl", "research")
        graph.add_edge("research", "audit")
        graph.add_edge("audit", END)
        return graph.compile()

    def run(
        self,
        *,
        resume: bool = True,
        targets_file: Path | None = None,
        max_jobs: int = 20,
        max_pages: int = 8,
    ) -> dict:
        state = self.build_graph().invoke(
            {
                "resume": resume,
                "targets_file": str(targets_file.resolve()) if targets_file else None,
                "max_jobs": max(1, min(max_jobs, 394)),
                "max_pages": max(1, min(max_pages, 100)),
            }
        )
        return state["result"]
