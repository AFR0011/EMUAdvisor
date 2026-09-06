"""PDF ingestion into canonical EMU Advisor chunks."""

from __future__ import annotations

import argparse
import json
import re
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional
from urllib.parse import urlparse

from .html_ingest import ALLOWED_REGULATION_HOST
from .schema import validate_chunk


ARTICLE_RE = re.compile(r"\b(?:Article|Madde)\s+([0-9]+[A-Za-z]?)\b", re.IGNORECASE)


@dataclass(frozen=True)
class PdfDocumentInput:
    pdf_path: Path
    source_url: str
    source_title: str
    language: str
    last_crawled_at: Optional[str] = None
    access_tier: str = "public"


class PdfDependencyError(RuntimeError):
    """Raised when the optional PDF reader dependency is unavailable."""


class PdfScopeError(ValueError):
    """Raised when PDF ingestion receives a source outside V1 scope."""


def ingest_pdf_document(input_doc: PdfDocumentInput, *, max_words: int = 220) -> List[Dict[str, Any]]:
    _require_allowed_pdf_source(input_doc.source_url)
    if input_doc.language not in {"en", "tr"}:
        raise ValueError("PDF language must be 'en' or 'tr'")

    try:
        from pypdf import PdfReader
    except ImportError as exc:
        raise PdfDependencyError("pypdf is required for PDF ingestion") from exc

    pdf_bytes = input_doc.pdf_path.read_bytes()
    version_hash = _stable_hash_bytes(input_doc.source_url, pdf_bytes)
    last_crawled_at = input_doc.last_crawled_at or datetime.now(timezone.utc).isoformat()
    corpus = "regulations_tr" if input_doc.language == "tr" else "regulations_en"
    document_id = _document_id(input_doc.source_url, input_doc.language)

    reader = PdfReader(str(input_doc.pdf_path))
    chunks: List[Dict[str, Any]] = []
    for page_index, page in enumerate(reader.pages, start=1):
        text = " ".join((page.extract_text() or "").split())
        if not text:
            continue
        page_chunks = _split_words(text, max_words=max_words)
        for page_chunk in page_chunks:
            section_path = _section_path(page_chunk, input_doc.language)
            article_number = _article_number(page_chunk)
            chunk_index = len(chunks) + 1
            record = {
                "document_id": document_id,
                "chunk_id": f"{document_id}:p{page_index:04d}:c{chunk_index:04d}",
                "parent_document_id": None,
                "source_type": "pdf",
                "source_url": input_doc.source_url,
                "source_title": input_doc.source_title,
                "language": input_doc.language,
                "corpus": corpus,
                "access_tier": input_doc.access_tier,
                "effective_date": None,
                "last_crawled_at": last_crawled_at,
                "version_hash": version_hash,
                "section_path": section_path,
                "article_number": article_number,
                "page_number": page_index,
                "chunk_text": page_chunk,
                "metadata": {
                    "ingest_method": "pypdf",
                    "page_index": page_index,
                    "word_count": len(page_chunk.split()),
                    "table_text_detected": _looks_like_table(page_chunk),
                },
            }
            validate_chunk(record)
            chunks.append(record)

    return chunks


def _require_allowed_pdf_source(source_url: str) -> None:
    parsed = urlparse(source_url)
    if parsed.scheme == "fixture" and not parsed.hostname and parsed.path.lower().endswith(".pdf"):
        return
    if parsed.scheme not in {"http", "https"}:
        raise PdfScopeError("PDF source URL must be official HTTPS or explicit fixture provenance")
    if parsed.hostname != ALLOWED_REGULATION_HOST:
        raise PdfScopeError(f"source host is outside V1 scope: {parsed.hostname}")
    if not parsed.path.lower().endswith(".pdf"):
        raise PdfScopeError("PDF source URL must end in .pdf")


def _split_words(text: str, *, max_words: int) -> List[str]:
    words = text.split()
    if len(words) <= max_words:
        return [text]
    chunks = []
    for idx in range(0, len(words), max_words):
        chunks.append(" ".join(words[idx : idx + max_words]))
    return chunks


def _section_path(text: str, language: str) -> Optional[str]:
    article = _article_number(text)
    if article:
        return f"Article {article}" if language == "en" else f"Madde {article}"
    heading = text.split(". ", 1)[0].strip()
    if 3 <= len(heading) <= 80 and heading.isupper():
        return heading.title()
    return None


def _article_number(text: str) -> Optional[str]:
    match = ARTICLE_RE.search(text)
    return match.group(1) if match else None


def _looks_like_table(text: str) -> bool:
    return text.count("|") >= 2 or bool(re.search(r"\b[A-Z][A-Za-z ]+\s+\d+(?:\.\d+)?\s+\d+(?:\.\d+)?", text))


def _document_id(source_url: str, language: str) -> str:
    parsed = urlparse(source_url)
    slug = re.sub(r"[^a-zA-Z0-9]+", "-", parsed.path.strip("/")).strip("-").lower()
    return f"{language}:pdf:{slug}:{_stable_hash([source_url])[:10]}"


def _stable_hash(parts: Iterable[str]) -> str:
    import hashlib

    h = hashlib.sha256()
    for part in parts:
        h.update(str(part).encode("utf-8"))
        h.update(b"\0")
    return h.hexdigest()


def _stable_hash_bytes(source_url: str, payload: bytes) -> str:
    import hashlib

    h = hashlib.sha256()
    h.update(source_url.encode("utf-8"))
    h.update(b"\0")
    h.update(payload)
    return h.hexdigest()


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Ingest one official EMU regulation PDF.")
    parser.add_argument("pdf_path", type=Path)
    parser.add_argument("--source-url", required=True)
    parser.add_argument("--source-title", required=True)
    parser.add_argument("--language", choices=("en", "tr"), required=True)
    parser.add_argument("--out", type=Path, required=True)
    return parser


def main(argv: Optional[List[str]] = None) -> int:
    args = build_parser().parse_args(argv)
    records = ingest_pdf_document(
        PdfDocumentInput(
            pdf_path=args.pdf_path,
            source_url=args.source_url,
            source_title=args.source_title,
            language=args.language,
        )
    )
    with args.out.open("w", encoding="utf-8") as handle:
        for record in records:
            handle.write(json.dumps(record, ensure_ascii=False, sort_keys=True) + "\n")
    print(f"wrote {len(records)} canonical chunks to {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
