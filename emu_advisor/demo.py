"""Small built-in demo corpus for local API/UI smoke tests."""

from __future__ import annotations

from typing import Dict, List

from .schema import validate_chunk


def demo_chunks() -> List[Dict[str, object]]:
    records: List[Dict[str, object]] = [
        _chunk(
            "en-attendance:c1",
            "en:html:attendance",
            "Article 1 Attendance Requirement",
            "Students must meet the attendance requirement stated in the official regulation.",
            language="en",
            corpus="regulations_en",
            article="1",
        ),
        _chunk(
            "en-honour:c1",
            "en:html:honour",
            "Article 2 High Honour",
            "High honour is awarded when the cited regulation's CGPA and semester conditions are met.",
            language="en",
            corpus="regulations_en",
            article="2",
        ),
        _chunk(
            "tr-devam:c1",
            "tr:html:devam",
            "Madde 1 Devam Zorunlulugu",
            "Öğrenciler resmi yönetmelikte belirtilen devam zorunluluğuna uymalıdır.",
            language="tr",
            corpus="regulations_tr",
            article="1",
        ),
        _chunk(
            "tr-seref:c1",
            "tr:html:seref",
            "Madde 2 Yüksek Şeref",
            "Yüksek şeref, ilgili yönetmelikte belirtilen not ortalaması ve dönem koşulları sağlandığında verilir.",
            language="tr",
            corpus="regulations_tr",
            article="2",
        ),
    ]
    for record in records:
        validate_chunk(record)
    return records


def _chunk(
    chunk_id: str,
    document_id: str,
    title: str,
    text: str,
    *,
    language: str,
    corpus: str,
    article: str,
) -> Dict[str, object]:
    return {
        "document_id": document_id,
        "chunk_id": chunk_id,
        "parent_document_id": None,
        "source_type": "html",
        "source_url": f"https://mevzuat.emu.edu.tr/content/{language}/{document_id}.htm",
        "source_title": title,
        "language": language,
        "corpus": corpus,
        "access_tier": "public",
        "effective_date": None,
        "last_crawled_at": "2026-05-04T08:00:00Z",
        "version_hash": "demo-" + chunk_id,
        "section_path": title,
        "article_number": article,
        "page_number": None,
        "chunk_text": text,
        "metadata": {"demo": True},
    }
