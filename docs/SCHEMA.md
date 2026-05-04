# Canonical Schema

Last updated: 2026-05-04

Primary source of truth: `EMU_RAG_Current_System_Specs.md`

## Purpose

The canonical schema is the contract between ingestion, indexing, retrieval, citations, and auditability. Pipeline stages may keep temporary fields internally, but handoff records must validate against this schema before they are used for indexing or answer citations.

## Chunk Record

Required fields:

- `document_id`: stable source document identifier.
- `chunk_id`: stable chunk identifier.
- `parent_document_id`: parent document identifier or `null`.
- `source_type`: one of `html`, `pdf`, `docx`, `pptx`, `xlsx`, `other`.
- `source_url`: official source URL or local source path.
- `source_title`: human-readable regulation/source title.
- `language`: `en` or `tr`.
- `corpus`: one of `regulations_en`, `regulations_tr`, `future_programs`, `future_events`, `other`.
- `access_tier`: one of `public`, `staff`, `student`, `faculty`, `department`, `admin`.
- `effective_date`: ISO date string or `null`.
- `last_crawled_at`: ISO datetime string.
- `version_hash`: stable source version hash.
- `section_path`: section/article path string or `null`.
- `article_number`: article number string or `null`.
- `page_number`: PDF page number integer or `null`.
- `chunk_text`: non-empty chunk text.
- `metadata`: object for stage-specific structured metadata.

## Document Record

Document records use the same source metadata fields as chunks, without chunk-specific fields. They are intended for source inventory, snapshot diffing, and audit.

Required fields:

- `document_id`
- `parent_document_id`
- `source_type`
- `source_url`
- `source_title`
- `language`
- `corpus`
- `access_tier`
- `effective_date`
- `last_crawled_at`
- `version_hash`
- `metadata`

## Validation

Validate canonical chunk JSONL:

```powershell
python -m emu_advisor.validate_jsonl tests\fixtures\canonical_chunks.valid.jsonl --kind chunk
```

Validate canonical document JSONL:

```powershell
python -m emu_advisor.validate_jsonl path\to\documents.jsonl --kind document
```

## Legacy Mapping

`emu_advisor.schema.legacy_chunk_to_canonical()` maps old-demo chunk-like records into the canonical chunk shape. When legacy records lack a source hash, the mapper creates a deterministic fallback hash and marks `metadata.legacy_missing_source_hash=true`. This is acceptable for migration fixtures and diagnostics, but production ingestion should use a real source version hash.
