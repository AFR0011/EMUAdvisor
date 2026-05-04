"""Canonical schema validation for EMU Regulation Assistant records.

The root system spec defines the chunk schema as the stable contract between
ingestion, indexing, retrieval, citations, and auditability. This module keeps
that contract dependency-free so every pipeline stage can validate records
without needing the backend stack.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from datetime import date, datetime
from typing import Any, Dict, Iterable, List, Mapping, Optional


SOURCE_TYPES = frozenset({"html", "pdf", "docx", "pptx", "xlsx", "other"})
LANGUAGES = frozenset({"en", "tr"})
CORPORA = frozenset(
    {"regulations_en", "regulations_tr", "future_programs", "future_events", "other"}
)
ACCESS_TIERS = frozenset({"public", "staff", "student", "faculty", "department", "admin"})

DOCUMENT_REQUIRED_FIELDS = (
    "document_id",
    "parent_document_id",
    "source_type",
    "source_url",
    "source_title",
    "language",
    "corpus",
    "access_tier",
    "effective_date",
    "last_crawled_at",
    "version_hash",
    "metadata",
)

CHUNK_REQUIRED_FIELDS = DOCUMENT_REQUIRED_FIELDS + (
    "chunk_id",
    "section_path",
    "article_number",
    "page_number",
    "chunk_text",
)


@dataclass(frozen=True)
class ValidationIssue:
    """A single schema validation issue."""

    field: str
    message: str

    def format(self) -> str:
        return f"{self.field}: {self.message}"


class SchemaValidationError(ValueError):
    """Raised when a record fails canonical schema validation."""

    def __init__(self, issues: Iterable[ValidationIssue]):
        self.issues = list(issues)
        message = "; ".join(issue.format() for issue in self.issues)
        super().__init__(message)


@dataclass(frozen=True)
class SourceMetadata:
    source_type: str
    source_url: str
    source_title: str
    language: str
    corpus: str
    access_tier: str
    effective_date: Optional[str]
    last_crawled_at: str
    version_hash: str


@dataclass(frozen=True)
class CanonicalDocument:
    document_id: str
    parent_document_id: Optional[str]
    source: SourceMetadata
    metadata: Dict[str, Any]


@dataclass(frozen=True)
class CanonicalChunk:
    document_id: str
    chunk_id: str
    parent_document_id: Optional[str]
    source: SourceMetadata
    section_path: Optional[str]
    article_number: Optional[str]
    page_number: Optional[int]
    chunk_text: str
    metadata: Dict[str, Any]


def document_issues(record: Mapping[str, Any]) -> List[ValidationIssue]:
    issues = _base_issues(record, DOCUMENT_REQUIRED_FIELDS)
    _validate_document_id(record, issues)
    return issues


def chunk_issues(record: Mapping[str, Any]) -> List[ValidationIssue]:
    issues = _base_issues(record, CHUNK_REQUIRED_FIELDS)
    _validate_document_id(record, issues)
    _require_non_empty_str(record, "chunk_id", issues)
    _require_nullable_str(record, "section_path", issues)
    _require_nullable_str(record, "article_number", issues)
    _require_nullable_int(record, "page_number", issues)
    _require_non_empty_str(record, "chunk_text", issues)
    return issues


def validate_document(record: Mapping[str, Any]) -> CanonicalDocument:
    issues = document_issues(record)
    if issues:
        raise SchemaValidationError(issues)

    source = _source_from_record(record)
    return CanonicalDocument(
        document_id=str(record["document_id"]),
        parent_document_id=_nullable_str_value(record["parent_document_id"]),
        source=source,
        metadata=dict(record["metadata"]),
    )


def validate_chunk(record: Mapping[str, Any]) -> CanonicalChunk:
    issues = chunk_issues(record)
    if issues:
        raise SchemaValidationError(issues)

    source = _source_from_record(record)
    return CanonicalChunk(
        document_id=str(record["document_id"]),
        chunk_id=str(record["chunk_id"]),
        parent_document_id=_nullable_str_value(record["parent_document_id"]),
        source=source,
        section_path=_nullable_str_value(record["section_path"]),
        article_number=_nullable_str_value(record["article_number"]),
        page_number=record["page_number"],
        chunk_text=str(record["chunk_text"]),
        metadata=dict(record["metadata"]),
    )


def legacy_chunk_to_canonical(
    raw: Mapping[str, Any],
    *,
    last_crawled_at: str,
    source_type: str = "html",
    access_tier: str = "public",
    corpus: Optional[str] = None,
) -> Dict[str, Any]:
    """Map an old-demo hit/chunk-like record into the canonical chunk shape.

    Legacy artifacts often lack source version hashes and crawl timestamps. The
    caller must provide `last_crawled_at`; this mapper uses a deterministic
    fallback hash when no source hash exists and marks that in metadata.
    """

    text = _first_present(raw, "chunk_text", "text", "chunk", "content")
    if text is None:
        text = ""
    text = str(text)

    document_id = _first_present(raw, "document_id", "doc_id", "doc_code", "doc")
    if document_id is None or str(document_id).strip() == "":
        document_id = _stable_id("legacy-doc", text)
    document_id = str(document_id)

    chunk_id = _first_present(raw, "chunk_id", "id")
    if chunk_id is None or str(chunk_id).strip() == "":
        chunk_id = _stable_id(document_id, text)
    chunk_id = str(chunk_id)

    language = _first_present(raw, "language", "lang")
    language = str(language or "").strip().lower()
    if corpus is None:
        corpus = "regulations_tr" if language == "tr" else "regulations_en"

    source_url = str(_first_present(raw, "source_url", "url") or "")
    source_title = str(
        _first_present(raw, "source_title", "title", "doc_title", "doc_code", "doc_id")
        or document_id
    )

    version_hash = _first_present(raw, "version_hash", "source_hash")
    used_fallback_hash = version_hash is None or str(version_hash).strip() == ""
    if used_fallback_hash:
        version_hash = _stable_hash([source_url, source_title, text])

    section_path = _first_present(raw, "section_path", "section")
    if isinstance(section_path, list):
        section_path = " > ".join(str(part) for part in section_path if str(part).strip())

    metadata: Dict[str, Any] = {}
    raw_metadata = raw.get("metadata")
    if isinstance(raw_metadata, Mapping):
        metadata.update(dict(raw_metadata))
    metadata.update(
        {
            "legacy_source": True,
            "legacy_missing_source_hash": used_fallback_hash,
        }
    )

    record = {
        "document_id": document_id,
        "chunk_id": chunk_id,
        "parent_document_id": _first_present(raw, "parent_document_id"),
        "source_type": source_type,
        "source_url": source_url,
        "source_title": source_title,
        "language": language,
        "corpus": corpus,
        "access_tier": access_tier,
        "effective_date": _first_present(raw, "effective_date"),
        "last_crawled_at": last_crawled_at,
        "version_hash": str(version_hash),
        "section_path": section_path,
        "article_number": _first_present(raw, "article_number", "article"),
        "page_number": _first_present(raw, "page_number", "page"),
        "chunk_text": text,
        "metadata": metadata,
    }
    validate_chunk(record)
    return record


def _base_issues(record: Mapping[str, Any], required_fields: Iterable[str]) -> List[ValidationIssue]:
    issues: List[ValidationIssue] = []
    for field in required_fields:
        if field not in record:
            issues.append(ValidationIssue(field, "missing required field"))

    _require_enum(record, "source_type", SOURCE_TYPES, issues)
    _require_non_empty_str(record, "source_url", issues)
    _require_non_empty_str(record, "source_title", issues)
    _require_enum(record, "language", LANGUAGES, issues)
    _require_enum(record, "corpus", CORPORA, issues)
    _require_enum(record, "access_tier", ACCESS_TIERS, issues)
    _require_nullable_date(record, "effective_date", issues)
    _require_datetime(record, "last_crawled_at", issues)
    _require_non_empty_str(record, "version_hash", issues)
    _require_dict(record, "metadata", issues)
    return issues


def _validate_document_id(record: Mapping[str, Any], issues: List[ValidationIssue]) -> None:
    _require_non_empty_str(record, "document_id", issues)
    _require_nullable_str(record, "parent_document_id", issues)


def _require_non_empty_str(
    record: Mapping[str, Any], field: str, issues: List[ValidationIssue]
) -> None:
    if field not in record:
        return
    value = record[field]
    if not isinstance(value, str) or value.strip() == "":
        issues.append(ValidationIssue(field, "must be a non-empty string"))


def _require_nullable_str(
    record: Mapping[str, Any], field: str, issues: List[ValidationIssue]
) -> None:
    if field not in record:
        return
    value = record[field]
    if value is not None and not isinstance(value, str):
        issues.append(ValidationIssue(field, "must be a string or null"))


def _require_nullable_int(
    record: Mapping[str, Any], field: str, issues: List[ValidationIssue]
) -> None:
    if field not in record:
        return
    value = record[field]
    if value is not None and not isinstance(value, int):
        issues.append(ValidationIssue(field, "must be an integer or null"))


def _require_enum(
    record: Mapping[str, Any], field: str, allowed: Iterable[str], issues: List[ValidationIssue]
) -> None:
    if field not in record:
        return
    value = record[field]
    if not isinstance(value, str) or value not in allowed:
        allowed_text = ", ".join(sorted(allowed))
        issues.append(ValidationIssue(field, f"must be one of: {allowed_text}"))


def _require_nullable_date(
    record: Mapping[str, Any], field: str, issues: List[ValidationIssue]
) -> None:
    if field not in record:
        return
    value = record[field]
    if value is None:
        return
    if not isinstance(value, str):
        issues.append(ValidationIssue(field, "must be an ISO date string or null"))
        return
    try:
        date.fromisoformat(value)
    except ValueError:
        issues.append(ValidationIssue(field, "must be an ISO date string or null"))


def _require_datetime(record: Mapping[str, Any], field: str, issues: List[ValidationIssue]) -> None:
    if field not in record:
        return
    value = record[field]
    if not isinstance(value, str) or value.strip() == "":
        issues.append(ValidationIssue(field, "must be an ISO datetime string"))
        return
    try:
        datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        issues.append(ValidationIssue(field, "must be an ISO datetime string"))


def _require_dict(record: Mapping[str, Any], field: str, issues: List[ValidationIssue]) -> None:
    if field not in record:
        return
    if not isinstance(record[field], dict):
        issues.append(ValidationIssue(field, "must be an object"))


def _source_from_record(record: Mapping[str, Any]) -> SourceMetadata:
    return SourceMetadata(
        source_type=str(record["source_type"]),
        source_url=str(record["source_url"]),
        source_title=str(record["source_title"]),
        language=str(record["language"]),
        corpus=str(record["corpus"]),
        access_tier=str(record["access_tier"]),
        effective_date=_nullable_str_value(record["effective_date"]),
        last_crawled_at=str(record["last_crawled_at"]),
        version_hash=str(record["version_hash"]),
    )


def _nullable_str_value(value: Any) -> Optional[str]:
    if value is None:
        return None
    return str(value)


def _first_present(record: Mapping[str, Any], *fields: str) -> Any:
    for field in fields:
        if field in record:
            return record[field]
    return None


def _stable_id(prefix: str, text: str) -> str:
    return f"{prefix}:{_stable_hash([text])[:16]}"


def _stable_hash(parts: Iterable[str]) -> str:
    h = hashlib.sha256()
    for part in parts:
        h.update(str(part).encode("utf-8"))
        h.update(b"\0")
    return h.hexdigest()
