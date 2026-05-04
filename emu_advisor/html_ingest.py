"""HTML ingestion into canonical EMU Advisor chunks."""

from __future__ import annotations

import argparse
import json
import re
from dataclasses import dataclass
from datetime import datetime, timezone
from html.parser import HTMLParser
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional
from urllib.parse import urlparse

from .schema import validate_chunk


ALLOWED_REGULATION_HOST = "mevzuat.emu.edu.tr"
ARTICLE_RE = re.compile(r"\b(?:Article|Madde)\s+([0-9]+[A-Za-z]?)\b", re.IGNORECASE)


@dataclass(frozen=True)
class HtmlDocumentInput:
    html: str
    source_url: str
    source_title: Optional[str] = None
    language: Optional[str] = None
    last_crawled_at: Optional[str] = None
    access_tier: str = "public"


class HtmlScopeError(ValueError):
    """Raised when HTML ingestion receives a source outside V1 scope."""


class _RegulationHtmlParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.title: Optional[str] = None
        self._in_title = False
        self._skip_depth = 0
        self._current_tag: Optional[str] = None
        self.blocks: List[Dict[str, str]] = []
        self._buffer: List[str] = []
        self._link_href: Optional[str] = None

    def handle_starttag(self, tag: str, attrs: List[tuple[str, Optional[str]]]) -> None:
        tag = tag.lower()
        if tag in {"script", "style", "noscript"}:
            self._skip_depth += 1
            return
        if self._skip_depth:
            return
        if tag == "title":
            self._flush()
            self._in_title = True
            self._current_tag = tag
            return
        if tag in {"h1", "h2", "h3", "h4", "p", "li", "td", "th"}:
            self._flush()
            self._current_tag = tag
        if tag == "a":
            attrs_dict = {k.lower(): v for k, v in attrs}
            self._link_href = attrs_dict.get("href")

    def handle_endtag(self, tag: str) -> None:
        tag = tag.lower()
        if tag in {"script", "style", "noscript"} and self._skip_depth:
            self._skip_depth -= 1
            return
        if self._skip_depth:
            return
        if tag == "title":
            text = self._take_buffer()
            if text:
                self.title = text
            self._in_title = False
            self._current_tag = None
            return
        if tag in {"h1", "h2", "h3", "h4", "p", "li", "td", "th"}:
            self._flush()
            self._current_tag = None
        if tag == "a":
            self._link_href = None

    def handle_data(self, data: str) -> None:
        if self._skip_depth:
            return
        if self._in_title or self._current_tag:
            self._buffer.append(data)

    def _flush(self) -> None:
        text = self._take_buffer()
        if not text:
            return
        tag = self._current_tag or "text"
        kind = "heading" if tag in {"h1", "h2", "h3", "h4"} else "text"
        self.blocks.append({"kind": kind, "tag": tag, "text": text})

    def _take_buffer(self) -> str:
        text = " ".join(" ".join(self._buffer).split())
        self._buffer = []
        return text


def ingest_html_document(input_doc: HtmlDocumentInput, *, max_words: int = 220) -> List[Dict[str, Any]]:
    """Convert one HTML document into canonical chunks."""

    _require_allowed_source(input_doc.source_url)
    parser = _RegulationHtmlParser()
    parser.feed(input_doc.html)
    parser.close()

    language = input_doc.language or detect_language(parser.blocks, input_doc.source_url)
    corpus = "regulations_tr" if language == "tr" else "regulations_en"
    source_title = input_doc.source_title or parser.title or _title_from_url(input_doc.source_url)
    last_crawled_at = input_doc.last_crawled_at or datetime.now(timezone.utc).isoformat()
    version_hash = _stable_hash([input_doc.source_url, input_doc.html])
    document_id = _document_id(input_doc.source_url, language)

    chunks: List[Dict[str, Any]] = []
    current_section: Optional[str] = None
    current_article: Optional[str] = None
    buffer: List[str] = []

    def emit() -> None:
        nonlocal buffer
        text = " ".join(buffer).strip()
        buffer = []
        if not text:
            return
        chunk_index = len(chunks) + 1
        record = {
            "document_id": document_id,
            "chunk_id": f"{document_id}:c{chunk_index:04d}",
            "parent_document_id": None,
            "source_type": "html",
            "source_url": input_doc.source_url,
            "source_title": source_title,
            "language": language,
            "corpus": corpus,
            "access_tier": input_doc.access_tier,
            "effective_date": None,
            "last_crawled_at": last_crawled_at,
            "version_hash": version_hash,
            "section_path": current_section,
            "article_number": current_article,
            "page_number": None,
            "chunk_text": text,
            "metadata": {
                "ingest_method": "html_stdlib",
                "word_count": len(text.split()),
            },
        }
        validate_chunk(record)
        chunks.append(record)

    for block in parser.blocks:
        text = block["text"]
        if block["kind"] == "heading":
            emit()
            current_section = text
            article = _article_number(text)
            if article:
                current_article = article
            continue

        article = _article_number(text)
        if article:
            emit()
            current_article = article
            if not current_section:
                current_section = f"Article {article}" if language == "en" else f"Madde {article}"

        prospective = " ".join(buffer + [text])
        if len(prospective.split()) > max_words and buffer:
            emit()
        buffer.append(text)
    emit()

    return chunks


def ingest_html_file(
    path: Path,
    *,
    source_url: str,
    source_title: Optional[str] = None,
    language: Optional[str] = None,
    last_crawled_at: Optional[str] = None,
) -> List[Dict[str, Any]]:
    html = path.read_text(encoding="utf-8")
    return ingest_html_document(
        HtmlDocumentInput(
            html=html,
            source_url=source_url,
            source_title=source_title,
            language=language,
            last_crawled_at=last_crawled_at,
        )
    )


def detect_language(blocks: Iterable[Dict[str, str]], source_url: str = "") -> str:
    text = " ".join(block.get("text", "") for block in blocks).lower()
    if "/tr/" in source_url.lower() or re.search(r"\b(madde|yonetmelik|yönetmelik|ogrenci|öğrenci)\b", text):
        return "tr"
    return "en"


def _require_allowed_source(source_url: str) -> None:
    parsed = urlparse(source_url)
    if parsed.scheme not in {"http", "https"}:
        raise HtmlScopeError("HTML source URL must be http or https")
    if parsed.hostname != ALLOWED_REGULATION_HOST:
        raise HtmlScopeError(f"source host is outside V1 scope: {parsed.hostname}")


def _document_id(source_url: str, language: str) -> str:
    parsed = urlparse(source_url)
    slug = re.sub(r"[^a-zA-Z0-9]+", "-", parsed.path.strip("/")).strip("-").lower()
    if not slug:
        slug = "root"
    return f"{language}:html:{slug}:{_stable_hash([source_url])[:10]}"


def _title_from_url(source_url: str) -> str:
    path = urlparse(source_url).path.rstrip("/")
    leaf = path.rsplit("/", 1)[-1] or "EMU regulation"
    return re.sub(r"[-_]+", " ", leaf.rsplit(".", 1)[0]).strip().title()


def _article_number(text: str) -> Optional[str]:
    match = ARTICLE_RE.search(text)
    return match.group(1) if match else None


def _stable_hash(parts: Iterable[str]) -> str:
    import hashlib

    h = hashlib.sha256()
    for part in parts:
        h.update(str(part).encode("utf-8"))
        h.update(b"\0")
    return h.hexdigest()


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Ingest one official EMU regulation HTML file.")
    parser.add_argument("html_path", type=Path)
    parser.add_argument("--source-url", required=True)
    parser.add_argument("--source-title")
    parser.add_argument("--language", choices=("en", "tr"))
    parser.add_argument("--out", type=Path, required=True)
    return parser


def main(argv: Optional[List[str]] = None) -> int:
    args = build_parser().parse_args(argv)
    records = ingest_html_file(
        args.html_path,
        source_url=args.source_url,
        source_title=args.source_title,
        language=args.language,
    )
    with args.out.open("w", encoding="utf-8") as handle:
        for record in records:
            handle.write(json.dumps(record, ensure_ascii=False, sort_keys=True) + "\n")
    print(f"wrote {len(records)} canonical chunks to {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
