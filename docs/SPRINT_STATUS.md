# Sprint Status

Last updated: 2026-05-05

This records implementation status for the 24-48 hour sprint plan. `Implemented` means local code paths and tests exist. The presentable-demo pass now also has a live official-corpus crawl, assistant-curated 60-case candidate metrics, and a 50-case hard regression set for table/broad-query failures.

| Sprint | Status | Evidence |
|---|---|---|
| 0 Repo ownership | Implemented | Root repo is primary; `.old/` is ignored legacy archive. |
| 1 Canonical schema | Implemented | `emu_advisor/schema.py`, JSONL validator, fixtures, tests. |
| 2 HTML ingestion | Implemented | `emu_advisor/html_ingest.py` emits canonical HTML chunks with traceability, table summaries, row chunks, and derived salary facts. |
| 3 PDF ingestion | Implemented | `emu_advisor/pdf_ingest.py` extracts text/page metadata via local `pypdf`. |
| 4 Language/scope routing | Implemented | `emu_advisor/routing.py` keeps EN/TR corpora separate by default. |
| 5 Evaluation set v0 | Implemented | `eval_sets/v1_gold.jsonl` now contains 60 assistant-curated EN/TR cases pending human review. |
| 6 Multilingual embedding replacement | Implemented baseline | `emu_advisor/embeddings.py` defaults to local multilingual hash baseline and supports optional Ollama `qwen3-embedding:4b`. |
| 7 Qdrant foundation | Implemented + embedded validation | `emu_advisor/store.py` provides a Qdrant adapter and local fallback; `emu_advisor/index.py` built the 8,714-chunk embedded Qdrant index at `artifacts/qdrant/latest`. |
| 8 Hybrid retrieval | Implemented | `emu_advisor/retrieval.py` provides lexical+dense RRF retrieval with route filters. |
| 9 Operating modes | Implemented | `emu_advisor/modes.py` defines cheap/balanced/expensive full-pipeline presets. |
| 10 Answerability/conflict | Implemented | `emu_advisor/answer.py` gates answer/refuse/clarify/conflict before generation. |
| 11 Citations/traceability | Implemented | `emu_advisor/citations.py` maps answers to chunk/source/version/page metadata. |
| 12 Streaming/fallback | Implemented | `progressive_answer_events()` yields extractive answer before optional generation. |
| 13 Admin snapshots | Implemented | `emu_advisor/admin.py` stages, diffs, activates, and exports snapshots. |
| 14 UI/API | Implemented demo | `emu_advisor/server.py` plus `static/` EMU-branded demo UI with corpus, metrics, and local LLM status cards. |
| 15 Privacy logging | Implemented | `emu_advisor/audit_log.py` hashes session IDs and logs query diagnostics. |
| 16 Load simulation | Implemented | `emu_advisor/load_test.py` simulates 50 active sessions in tests. |
| 17 Release candidate | Implemented demo | `docs/RELEASE_CANDIDATE.md` records live demo status, commands, measured metrics, and gaps. |
| 18 Real-corpus demo metrics | Implemented | `emu_advisor/pipeline.py`, `emu_advisor/metrics.py`, ignored `artifacts/demo_corpus/latest`, and ignored `artifacts/metrics/latest`. |
| 19 Evaluation-first hardening | Implemented candidate pass | 60-case candidate set, failure analysis, demo README/snapshot, LLM status checks, retrieval scoring hardening, Qdrant backend envs. |
| 20 Structured evidence hardening | Implemented regression pass | Table-aware ingestion, derived salary facts, scholarship topic bundles, cross-corpus diversification, `eval_sets/v1_hard.jsonl`, and refreshed metrics. |
| 21 Demo split and mode benchmark foundation | Implemented | `/` simple chatbot, `/admin` diagnostics console, sanitized `/chat`, `eval_sets/emu_gold_seed.jsonl`, `docs/eval_spec.md`, and `--all-modes` metrics comparison. |

## Validation Boundary

Validated locally:

- Unit tests for schema, ingestion, pipeline, routing, retrieval, answer behavior, metrics, admin workflow, API, logging, and load simulation.
- Evaluation gold file schema and categories.
- FastAPI import and test-client smoke.
- Live official crawl: 123 pages, 22 PDFs, 8,714 canonical chunks, 4 crawl errors.
- Structured evidence chunks: 493 table summaries, 7,601 table rows, 8 derived salary facts.
- Live assistant-curated candidate metrics: top-5 retrieval 100%, response accuracy 100%, rejection accuracy 100%, clarification accuracy 100%, citation coverage 100%, extractive p50 674 ms / p95 1,267 ms.
- Hard regression metrics: top-5 retrieval 100%, response accuracy 100%, rejection accuracy 100%, citation coverage 100%, extractive p50 468 ms / p95 2,867 ms.
- Bounded generated metrics with Ollama `qwen3:8b`: model detected, but 2-second smoke generation timed out; generated metrics marked unavailable and extractive fallback preserved.
- Embedded local Qdrant index build: 8,714 chunks, 256 dimensions, collection `emu_regulations`.
- Simple/admin UI split and sanitized chat endpoint have unit/API coverage.
- Provisional 50-case gold seed validates as source-binding pending rather than adjudicated gold.

Not validated:

- Docker/live Qdrant service build/run.
- Human-reviewed 50-60 question gold set.
- Human-reviewed provisional gold-seed source/chunk bindings.
- Human-rated generated-answer quality; generated mode is implemented but currently timed out under the bounded 2-second smoke metric.
- Campus deployment constraints.
