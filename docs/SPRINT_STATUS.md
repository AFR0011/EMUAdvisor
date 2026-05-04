# Sprint Status

Last updated: 2026-05-04

This records implementation status for the 24-48 hour sprint plan. `Implemented` means local code paths and tests exist. It does not mean real EMU corpus quality has been validated.

| Sprint | Status | Evidence |
|---|---|---|
| 0 Repo ownership | Implemented | Root repo is primary; `.old/` is ignored legacy archive. |
| 1 Canonical schema | Implemented | `emu_advisor/schema.py`, JSONL validator, fixtures, tests. |
| 2 HTML ingestion | Implemented | `emu_advisor/html_ingest.py` emits canonical HTML chunks with traceability. |
| 3 PDF ingestion | Implemented | `emu_advisor/pdf_ingest.py` extracts text/page metadata via local `pypdf`. |
| 4 Language/scope routing | Implemented | `emu_advisor/routing.py` keeps EN/TR corpora separate by default. |
| 5 Evaluation set v0 | Implemented | `eval_sets/v1_seed.jsonl` and `emu_advisor/evaluation.py`. |
| 6 Multilingual embedding replacement | Implemented baseline | `emu_advisor/embeddings.py` defaults to local multilingual hash baseline, not English E5. |
| 7 Qdrant foundation | Implemented offline fallback | `emu_advisor/store.py` provides Qdrant-compatible payload/vector semantics; real `qdrant_client` is not installed. |
| 8 Hybrid retrieval | Implemented | `emu_advisor/retrieval.py` provides lexical+dense RRF retrieval with route filters. |
| 9 Operating modes | Implemented | `emu_advisor/modes.py` defines cheap/balanced/expensive full-pipeline presets. |
| 10 Answerability/conflict | Implemented | `emu_advisor/answer.py` gates answer/refuse/clarify/conflict before generation. |
| 11 Citations/traceability | Implemented | `emu_advisor/citations.py` maps answers to chunk/source/version/page metadata. |
| 12 Streaming/fallback | Implemented | `progressive_answer_events()` yields extractive answer before optional generation. |
| 13 Admin snapshots | Implemented | `emu_advisor/admin.py` stages, diffs, activates, and exports snapshots. |
| 14 UI/API | Implemented demo | `emu_advisor/server.py` plus `static/` EMU-branded demo UI. |
| 15 Privacy logging | Implemented | `emu_advisor/audit_log.py` hashes session IDs and logs query diagnostics. |
| 16 Load simulation | Implemented | `emu_advisor/load_test.py` simulates 50 active sessions in tests. |
| 17 Release candidate | Implemented scaffold | `docs/RELEASE_CANDIDATE.md` records demo status, commands, and gaps. |

## Validation Boundary

Validated locally:

- Unit tests for schema, ingestion, routing, retrieval, answer behavior, admin workflow, API, logging, and load simulation.
- Evaluation seed file schema and categories.
- FastAPI import and test-client smoke.

Not validated:

- Live crawl of `mevzuat.emu.edu.tr`.
- Production Qdrant server.
- Reviewed 50-60 question gold set.
- Real local LLM quality or GPU latency.
- Campus deployment constraints.
