"""Fetch and retain immutable source bytes with reproducible extracted text."""

from __future__ import annotations

import hashlib
import os
import tempfile
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from urllib.parse import urlsplit
from urllib.robotparser import RobotFileParser

import httpx
import pymupdf as fitz
from bs4 import BeautifulSoup

from trade_research.models import SourceCandidate

USER_AGENT = "TradeCertificationResearch/0.1 (+evidence-first research)"
MAX_BYTES = 25 * 1024 * 1024


class SourceUnavailable(RuntimeError):
    pass


@dataclass(frozen=True)
class RetrievedDocument:
    source_url: str
    resolved_url: str
    authority_tier: int
    source_type: str
    publisher: str | None
    title: str
    mime_type: str
    content_sha256: str
    raw_artifact_path: str
    extracted_text: str
    page_starts: list[int]
    retrieved_at: datetime
    status_code: int
    etag: str | None = None
    last_modified: str | None = None

    def as_state(self) -> dict:
        from dataclasses import asdict

        result = asdict(self)
        result["retrieved_at"] = self.retrieved_at.isoformat()
        return result


def extract_text(raw: bytes, mime_type: str) -> tuple[str, str, list[int]]:
    mime = mime_type.split(";", 1)[0].strip().lower()
    if mime in ("text/html", "application/xhtml+xml"):
        soup = BeautifulSoup(raw, "html.parser")
        title = soup.title.get_text(" ", strip=True) if soup.title else "Untitled HTML"
        for element in soup(["script", "style", "noscript", "svg"]):
            element.decompose()
        return soup.get_text(" ", strip=True), title, [0]
    if mime == "application/pdf" or raw.startswith(b"%PDF-"):
        try:
            pdf = fitz.open(stream=raw, filetype="pdf")
            pages = [page.get_text(sort=True) for page in pdf]
        except Exception as exc:
            raise SourceUnavailable(f"PDF text extraction failed: {exc}") from exc
        starts: list[int] = []
        offset = 0
        for page in pages:
            starts.append(offset)
            offset += len(page) + 2
        return "\n\n".join(pages), "PDF document", starts
    if mime == "text/plain":
        return raw.decode("utf-8", errors="replace"), "Text document", [0]
    raise SourceUnavailable(f"Unsupported source type: {mime or 'missing MIME'}")


def save_raw(raw: bytes, artifact_dir: Path) -> tuple[str, str]:
    digest = hashlib.sha256(raw).hexdigest()
    target = artifact_dir / "objects" / digest[:2] / digest
    target.parent.mkdir(parents=True, exist_ok=True)
    if not target.exists():
        descriptor, temp_path = tempfile.mkstemp(dir=target.parent, prefix=".fetch-")
        try:
            with os.fdopen(descriptor, "wb") as stream:
                stream.write(raw)
                stream.flush()
                os.fsync(stream.fileno())
            os.replace(temp_path, target)
        finally:
            if os.path.exists(temp_path):
                os.unlink(temp_path)
    return digest, str(target)


def robots_allowed(client: httpx.Client, url: str) -> bool:
    parsed = urlsplit(url)
    robots_url = f"{parsed.scheme}://{parsed.netloc}/robots.txt"
    try:
        response = client.get(robots_url)
        if response.status_code == 404:
            return True
        response.raise_for_status()
        parser = RobotFileParser()
        parser.parse(response.text.splitlines())
        return parser.can_fetch(USER_AGENT, url)
    except httpx.HTTPError as exc:
        raise SourceUnavailable(
            f"Could not establish robots policy for {parsed.netloc}: {exc}"
        ) from exc


def fetch_document(
    candidate: SourceCandidate, artifact_dir: Path, client: httpx.Client | None = None
) -> RetrievedDocument:
    url = str(candidate.url)
    if urlsplit(url).scheme != "https":
        raise SourceUnavailable("Official source retrieval requires HTTPS")
    owned_client = client is None
    if owned_client:
        client = httpx.Client(timeout=20, follow_redirects=True, headers={"User-Agent": USER_AGENT})
    assert client is not None
    try:
        if not robots_allowed(client, url):
            raise SourceUnavailable(f"robots.txt disallows retrieval: {url}")
        with client.stream("GET", url) as response:
            response.raise_for_status()
            chunks: list[bytes] = []
            size = 0
            for chunk in response.iter_bytes():
                size += len(chunk)
                if size > MAX_BYTES:
                    raise SourceUnavailable(f"Source exceeds {MAX_BYTES} bytes: {url}")
                chunks.append(chunk)
            raw = b"".join(chunks)
            mime = response.headers.get("content-type", "")
            extracted, title, page_starts = extract_text(raw, mime)
            digest, path = save_raw(raw, artifact_dir)
            return RetrievedDocument(
                source_url=url,
                resolved_url=str(response.url),
                authority_tier=candidate.authority_tier,
                source_type=candidate.source_type,
                publisher=candidate.publisher,
                title=title,
                mime_type=mime,
                content_sha256=digest,
                raw_artifact_path=path,
                extracted_text=extracted,
                page_starts=page_starts,
                retrieved_at=datetime.now(UTC),
                status_code=response.status_code,
                etag=response.headers.get("etag"),
                last_modified=response.headers.get("last-modified"),
            )
    except httpx.HTTPError as exc:
        raise SourceUnavailable(f"Source request failed for {url}: {exc}") from exc
    finally:
        if owned_client:
            client.close()
