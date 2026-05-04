"""Citation and traceability helpers."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Iterable, List, Mapping


@dataclass(frozen=True)
class Citation:
    chunk_id: str
    document_id: str
    source_type: str
    source_title: str
    source_url: str
    language: str
    section_path: str | None
    article_number: str | None
    page_number: int | None
    version_hash: str
    last_crawled_at: str

    def label(self) -> str:
        pieces = [self.source_title]
        if self.article_number:
            pieces.append(f"Article {self.article_number}" if self.language == "en" else f"Madde {self.article_number}")
        elif self.section_path:
            pieces.append(self.section_path)
        if self.source_type == "pdf" and self.page_number is not None:
            pieces.append(f"p. {self.page_number}")
        pieces.append(self.source_url)
        return " | ".join(pieces)

    def as_dict(self) -> Dict[str, Any]:
        return {
            "chunk_id": self.chunk_id,
            "document_id": self.document_id,
            "source_type": self.source_type,
            "source_title": self.source_title,
            "source_url": self.source_url,
            "language": self.language,
            "section_path": self.section_path,
            "article_number": self.article_number,
            "page_number": self.page_number,
            "version_hash": self.version_hash,
            "last_crawled_at": self.last_crawled_at,
            "label": self.label(),
        }


def citation_from_chunk(chunk: Mapping[str, Any]) -> Citation:
    return Citation(
        chunk_id=str(chunk["chunk_id"]),
        document_id=str(chunk["document_id"]),
        source_type=str(chunk["source_type"]),
        source_title=str(chunk["source_title"]),
        source_url=str(chunk["source_url"]),
        language=str(chunk["language"]),
        section_path=chunk.get("section_path"),
        article_number=chunk.get("article_number"),
        page_number=chunk.get("page_number"),
        version_hash=str(chunk["version_hash"]),
        last_crawled_at=str(chunk["last_crawled_at"]),
    )


def unique_citations(chunks: Iterable[Mapping[str, Any]], *, limit: int = 8) -> List[Citation]:
    seen = set()
    citations: List[Citation] = []
    for chunk in chunks:
        citation = citation_from_chunk(chunk)
        key = citation.chunk_id
        if key in seen:
            continue
        seen.add(key)
        citations.append(citation)
        if len(citations) >= limit:
            break
    return citations
