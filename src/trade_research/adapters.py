"""Optional provider adapters. Search results only discover candidate source URLs."""

from __future__ import annotations

import os
from urllib.parse import urlsplit

import httpx
from langchain_openai import ChatOpenAI
from pydantic import BaseModel, Field

from trade_research.documents import RetrievedDocument
from trade_research.models import CuratedClaim, ResearchRequest, SourceCandidate
from trade_research.registry import normalize_jurisdiction, normalize_trade


class ProviderUnavailable(RuntimeError):
    pass


class BraveSearchAdapter:
    """Discover official-looking URLs; never upgrade a search result into evidence."""

    endpoint = "https://api.search.brave.com/res/v1/web/search"

    def __init__(self, api_key: str | None = None, client: httpx.Client | None = None):
        self.api_key = api_key or os.environ.get("TRADE_SEARCH_API_KEY")
        if not self.api_key:
            raise ProviderUnavailable("TRADE_SEARCH_API_KEY is required for national discovery")
        self.client = client or httpx.Client(timeout=20)
        self.owns_client = client is None

    def close(self) -> None:
        if self.owns_client:
            self.client.close()

    def discover(
        self, request: ResearchRequest, missing_fields: list[str], round_number: int
    ) -> list[SourceCandidate]:
        _, state_name = normalize_jurisdiction(request.state)
        trade = normalize_trade(request.trade).replace("_", " ")
        level = request.credential_level or "licensing authority credential types"
        topics = [
            "board licensing law",
            "license levels journeyman master contractor",
            "application exam candidate bulletin",
            "local government delegated licensing",
        ]
        topic = topics[min(round_number, len(topics) - 1)]
        query = f"{state_name} {trade} {level} {topic} official government"
        try:
            response = self.client.get(
                self.endpoint,
                params={"q": query, "count": 10},
                headers={"X-Subscription-Token": self.api_key, "Accept": "application/json"},
            )
            response.raise_for_status()
            results = response.json().get("web", {}).get("results", [])
        except (httpx.HTTPError, ValueError) as exc:
            raise ProviderUnavailable(f"Search discovery failed: {exc}") from exc
        candidates = []
        seen = set()
        for item in results:
            url = item.get("url", "")
            parts = urlsplit(url)
            host = (parts.hostname or "").lower()
            if parts.scheme != "https" or not host.endswith((".gov", ".us")):
                continue
            if url in seen:
                continue
            seen.add(url)
            candidates.append(
                SourceCandidate(
                    url=url,
                    authority_tier=7,
                    source_type="search_discovery",
                )
            )
        return candidates


class CandidateBatch(BaseModel):
    claims: list[CuratedClaim] = Field(default_factory=list)


class OpenAIClaimExtractor:
    """Produce candidate claims; deterministic citation checks still gate persistence."""

    def __init__(self, api_key: str | None = None, model: str | None = None, llm=None):
        key = api_key or os.environ.get("TRADE_LLM_API_KEY")
        if llm is None and not key:
            raise ProviderUnavailable("TRADE_LLM_API_KEY is required for model extraction")
        if llm is None:
            llm = ChatOpenAI(
                api_key=key,
                model=model or os.environ.get("TRADE_LLM_MODEL", "gpt-4.1-mini"),
                temperature=0,
            )
        self.llm = llm.with_structured_output(CandidateBatch)

    def extract(self, request: ResearchRequest, document: RetrievedDocument) -> list[CuratedClaim]:
        if not document.extracted_text.strip():
            return []
        if len(document.extracted_text) > 96_000:
            raise ProviderUnavailable(
                f"Document {document.source_url} exceeds the 96,000-character extraction cap"
            )
        system = (
            "Extract candidate licensing facts only for the requested jurisdiction, trade, "
            "credential, locality, and date. Return exact contiguous quotations copied from "
            "the source text and their field paths. Omit unsupported facts. Never infer that "
            "a license is not required from silence. Do not transfer contractor requirements "
            "to workers or one exam to another. Search output is not evidence. "
            "Return at most 20 claims; human review is still required."
        )
        user = (
            f"Request: {request.model_dump_json()}\n"
            f"Source URL: {document.source_url}\n"
            f"Source title: {document.title}\n"
            f"Extracted text:\n{document.extracted_text}"
        )
        try:
            batch = self.llm.invoke([("system", system), ("human", user)])
        except Exception as exc:
            raise ProviderUnavailable(f"Model extraction failed: {type(exc).__name__}") from exc
        result = CandidateBatch.model_validate(batch)
        return [claim for claim in result.claims if str(claim.source_url) == document.source_url]
