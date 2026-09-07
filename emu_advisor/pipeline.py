"""Corpus crawl/build pipeline with explicit source provenance."""

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
REDIRECT_CODES = {301, 302, 303, 307, 308}
MAX_REDIRECTS = 5


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
        return not parsed.netloc and bool(parsed.path)
    if parsed.scheme != "https" or parsed.hostname != ALLOWED_HOST:
        return False
    if parsed.username or parsed.password:
        return False
    try:
        return parsed.port in {None, 443}
    except ValueError:
        return False


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

    with httpx.Client(timeout=timeout_s, follow_redirects=False) as client:
        while queue and len(seen) < max_pages:
            url = queue.pop(0)
            if url in seen:
                continue
            seen.add(url)
            fetched_at = datetime.now(timezone.utc).isoformat()
            record: Dict[str, Any] = {"url": _public_source_url(url), "fetched_at": fetched_at}
            try:
                payload, content_type, final_url, redirect_chain = _fetch(url, client, allow_file=allow_file)
                source_url = _public_source_url(final_url)
                raw_path = raw_dir / f"{len(seen):05d}_{_safe_name(url)}"
                if final_url.lower().endswith(".pdf") or "pdf" in content_type.lower():
                    if not include_pdfs:
                        continue
                    pdf_count += 1
                    pdf_path = raw_path.with_suffix(".pdf")
                    pdf_path.write_bytes(payload)
                    pdf_chunks = ingest_pdf_document(
                        PdfDocumentInput(
                            pdf_path=pdf_path,
                            source_url=source_url,
                            source_title=_title_from_url(final_url),
                            language=_language_hint_from_url(final_url) or "en",
                            last_crawled_at=fetched_at,
                        )
                    )
                    _mark_fixture_chunks(pdf_chunks, final_url)
                    chunks.extend(pdf_chunks)
                    record.update({"status": "ok", "content_type": content_type, "chunks": len(pdf_chunks), "source_type": "pdf"})
                else:
                    html = _decode_html(payload, content_type)
                    html_path = raw_path.with_suffix(".html")
                    html_path.write_text(html, encoding="utf-8")
                    html_chunks = ingest_html_document(
                        HtmlDocumentInput(
                            html=html,
                            source_url=source_url,
                            source_title=None,
                            language=_language_hint_from_url(url),
                            last_crawled_at=fetched_at,
                        )
                    )
                    _mark_fixture_chunks(html_chunks, final_url)
                    chunks.extend(html_chunks)
                    record.update({"status": "ok", "content_type": content_type, "chunks": len(html_chunks), "source_type": "html"})
                    for link in discover_links(html, final_url, include_pdfs=include_pdfs, allow_file=allow_file):
                        if link not in seen and link not in queue and len(seen) + len(queue) < max_pages * 3:
                            queue.append(link)
                record.update({"requested_url": _public_source_url(url), "final_url": source_url, "redirect_chain": redirect_chain})
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
        "seeds": [_public_source_url(seed) for seed in seeds],
        "max_pages": max_pages,
        "include_pdfs": include_pdfs,
        "page_count": len(pages),
        "chunk_count": len(chunks),
        "pdf_count": pdf_count,
        "errors": errors,
    }
    (out_dir / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True), encoding="utf-8")
    snapshot = write_snapshot(chunks, out_dir.parent / "snapshots", label="live-corpus")
    try:
        snapshot_pointer = snapshot.relative_to(out_dir.parent).as_posix()
    except ValueError:
        snapshot_pointer = snapshot.name
    (out_dir.parent / "active_snapshot.txt").write_text(snapshot_pointer, encoding="utf-8")
    return BuildResult(out_dir=out_dir, chunk_count=len(chunks), page_count=len(pages), pdf_count=pdf_count, errors=errors)


def _fetch(
    url: str,
    client: httpx.Client,
    *,
    allow_file: bool = False,
) -> tuple[bytes, str, str, List[str]]:
    parsed = urlparse(url)
    if parsed.scheme == "file":
        if not is_allowed_crawl_url(url, allow_file=allow_file):
            raise ValueError("file fixtures require explicit allow_file mode")
        path = Path(url2pathname(parsed.path))
        payload = path.read_bytes()
        content_type = "application/pdf" if path.suffix.lower() == ".pdf" else "text/html"
        return payload, content_type, url, []
    if not is_allowed_crawl_url(url):
        raise ValueError(f"refusing out-of-scope crawl URL: {url}")
    current = normalize_url(url)
    redirects: List[str] = []
    for _ in range(MAX_REDIRECTS + 1):
        if not is_allowed_crawl_url(current):
            raise ValueError(f"refusing out-of-scope redirect URL: {current}")
        response = client.get(current, headers={"User-Agent": "EMUAdvisorDemo/1.0"}, follow_redirects=False)
        response_url = normalize_url(str(response.url))
        if not is_allowed_crawl_url(response_url):
            raise ValueError(f"refusing out-of-scope final response URL: {response_url}")
        if response.status_code not in REDIRECT_CODES:
            response.raise_for_status()
            return response.content, response.headers.get("content-type", ""), response_url, redirects
        location = response.headers.get("location")
        if not location:
            raise ValueError("redirect response is missing Location")
        target = normalize_url(urljoin(response_url, location))
        if not is_allowed_crawl_url(target):
            raise ValueError(f"refusing out-of-scope redirect URL: {target}")
        if target in redirects or target == current:
            raise ValueError("redirect loop detected")
        redirects.append(target)
        current = target
    raise ValueError(f"redirect limit exceeded ({MAX_REDIRECTS})")


def _public_source_url(url: str) -> str:
    parsed = urlparse(url)
    if parsed.scheme == "file":
        return f"fixture:///{Path(parsed.path).name}"
    return normalize_url(url)


def _mark_fixture_chunks(chunks: List[Dict[str, Any]], source_url: str) -> None:
    if urlparse(source_url).scheme != "file":
        return
    for chunk in chunks:
        chunk["metadata"] = {
            **dict(chunk.get("metadata") or {}),
            "fixture": True,
            "official_source": False,
        }


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
