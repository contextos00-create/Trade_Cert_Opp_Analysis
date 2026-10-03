from __future__ import annotations

import httpx
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from trade_research.adapters import BraveSearchAdapter
from trade_research.db import Base
from trade_research.models import ResearchRequest
from trade_research.national import NationwideTradeCertificationGraph


def test_national_graph_queues_all_primary_and_federal_work_without_provider(tmp_path, monkeypatch):
    monkeypatch.delenv("TRADE_SEARCH_API_KEY", raising=False)
    engine = create_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(engine)
    graph = NationwideTradeCertificationGraph(sessionmaker(engine), tmp_path)

    first = graph.run(max_jobs=1)
    second = graph.run(max_jobs=1)

    assert first["nationwide_run_id"] == second["nationwide_run_id"]
    assert first["status"] == "blocked_configuration"
    assert first["job_counts"] == {"queued": 394}
    assert first["coverage"]["present_primary_inventories"] == 392
    assert first["coverage"]["present_federal_overlays"] == 2
    assert first["coverage"]["national_complete"] is False


def test_search_results_are_discovery_only_and_restricted_to_government_hosts():
    def respond(request):
        assert "site:gov" not in request.url.params["q"]
        return httpx.Response(
            200,
            json={
                "web": {
                    "results": [
                        {"url": "https://licensing.texas.gov/rules"},
                        {"url": "https://county.example.us/permits"},
                        {"url": "https://exam-prep.example.com/ohio"},
                        {"url": "http://legacy.ohio.gov/page"},
                    ]
                }
            },
        )

    with httpx.Client(transport=httpx.MockTransport(respond)) as client:
        adapter = BraveSearchAdapter(api_key="test-key", client=client)
        sources = adapter.discover(
            ResearchRequest(state="TX", trade="electrical"), ["authority"], 0
        )
    assert len(sources) == 2
    assert all(source.authority_tier == 7 for source in sources)
    assert all(source.source_type == "search_discovery" for source in sources)
