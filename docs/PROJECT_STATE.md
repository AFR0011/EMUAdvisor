# Project State

Last updated: 2026-05-04

## Current Snapshot

- The current product source of truth is `EMU_RAG_Current_System_Specs.md`.
- The current deliverable is a demo-first, local-only EMU Regulation Assistant, not a full production release.
- The root workspace is now the primary Git repository on branch `main`.
- `.old/` is an ignored local archive of the previous NLPCrawler demo.
- The old demo archive includes a Python RAG pipeline, FastAPI backend, static UI, Ollama integration, and an evaluation harness.
- Generated crawl, index, and evaluation artifacts are not present in the current workspace.
- `docs/SPRINT_PLAN.md` now sequences implementation and testing into 24-48 hour sprints.
- Sprint 1 has added the root canonical schema package, JSONL validator, schema docs, fixtures, and unit tests.
- Sprints 2-17 now have root implementation scaffolds and local tests; see `docs/SPRINT_STATUS.md`.

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
- Full root test suite passed: 27 tests.
- Canonical valid chunk fixture passed JSONL validation.
- Canonical invalid chunk fixture failed validation as expected with field-level errors.
- Root package/test syntax scan passed for 24 files.
- Evaluation seed validation passed for 30 cases across 10 categories.
- FastAPI app import smoke passed: app title `EMU Regulation Assistant`.
- No end-to-end RAG run has been verified in this mapping pass.
- No generated index is available in this workspace, so retrieval quality and answer behavior are unvalidated here.
- No campus/server deployment environment is documented yet.

## Known Risks

- The old demo still defaults to `intfloat/e5-base-v2` in multiple places, which conflicts with the current bilingual requirement.
- Qdrant is the target direction in the spec, but the old demo currently uses BM25 plus FAISS/numpy dense search.
- Canonical document/chunk schema is implemented and integrated into local ingestion, store, retrieval, and citation tests.
- PDF handling requirements are stronger than the evidence visible in the old demo code and docs.
- The `.old/` archive contains `__pycache__` files, but `.old/` is ignored by the root repo.
- The `.old/` backend currently fails import in this environment because of an existing AnyIO import issue.
- The root spec displays mojibake in the current PowerShell output; avoid rewriting it until encoding expectations are confirmed.

## Next Actions

1. Run a real small crawl against `mevzuat.emu.edu.tr` and validate produced canonical chunks.
2. Expand `eval_sets/v1_seed.jsonl` from 30 seed cases to the reviewed 50-60 question gold set.
3. Install/provision Qdrant and replace the offline local store with a real Qdrant adapter.
4. Select and benchmark real local embedding/reranker/LLM models on target hardware.
5. Confirm target deployment hardware and local-service permissions with IT before latency or serving commitments.
