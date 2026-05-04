"""Corpus crawl/build pipeline for presentable demo artifacts."""

from __future__ import annotations

import argparse
import json
import re
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from html.parser import HTMLParser
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional
from urllib.request import url2pathname
from urllib.parse import urldefrag, urljoin, urlparse, urlunparse

import httpx

from .admin import write_snapshot
from .corpus import write_chunks_jsonl
from .html_ingest import HtmlDocumentInput, ingest_html_document
from .pdf_ingest import PdfDocumentInput, ingest_pdf_document
from .schema import validate_chunk


ALLOWED_HOST = "mevzuat.emu.edu.tr"
TRACKING_PARAMS = {"utm_source", "utm_medium", "utm_campaign", "utm_term", "utm_content", "gclid", "fbclid"}


@dataclass(frozen=True)
class BuildResult:
    out_dir: Path
    chunk_count: int
    page_count: int
    pdf_count: int
    errors: int


class LinkParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.links: List[str] = []

    def handle_starttag(self, tag: str, attrs: List[tuple[str, Optional[str]]]) -> None:
        if tag.lower() != "a":
            return
        attrs_dict = {name.lower(): value for name, value in attrs}
        href = attrs_dict.get("href")
        if href:
            self.links.append(href)


def normalize_url(url: str) -> str:
    url, _fragment = urldefrag(url.strip())
    parsed = urlparse(url)
    scheme = (parsed.scheme or "https").lower()
    netloc = parsed.netloc.lower()
    query_pairs = []
    for piece in parsed.query.split("&"):
        if not piece:
            continue
        key = piece.split("=", 1)[0]
        if key not in TRACKING_PARAMS:
            query_pairs.append(piece)
    return urlunparse((scheme, netloc, parsed.path or "/", parsed.params, "&".join(query_pairs), ""))


def is_allowed_crawl_url(url: str, *, allow_file: bool = False) -> bool:
    parsed = urlparse(url)
    if allow_file and parsed.scheme == "file":
        return True
    return parsed.scheme in {"http", "https"} and parsed.hostname == ALLOWED_HOST


def discover_links(html: str, base_url: str, *, include_pdfs: bool, allow_file: bool = False) -> List[str]:
    parser = LinkParser()
    parser.feed(html)
    out: List[str] = []
    for href in parser.links:
        if href.startswith(("mailto:", "javascript:", "#")):
            continue
        absolute = normalize_url(urljoin(base_url, href))
        if not is_allowed_crawl_url(absolute, allow_file=allow_file):
            continue
        if absolute.lower().endswith(".pdf") and not include_pdfs:
            continue
        out.append(absolute)
    return out


def build_corpus(
    *,
    seeds: List[str],
    out_dir: Path,
    max_pages: int = 1000,
    include_pdfs: bool = False,
    delay_s: float = 0.3,
    timeout_s: float = 30.0,
    allow_file: bool = False,
) -> BuildResult:
    out_dir.mkdir(parents=True, exist_ok=True)
    raw_dir = out_dir / "raw"
    raw_dir.mkdir(exist_ok=True)
    queue = [normalize_url(seed) for seed in seeds]
    seen: set[str] = set()
    chunks: List[Dict[str, Any]] = []
    pages: List[Dict[str, Any]] = []
    errors = 0
    pdf_count = 0

    with httpx.Client(timeout=timeout_s, follow_redirects=True) as client:
        while queue and len(seen) < max_pages:
            url = queue.pop(0)
            if url in seen:
                continue
            seen.add(url)
            fetched_at = datetime.now(timezone.utc).isoformat()
            record: Dict[str, Any] = {"url": url, "fetched_at": fetched_at}
            try:
                payload, content_type = _fetch(url, client)
                raw_path = raw_dir / f"{len(seen):05d}_{_safe_name(url)}"
                if url.lower().endswith(".pdf") or "pdf" in content_type.lower():
                    if not include_pdfs:
                        continue
                    pdf_count += 1
                    pdf_path = raw_path.with_suffix(".pdf")
                    pdf_path.write_bytes(payload)
                    pdf_chunks = ingest_pdf_document(
                        PdfDocumentInput(
                            pdf_path=pdf_path,
                            source_url=_public_source_url(url),
                            source_title=_title_from_url(url),
                            language=_language_hint_from_url(url) or "en",
                            last_crawled_at=fetched_at,
                        )
                    )
                    chunks.extend(pdf_chunks)
                    record.update({"status": "ok", "content_type": content_type, "chunks": len(pdf_chunks), "source_type": "pdf"})
                else:
                    html = _decode_html(payload, content_type)
                    html_path = raw_path.with_suffix(".html")
                    html_path.write_text(html, encoding="utf-8")
                    html_chunks = ingest_html_document(
                        HtmlDocumentInput(
                            html=html,
                            source_url=_public_source_url(url),
                            source_title=None,
                            language=_language_hint_from_url(url),
                            last_crawled_at=fetched_at,
                        )
                    )
                    chunks.extend(html_chunks)
                    record.update({"status": "ok", "content_type": content_type, "chunks": len(html_chunks), "source_type": "html"})
                    for link in discover_links(html, url, include_pdfs=include_pdfs, allow_file=allow_file):
                        if link not in seen and link not in queue and len(seen) + len(queue) < max_pages * 3:
                            queue.append(link)
                time.sleep(delay_s)
            except Exception as exc:
                errors += 1
                record.update({"status": "error", "error": str(exc)})
            pages.append(record)

    for chunk in chunks:
        validate_chunk(chunk)
    write_chunks_jsonl(chunks, out_dir / "chunks.jsonl")
    _write_jsonl(pages, out_dir / "crawl_pages.jsonl")
    manifest = {
        "created_at": datetime.now(timezone.utc).isoformat(),
        "seeds": seeds,
        "max_pages": max_pages,
        "include_pdfs": include_pdfs,
        "page_count": len(pages),
        "chunk_count": len(chunks),
        "pdf_count": pdf_count,
        "errors": errors,
    }
    (out_dir / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True), encoding="utf-8")
    snapshot = write_snapshot(chunks, out_dir.parent / "snapshots", label="live-corpus")
    (out_dir.parent / "active_snapshot.txt").write_text(str(snapshot.resolve()), encoding="utf-8")
    return BuildResult(out_dir=out_dir, chunk_count=len(chunks), page_count=len(pages), pdf_count=pdf_count, errors=errors)


def _fetch(url: str, client: httpx.Client) -> tuple[bytes, str]:
    parsed = urlparse(url)
    if parsed.scheme == "file":
        path = Path(url2pathname(parsed.path))
        payload = path.read_bytes()
        content_type = "application/pdf" if path.suffix.lower() == ".pdf" else "text/html"
        return payload, content_type
    if not is_allowed_crawl_url(url):
        raise ValueError(f"refusing out-of-scope crawl URL: {url}")
    response = client.get(url, headers={"User-Agent": "EMUAdvisorDemo/1.0"})
    response.raise_for_status()
    return response.content, response.headers.get("content-type", "")


def _public_source_url(url: str) -> str:
    parsed = urlparse(url)
    if parsed.scheme == "file":
        return f"https://{ALLOWED_HOST}/content/fixture/{Path(parsed.path).name}"
    return url


def _decode_html(payload: bytes, content_type: str) -> str:
    candidates = []
    match = re.search(r"charset=([^;\s]+)", content_type, flags=re.IGNORECASE)
    if match:
        candidates.append(match.group(1).strip("\"'"))
    candidates.extend(["utf-8", "windows-1254", "iso-8859-9", "cp1254", "latin-1"])

    tried: set[str] = set()
    for encoding in candidates:
        lowered = encoding.lower()
        if lowered in tried:
            continue
        tried.add(lowered)
        try:
            return payload.decode(encoding)
        except (LookupError, UnicodeDecodeError):
            continue
    return payload.decode("utf-8", errors="replace")


def _language_hint_from_url(url: str) -> Optional[str]:
    lowered = url.lower()
    if "content-en" in lowered or "/en/" in lowered:
        return "en"
    if "/tr/" in lowered or lowered.endswith("/content.htm"):
        return "tr"
    if re.search(r"(yonetmelik|yönetmelik|ogrenci|öğrenci|kurul|tuzuk|tüzük|yasa)", lowered):
        return "tr"
    return None


def _title_from_url(url: str) -> str:
    leaf = Path(urlparse(url).path).name or "EMU Regulation"
    return leaf.rsplit(".", 1)[0].replace("-", " ").replace("_", " ").title()


def _safe_name(url: str) -> str:
    import re

    return re.sub(r"[^a-zA-Z0-9_.-]+", "-", urlparse(url).path.strip("/") or "root")[:80]


def _write_jsonl(records: Iterable[Dict[str, Any]], path: Path) -> None:
    with path.open("w", encoding="utf-8") as handle:
        for record in records:
            handle.write(json.dumps(record, ensure_ascii=False, sort_keys=True) + "\n")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Build canonical EMU Advisor corpus artifacts.")
    sub = parser.add_subparsers(dest="cmd", required=True)
    build = sub.add_parser("build")
    build.add_argument("--seed", action="append", required=True)
    build.add_argument("--out", type=Path, required=True)
    build.add_argument("--max-pages", type=int, default=1000)
    build.add_argument("--include-pdfs", action="store_true")
    build.add_argument("--delay-s", type=float, default=0.3)
    build.add_argument("--timeout-s", type=float, default=30.0)
    build.add_argument("--allow-file", action="store_true", help="Allow file:// seeds for offline fixture tests.")
    return parser


def main(argv: Optional[List[str]] = None) -> int:
    args = build_parser().parse_args(argv)
    if args.cmd == "build":
        result = build_corpus(
            seeds=args.seed,
            out_dir=args.out,
            max_pages=args.max_pages,
            include_pdfs=args.include_pdfs,
            delay_s=args.delay_s,
            timeout_s=args.timeout_s,
            allow_file=args.allow_file,
        )
        print(json.dumps(result.__dict__ | {"out_dir": str(result.out_dir)}, indent=2, sort_keys=True))
        return 0
    raise ValueError(args.cmd)


if __name__ == "__main__":
    raise SystemExit(main())
