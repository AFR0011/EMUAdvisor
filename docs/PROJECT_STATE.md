# Project State

Last updated: 2026-05-04

## Current Snapshot

- The current product source of truth is `EMU_RAG_Current_System_Specs.md`.
- The current deliverable is a demo-first, local-only EMU Regulation Assistant, not a full production release.
- The root workspace is now the primary Git repository on branch `main`.
- `.old/` is an ignored local archive of the previous NLPCrawler demo.
- The old demo archive includes a Python RAG pipeline, FastAPI backend, static UI, Ollama integration, and an evaluation harness.
- Live crawl, canonical chunk, and metrics artifacts have been generated under ignored `artifacts/`.
- `docs/SPRINT_PLAN.md` now sequences implementation and testing into 24-48 hour sprints.
- Sprint 1 has added the root canonical schema package, JSONL validator, schema docs, fixtures, and unit tests.
- Sprints 2-17 now have root implementation scaffolds, local tests, and a real-corpus demo validation pass; see `docs/SPRINT_STATUS.md`.

## Active Objective

Harden and productize the V1 EMU Regulation Assistant around the current spec:

- Narrow V1 to official EMU regulations and official linked PDFs.
- Preserve separate English and Turkish corpora.
- Replace the English-focused embedding default.
- Move toward a Qdrant-backed hybrid retrieval stack.
- Add canonical source/chunk metadata and traceability.
- Establish realistic verification with bilingual gold questions.

## Current Implementation Evidence

- Old-demo pipeline scripts live under `.old/` as numbered Python files from crawl through reranking.
- `.old/backend/server.py` exposes FastAPI endpoints for `/`, `/ask`, `/fetch`, `/fetch/status`, and `/whoami`.
- `.old/backend/rag_adapter.py` handles retrieval invocation, clarification, confidence gating, extraction answers, and optional Ollama generation.
- `.old/backend/config.json` points both English and Turkish index paths to `mevzuat_crawl/index_v4_dedup` and enables Ollama model `qwen2.5:14b-instruct`.
- `.old/requirements-full.txt` documents the full old-demo Python dependency surface and intentionally leaves `torch` unpinned.
- `emu_advisor/schema.py` defines canonical document/chunk validation and legacy chunk mapping.
- `emu_advisor/validate_jsonl.py` validates canonical document or chunk JSONL files.
- `emu_advisor/html_ingest.py` and `emu_advisor/pdf_ingest.py` emit canonical chunks from official-scope HTML/PDF sources.
- `emu_advisor/routing.py` handles language/corpus/scope routing.
- `emu_advisor/evaluation.py` validates evaluation sets and computes top-k retrieval metrics.
- `emu_advisor/pipeline.py` performs official-host crawl/build into canonical ignored artifacts.
- `emu_advisor/metrics.py` runs evaluation and writes dashboard-ready JSON, Markdown, per-case CSV, and human-review CSV.
- `emu_advisor/corpus.py` loads `artifacts/demo_corpus/latest/chunks.jsonl` when present and falls back to fixture chunks otherwise.
- `emu_advisor/generation.py` provides local Ollama `qwen3:8b` generation with extractive fallback on failure.
- `emu_advisor/embeddings.py`, `store.py`, `retrieval.py`, and `modes.py` provide local retrieval infrastructure.
- `emu_advisor/answer.py` and `citations.py` implement deterministic answerability, refusal, conflict, fallback, and citation behavior.
- `emu_advisor/admin.py` provides snapshot/diff/activation workflow.
- `emu_advisor/server.py`, `static/`, `audit_log.py`, and `load_test.py` provide demo API/UI, privacy logging, and load simulation.
- `tests/fixtures/` contains valid and invalid canonical chunk fixtures.

## Verification State

- Sprint 0 repo ownership baseline is complete: root is the primary Git repository and `.old/` is ignored local legacy reference code.
- Root documentation file listing was verified.
- Legacy `.old/` Python syntax scan passed for 15 files.
- Legacy `.old/backend` import smoke failed because `.old/backend/rag_adapter.py` imports `key` from `anyio`, which is not available in the installed AnyIO package.
- Root schema unit tests passed: `python -m unittest discover -s tests`.
- Full root test suite passed: 38 tests.
- Canonical valid chunk fixture passed JSONL validation.
- Canonical invalid chunk fixture failed validation as expected with field-level errors.
- Root package/test syntax scan passed for 29 files.
- Gold evaluation set validation passed for 30 cases across 10 categories.
- FastAPI app import smoke passed: app title `EMU Regulation Assistant`.
- Live crawl completed from `https://mevzuat.emu.edu.tr/content.htm` and `https://mevzuat.emu.edu.tr/Content-en.htm`: 123 pages, 22 PDFs, 2,496 chunks, 4 crawl errors.
- Active corpus status: 119 sources/documents, 1,226 English chunks, 1,270 Turkish chunks, 2,381 HTML chunks, 115 PDF chunks.
- Live metrics over `eval_sets/v1_gold.jsonl` are presentable for the current seed set: top-5 retrieval 95.83%, response accuracy 83.33%, rejection accuracy 100%, clarification accuracy 100%, citation coverage 100%, extractive latency p50 84 ms / p95 145 ms.
- Generated mode was attempted with local Ollama model `qwen3:8b`; all 23 attempted answerable generations timed out in this environment, so generated latency remains unavailable and extractive fallback is the verified path.
- No campus/server deployment environment is documented yet.

## Known Risks

- The old demo still defaults to `intfloat/e5-base-v2` in multiple places, but active root code now supports hash fallback plus optional local Ollama embeddings.
- Qdrant is the target direction in the spec, but the old demo currently uses BM25 plus FAISS/numpy dense search.
- Canonical document/chunk schema is implemented and integrated into local ingestion, pipeline build, corpus loading, store, retrieval, metrics, and citation tests.
- PDF handling requirements are stronger than the evidence visible in the old demo code and docs.
- The `.old/` archive contains `__pycache__` files, but `.old/` is ignored by the root repo.
- The `.old/` backend currently fails import in this environment because of an existing AnyIO import issue.
- Generated mode depends on an available local Ollama `qwen3:8b`; this environment timed out during bounded generation metrics.

## Next Actions

1. Review `artifacts/metrics/latest/human_review.csv` and replace placeholder expected sources/keywords with reviewed labels.
2. Expand `eval_sets/v1_gold.jsonl` from 30 seed cases to the reviewed 50-60 question gold set.
3. Install/provision Qdrant and replace the offline local store with a real Qdrant adapter.
4. Provision and benchmark local Ollama `qwen3:8b` and `qwen3-embedding:4b` on target hardware.
5. Confirm target deployment hardware and local-service permissions with IT before latency or serving commitments.
