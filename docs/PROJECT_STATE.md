# Project State

Last updated: 2026-04-30

## Current Snapshot

- The current product source of truth is `EMU_RAG_Current_System_Specs.md`.
- The current deliverable is a demo-first, local-only EMU Regulation Assistant, not a full production release.
- The root workspace contains the current specification and a nested old-demo codebase.
- The root workspace is not a Git repository.
- `NLPCrawler (Old Demo)/` is a clean nested Git worktree on `main` tracking `origin/main`.
- The old demo includes a Python RAG pipeline, FastAPI backend, static UI, Ollama integration, and an evaluation harness.
- Generated crawl, index, and evaluation artifacts are not present in the current workspace.
- `docs/SPRINT_PLAN.md` now sequences implementation and testing into 24-48 hour sprints.

## Active Objective

Harden and productize the V1 EMU Regulation Assistant around the current spec:

- Narrow V1 to official EMU regulations and official linked PDFs.
- Preserve separate English and Turkish corpora.
- Replace the English-focused embedding default.
- Move toward a Qdrant-backed hybrid retrieval stack.
- Add canonical source/chunk metadata and traceability.
- Establish realistic verification with bilingual gold questions.

## Current Implementation Evidence

- Old-demo pipeline scripts live under `NLPCrawler (Old Demo)/` as numbered Python files from crawl through reranking.
- `backend/server.py` exposes FastAPI endpoints for `/`, `/ask`, `/fetch`, `/fetch/status`, and `/whoami`.
- `backend/rag_adapter.py` handles retrieval invocation, clarification, confidence gating, extraction answers, and optional Ollama generation.
- `backend/config.json` points both English and Turkish index paths to `mevzuat_crawl/index_v4_dedup` and enables Ollama model `qwen2.5:14b-instruct`.
- `requirements-full.txt` documents the full old-demo Python dependency surface and intentionally leaves `torch` unpinned.

## Verification State

- Repo mapping was verified from filesystem evidence and existing documentation.
- No end-to-end RAG run has been verified in this mapping pass.
- No generated index is available in this workspace, so retrieval quality and answer behavior are unvalidated here.
- No campus/server deployment environment is documented yet.

## Known Risks

- The old demo still defaults to `intfloat/e5-base-v2` in multiple places, which conflicts with the current bilingual requirement.
- Qdrant is the target direction in the spec, but the old demo currently uses BM25 plus FAISS/numpy dense search.
- Canonical document/chunk schema is specified but not yet implemented as the stable pipeline contract.
- PDF handling requirements are stronger than the evidence visible in the old demo code and docs.
- The nested old-demo Git repo tracks `__pycache__` files, which is source-control drift.
- The root spec displays mojibake in the current PowerShell output; avoid rewriting it until encoding expectations are confirmed.

## Next Actions

1. Start with Sprint 0 in `docs/SPRINT_PLAN.md`: decide primary Git/workspace ownership and baseline verification.
2. Implement Sprint 1 canonical document/chunk schema before expanding ingestion or retrieval.
3. Use the sprint exit gates to avoid tuning retrieval before the evaluation set exists.
4. Confirm target deployment hardware and local-service permissions with IT before latency or serving commitments.
