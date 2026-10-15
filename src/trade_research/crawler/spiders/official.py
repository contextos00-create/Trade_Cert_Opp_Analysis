"""Bounded official-source spider. A crawled page is not a validated rule."""

from __future__ import annotations

import json
import os
import re
from datetime import UTC, datetime
from pathlib import Path
from urllib.parse import urlsplit

import scrapy

from trade_research.documents import SourceUnavailable, extract_text, save_raw
from trade_research.registry import normalize_jurisdiction, normalize_trade

RELEVANT = re.compile(
    r"licen[cs]|board|electri|plumb|hvac|refrig|hydron|mechanic|contract|"
    r"apprentic|journey|master|exam|application|renew|fee|reciproc|statut|rule",
    re.IGNORECASE,
)


class OfficialSpider(scrapy.Spider):
    name = "official"

    def __init__(self, targets_file: str, max_pages: int = 8, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.targets_file = Path(targets_file)
        self.max_pages = max(1, min(int(max_pages), 100))
        self.artifact_dir = Path(
            os.environ.get("TRADE_RESEARCH_DATA_DIR", ".trade_research")
        ).resolve()
        self.seen: dict[str, set[str]] = {}

    async def start(self):
        for line_number, line in enumerate(self.targets_file.read_text().splitlines(), start=1):
            if not line.strip():
                continue
            target = json.loads(line)
            code, _ = normalize_jurisdiction(target["jurisdiction"])
            trade = normalize_trade(target["trade"])
            url = target["url"]
            if urlsplit(url).scheme != "https":
                raise ValueError(f"Target {line_number} must use HTTPS")
            key = "|".join(
                (code, trade, target.get("locality") or "", target.get("credential_level") or "")
            )
            self.seen.setdefault(key, set()).add(url)
            yield scrapy.Request(
                url,
                callback=self.parse_page,
                errback=self.failed,
                dont_filter=True,
                meta={
                    "job_key": key,
                    "jurisdiction": code,
                    "trade": trade,
                    "locality": target.get("locality"),
                    "credential_level": target.get("credential_level"),
                    "authority_tier": int(target.get("authority_tier", 7)),
                    "source_type": target.get("source_type", "discovered_page"),
                    "publisher": target.get("publisher"),
                    "source_url": url,
                    "depth": 0,
                },
            )

    def failed(self, failure):
        request = failure.request
        yield {
            "status": "blocked_source",
            "source_url": request.meta["source_url"],
            "jurisdiction": request.meta["jurisdiction"],
            "trade": request.meta["trade"],
            "locality": request.meta["locality"],
            "credential_level": request.meta["credential_level"],
            "error": str(failure.value),
        }

    def parse_page(self, response):
        source_url = response.meta["source_url"]
        if urlsplit(response.url).scheme != "https":
            yield {
                "status": "blocked_source",
                "source_url": source_url,
                "jurisdiction": response.meta["jurisdiction"],
                "trade": response.meta["trade"],
                "error": "Source redirected away from HTTPS",
            }
            return
        digest, path = save_raw(response.body, self.artifact_dir)
        mime_type = response.headers.get(b"Content-Type", b"").decode("latin-1")
        try:
            extracted, title, page_starts = extract_text(response.body, mime_type)
        except SourceUnavailable as exc:
            yield {
                "status": "unsupported_source",
                "source_url": source_url,
                "jurisdiction": response.meta["jurisdiction"],
                "trade": response.meta["trade"],
                "content_sha256": digest,
                "raw_artifact_path": path,
                "error": str(exc),
            }
            return
        yield {
            "status": "retrieved",
            "source_url": source_url,
            "resolved_url": response.url,
            "jurisdiction": response.meta["jurisdiction"],
            "trade": response.meta["trade"],
            "locality": response.meta["locality"],
            "credential_level": response.meta["credential_level"],
            "authority_tier": response.meta["authority_tier"],
            "source_type": response.meta["source_type"],
            "publisher": response.meta["publisher"],
            "title": title,
            "mime_type": mime_type,
            "content_sha256": digest,
            "raw_artifact_path": path,
            "extracted_text": extracted,
            "page_starts": page_starts,
            "retrieved_at": datetime.now(UTC).isoformat(),
            "status_code": response.status,
            "etag": response.headers.get(b"ETag", b"").decode("latin-1") or None,
            "last_modified": response.headers.get(b"Last-Modified", b"").decode("latin-1") or None,
        }
        if response.meta["depth"] >= 2 or not mime_type.lower().startswith("text/html"):
            return
        host = urlsplit(response.url).hostname
        key = response.meta["job_key"]
        seen = self.seen[key]
        for anchor in response.css("a[href]"):
            if len(seen) >= self.max_pages:
                break
            href = anchor.attrib.get("href", "")
            label = anchor.css("::text").getall()
            if not RELEVANT.search(href + " " + " ".join(label)):
                continue
            link = response.urljoin(href)
            parts = urlsplit(link)
            if parts.scheme != "https" or parts.hostname != host or link in seen:
                continue
            seen.add(link)
            yield scrapy.Request(
                link,
                callback=self.parse_page,
                errback=self.failed,
                dont_filter=True,
                meta={
                    **response.meta,
                    "source_url": link,
                    "depth": response.meta["depth"] + 1,
                },
            )
