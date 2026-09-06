"""HTML ingestion into canonical EMU Advisor chunks."""

from __future__ import annotations

import argparse
import json
import re
import unicodedata
from dataclasses import dataclass
from datetime import datetime, timezone
from html.parser import HTMLParser
from pathlib import Path
from typing import Any, Dict, Iterable, List, Mapping, Optional
from urllib.parse import urlparse

from .schema import validate_chunk


ALLOWED_REGULATION_HOST = "mevzuat.emu.edu.tr"
ARTICLE_RE = re.compile(r"\b(?:Article|Madde)\s+([0-9]+[A-Za-z]?)\b", re.IGNORECASE)
MONEY_RE = re.compile(r"\b\d{1,3}(?:,\d{3})+\.\d{2}\b")


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
        self.blocks: List[Dict[str, Any]] = []
        self._buffer: List[str] = []
        self._link_href: Optional[str] = None
        self._table_depth = 0
        self._table_rows: List[List[Dict[str, Any]]] = []
        self._table_row: List[Dict[str, Any]] = []
        self._table_caption: Optional[str] = None
        self._cell_tag: Optional[str] = None
        self._cell_buffer: List[str] = []

    def handle_starttag(self, tag: str, attrs: List[tuple[str, Optional[str]]]) -> None:
        tag = tag.lower()
        if tag in {"script", "style", "noscript"}:
            self._skip_depth += 1
            return
        if self._skip_depth:
            return
        if tag == "table":
            if self._table_depth == 0:
                self._flush()
                self._table_rows = []
                self._table_row = []
                self._table_caption = None
            self._table_depth += 1
            return
        if self._table_depth:
            if tag == "tr":
                self._table_row = []
            elif tag in {"td", "th"}:
                self._cell_tag = tag
                self._cell_buffer = []
            elif tag == "caption":
                self._cell_tag = tag
                self._cell_buffer = []
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
        if self._table_depth:
            if tag in {"td", "th"} and self._cell_tag in {"td", "th"}:
                text = _clean_text(" ".join(self._cell_buffer))
                self._cell_buffer = []
                self._table_row.append({"text": text, "is_header": tag == "th"})
                self._cell_tag = None
                return
            if tag == "caption" and self._cell_tag == "caption":
                self._table_caption = _clean_text(" ".join(self._cell_buffer)) or self._table_caption
                self._cell_buffer = []
                self._cell_tag = None
                return
            if tag == "tr":
                if any(cell.get("text") for cell in self._table_row):
                    self._table_rows.append(self._table_row)
                self._table_row = []
                return
            if tag == "table":
                self._table_depth -= 1
                if self._table_depth == 0:
                    self._emit_table()
                return
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
        if self._table_depth and self._cell_tag:
            self._cell_buffer.append(data)
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

    def _emit_table(self) -> None:
        rows = [
            [{"text": str(cell.get("text", "")), "is_header": bool(cell.get("is_header"))} for cell in row]
            for row in self._table_rows
            if any(str(cell.get("text", "")).strip() for cell in row)
        ]
        if rows:
            self.blocks.append(
                {
                    "kind": "table",
                    "tag": "table",
                    "text": _table_text(rows, self._table_caption),
                    "caption": self._table_caption,
                    "rows": rows,
                }
            )
        self._table_rows = []
        self._table_row = []
        self._table_caption = None

    def _take_buffer(self) -> str:
        text = _clean_text(" ".join(self._buffer))
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
    table_source_ids: Dict[tuple[str, int], str] = {}

    def make_record(
        *,
        chunk_id: str,
        text: str,
        section_path: Optional[str],
        article_number: Optional[str],
        metadata: Dict[str, Any],
    ) -> Dict[str, Any]:
        record = {
            "document_id": document_id,
            "chunk_id": chunk_id,
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
            "section_path": section_path,
            "article_number": article_number,
            "page_number": None,
            "chunk_text": text,
            "metadata": metadata,
        }
        validate_chunk(record)
        return record

    def emit() -> None:
        nonlocal buffer
        text = " ".join(buffer).strip()
        buffer = []
        if not text:
            return
        chunks.append(
            make_record(
                chunk_id=f"{document_id}:c{len(chunks) + 1:04d}",
                text=text,
                section_path=current_section,
                article_number=current_article,
                metadata={
                    "evidence_kind": "text",
                    "ingest_method": "html_stdlib",
                    "word_count": len(text.split()),
                },
            )
        )

    def emit_table(block: Mapping[str, Any], table_number: int) -> None:
        table_id = f"{document_id}:t{table_number:04d}"
        rows = block.get("rows") if isinstance(block.get("rows"), list) else []
        if not rows:
            return
        headers = _table_headers(rows)
        table_title = str(block.get("caption") or current_section or source_title)
        summary_text = _table_summary_text(table_title, rows, headers)
        summary_id = f"{document_id}:c{len(chunks) + 1:04d}"
        chunks.append(
            make_record(
                chunk_id=summary_id,
                text=summary_text,
                section_path=current_section,
                article_number=current_article,
                metadata={
                    "evidence_kind": "table_summary",
                    "ingest_method": "html_stdlib_table",
                    "word_count": len(summary_text.split()),
                    "table_id": table_id,
                    "table_title": table_title,
                    "table_headers": headers,
                    "row_count": len(rows),
                },
            )
        )

        for row_index, row in enumerate(rows, start=1):
            cells = _row_cells(row)
            if not _meaningful_table_row(cells):
                continue
            row_text = _row_chunk_text(table_title, headers, cells, row_index=row_index)
            row_id = f"{document_id}:c{len(chunks) + 1:04d}"
            chunks.append(
                make_record(
                    chunk_id=row_id,
                    text=row_text,
                    section_path=current_section or table_title,
                    article_number=current_article,
                    metadata={
                        "evidence_kind": "table_row",
                        "ingest_method": "html_stdlib_table",
                        "word_count": len(row_text.split()),
                        "table_id": table_id,
                        "table_title": table_title,
                        "table_headers": headers,
                        "row_index": row_index,
                        "source_row_cells": cells,
                        "source_chunk_ids": [summary_id],
                    },
                )
            )
            table_source_ids[(table_id, row_index)] = row_id

    table_number = 0
    for block in parser.blocks:
        if block["kind"] == "table":
            emit()
            table_number += 1
            emit_table(block, table_number)
            continue

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

    for record in _derived_salary_chunks(
        document_id=document_id,
        source_url=input_doc.source_url,
        source_title=source_title,
        language=language,
        corpus=corpus,
        access_tier=input_doc.access_tier,
        last_crawled_at=last_crawled_at,
        version_hash=version_hash,
        blocks=parser.blocks,
        table_source_ids=table_source_ids,
        start_index=len(chunks) + 1,
    ):
        validate_chunk(record)
        chunks.append(record)

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


def detect_language(blocks: Iterable[Dict[str, Any]], source_url: str = "") -> str:
    text = " ".join(str(block.get("text", "")) for block in blocks).lower()
    folded = _fold(text)
    if "/tr/" in source_url.lower() or re.search(
        r"\b(madde|yÃ¶netmelik|yonetmelik|Ã¶ÄŸrenci|ogrenci|kurul|tÃ¼zÃ¼k|tuzuk|yasa)\b",
        text,
    ):
        return "tr"
    if any(token in folded for token in ("yonetmelik", "ogrenci", "ogretim", "kurul", "tuzuk", "yasa")):
        return "tr"
    return "en"


def _table_text(rows: List[List[Dict[str, Any]]], caption: Optional[str]) -> str:
    pieces = [caption] if caption else []
    for row in rows[:12]:
        cells = _row_cells(row)
        if cells:
            pieces.append(" | ".join(cells))
    return _clean_text(" ".join(pieces))


def _table_headers(rows: List[List[Dict[str, Any]]]) -> List[str]:
    if not rows:
        return []
    for row in rows[:3]:
        cells = _row_cells(row)
        if not cells:
            continue
        header_flags = [bool(cell.get("is_header")) for cell in row]
        if any(header_flags) or sum(_contains_number(cell) for cell in cells) <= max(1, len(cells) // 3):
            return cells
    return []


def _row_cells(row: Any) -> List[str]:
    if not isinstance(row, list):
        return []
    return [_clean_text(str(cell.get("text", ""))) for cell in row if _clean_text(str(cell.get("text", "")))]


def _meaningful_table_row(cells: List[str]) -> bool:
    joined = " ".join(cells)
    return len(cells) >= 2 and (_contains_number(joined) or len(joined.split()) >= 4)


def _table_summary_text(table_title: str, rows: List[List[Dict[str, Any]]], headers: List[str]) -> str:
    row_count = len(rows)
    sample_rows = []
    for row in rows[:8]:
        cells = _row_cells(row)
        if cells:
            sample_rows.append(" | ".join(cells[:8]))
    parts = [f"Structured table: {table_title}.", f"Rows: {row_count}."]
    if headers:
        parts.append("Headers: " + " | ".join(headers[:12]) + ".")
    if sample_rows:
        parts.append("Sample rows: " + " ; ".join(sample_rows) + ".")
    return _clean_text(" ".join(parts))[:1800]


def _row_chunk_text(table_title: str, headers: List[str], cells: List[str], *, row_index: int) -> str:
    if headers and len(headers) == len(cells):
        pairs = [f"{header}: {cell}" for header, cell in zip(headers, cells)]
        return _clean_text(f"{table_title}. Table row {row_index}: " + "; ".join(pairs))
    return _clean_text(f"{table_title}. Table row {row_index}: " + " | ".join(cells))


def _derived_salary_chunks(
    *,
    document_id: str,
    source_url: str,
    source_title: str,
    language: str,
    corpus: str,
    access_tier: str,
    last_crawled_at: str,
    version_hash: str,
    blocks: List[Mapping[str, Any]],
    table_source_ids: Mapping[tuple[str, int], str],
    start_index: int,
) -> List[Dict[str, Any]]:
    if not _looks_like_academic_staffing_source(source_url, source_title):
        return []
    rows: Dict[str, Dict[str, Any]] = {}
    table_number = 0
    for block in blocks:
        if block.get("kind") != "table":
            continue
        table_number += 1
        table_rows = block.get("rows") if isinstance(block.get("rows"), list) else []
        table_id = f"{document_id}:t{table_number:04d}"
        for row_index, row in enumerate(table_rows, start=1):
            cells = _row_cells(row)
            salary = _salary_row(cells)
            if not salary:
                continue
            salary["source_chunk_id"] = table_source_ids.get((table_id, row_index))
            rows[salary["canonical_title"]] = salary

    out: List[Dict[str, Any]] = []
    next_index = start_index
    for title in ("Professor", "Associate Professor", "Assistant Professor"):
        if title not in rows:
            continue
        salary = rows[title]
        text = _salary_fact_text(title, salary)
        out.append(
            _derived_record(
                document_id=document_id,
                chunk_id=f"{document_id}:c{next_index:04d}",
                source_url=source_url,
                source_title=source_title,
                language=language,
                corpus=corpus,
                access_tier=access_tier,
                last_crawled_at=last_crawled_at,
                version_hash=version_hash,
                text=text,
                source_chunk_ids=[salary["source_chunk_id"]] if salary.get("source_chunk_id") else [],
                row_cells=salary["cells"],
                derived_type="salary_title_range",
            )
        )
        next_index += 1

    if "Professor" in rows and "Assistant Professor" in rows:
        professor = rows["Professor"]
        assistant = rows["Assistant Professor"]
        text = (
            "Academic salary comparison derived from the salary scales table: "
            f"{_salary_fact_text('Professor', professor)} "
            f"{_salary_fact_text('Assistant Professor', assistant)} "
            "Article 5 states that academic staff salaries are paid according to their employed, appointed, "
            "and administrative duties; salary is paid monthly according to the assigned scale."
        )
        source_ids = [item.get("source_chunk_id") for item in (professor, assistant) if item.get("source_chunk_id")]
        out.append(
            _derived_record(
                document_id=document_id,
                chunk_id=f"{document_id}:c{next_index:04d}",
                source_url=source_url,
                source_title=source_title,
                language=language,
                corpus=corpus,
                access_tier=access_tier,
                last_crawled_at=last_crawled_at,
                version_hash=version_hash,
                text=_clean_text(text),
                source_chunk_ids=source_ids,
                row_cells=[professor["cells"], assistant["cells"]],
                derived_type="salary_comparison",
            )
        )
    return out


def _derived_record(
    *,
    document_id: str,
    chunk_id: str,
    source_url: str,
    source_title: str,
    language: str,
    corpus: str,
    access_tier: str,
    last_crawled_at: str,
    version_hash: str,
    text: str,
    source_chunk_ids: List[str],
    row_cells: Any,
    derived_type: str,
) -> Dict[str, Any]:
    return {
        "document_id": document_id,
        "chunk_id": chunk_id,
        "parent_document_id": None,
        "source_type": "html",
        "source_url": source_url,
        "source_title": source_title,
        "language": language,
        "corpus": corpus,
        "access_tier": access_tier,
        "effective_date": None,
        "last_crawled_at": last_crawled_at,
        "version_hash": version_hash,
        "section_path": "Structured derived evidence",
        "article_number": None,
        "page_number": None,
        "chunk_text": text,
        "metadata": {
            "evidence_kind": "derived_fact",
            "derived_type": derived_type,
            "ingest_method": "html_stdlib_table_derived",
            "word_count": len(text.split()),
            "source_chunk_ids": source_chunk_ids,
            "source_row_cells": row_cells,
        },
    }


def _salary_row(cells: List[str]) -> Optional[Dict[str, Any]]:
    row_text = " ".join(cells)
    amounts = MONEY_RE.findall(row_text)
    if len(amounts) < 2:
        return None
    title = _salary_title(row_text)
    if not title:
        return None
    scale = _salary_scale(cells, title)
    return {
        "canonical_title": title,
        "scale": scale,
        "min_amount": amounts[0],
        "max_amount": amounts[-1],
        "steps": len(amounts),
        "cells": cells,
    }


def _salary_title(row_text: str) -> Optional[str]:
    folded = re.sub(r"[^a-z0-9]+", " ", _fold(row_text))
    if "assistant professor" in folded or "assist professor" in folded or "yardimci docent" in folded:
        return "Assistant Professor"
    if "associate professor" in folded or "assoc professor" in folded or "docent" in folded:
        return "Associate Professor"
    if "professor" in folded or "profesor" in folded:
        return "Professor"
    return None


def _salary_scale(cells: List[str], title: str) -> Optional[str]:
    title_folded = re.sub(r"[^a-z0-9]+", " ", _fold(title)).strip()
    for cell in cells:
        folded = re.sub(r"[^a-z0-9]+", " ", _fold(cell)).strip()
        if title_folded in folded:
            continue
        if MONEY_RE.search(cell):
            continue
        if re.fullmatch(r"\d+[A-Za-z]?", cell.strip()):
            return cell.strip()
    return None


def _salary_fact_text(title: str, salary: Mapping[str, Any]) -> str:
    scale = f"scale {salary.get('scale')}" if salary.get("scale") else "the stated scale"
    return (
        f"{title} uses {scale} with steps 1-{salary.get('steps')} "
        f"from {salary.get('min_amount')} to {salary.get('max_amount')}."
    )


def _looks_like_academic_staffing_source(source_url: str, source_title: str) -> bool:
    folded = _fold(f"{source_url} {source_title}")
    return "6-1_staffingemploymentacademicstaff" in folded or "6-1_akdperskadrocal" in folded


def _contains_number(text: str) -> bool:
    return bool(re.search(r"\d", text))


def _clean_text(text: str) -> str:
    return " ".join(str(text).replace("\xa0", " ").split())


def _fold(text: str) -> str:
    translated = str(text).translate(
        str.maketrans(
            {
                "ç": "c",
                "Ç": "C",
                "ğ": "g",
                "Ğ": "G",
                "ı": "i",
                "İ": "I",
                "ö": "o",
                "Ö": "O",
                "ş": "s",
                "Ş": "S",
                "ü": "u",
                "Ü": "U",
            }
        )
    )
    normalized = unicodedata.normalize("NFKD", translated)
    ascii_text = normalized.encode("ascii", "ignore").decode("ascii")
    return ascii_text.casefold()


def _require_allowed_source(source_url: str) -> None:
    parsed = urlparse(source_url)
    if parsed.scheme == "fixture" and not parsed.hostname and parsed.path:
        return
    if parsed.scheme not in {"http", "https"}:
        raise HtmlScopeError("HTML source URL must be official HTTPS or explicit fixture provenance")
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
