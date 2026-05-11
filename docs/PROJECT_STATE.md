# Project State

Last updated: 2026-05-07

## Current Snapshot

- The current product source of truth is `EMU_RAG_Current_System_Specs.md`.
- The current deliverable is a demo-first, local-only EMU Regulation Assistant, not a full production release.
- The root workspace is now the primary Git repository on branch `main`.
- `.old/` is an ignored local archive of the previous NLPCrawler demo.
- The old demo archive includes a Python RAG pipeline, FastAPI backend, static UI, Ollama integration, and an evaluation harness.
- Live crawl, canonical chunk, and metrics artifacts have been generated under ignored `artifacts/`.
- `eval_sets/v1_gold.jsonl` is now a 60-case assistant-curated candidate set with review status `assistant_curated_pending_human_review`; it is not yet a human-reviewed gold set.
- `eval_sets/emu_gold_seed.jsonl` is now a 50-case provisional seed converted from `docs/gold-set-comprehensive-analysis.md`; it is source-binding and human-review pending.
- Root `README.md` and `docs/DEMO_METRICS_SNAPSHOT.md` now describe the publishable local demo boundary, commands, metrics, and known limits.
- `docs/PROJECT_STATUS_PROGRESS_PLAN.md` now provides a concise current-status, progress, metrics, limitations, and forward-plan summary.
- `docs/SPRINT_PLAN.md` now sequences implementation and testing into 24-48 hour sprints.
- Sprint 1 has added the root canonical schema package, JSONL validator, schema docs, fixtures, and unit tests.
- Sprints 2-17 now have root implementation scaffolds, local tests, and a real-corpus demo validation pass; see `docs/SPRINT_STATUS.md`.
- Board-readiness continuation work from `docs/EMUAdvisor Full Analysis.md` has added strict request validation, optional admin-token protection, security headers, CI, browser-smoke tooling, local analytics, review helpers, benchmark probes, and board-demo documentation.

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
- `emu_advisor/html_ingest.py` and `emu_advisor/pdf_ingest.py` emit canonical chunks from official-scope HTML/PDF sources; HTML ingestion now preserves table summaries, row-level evidence, and derived academic salary facts.
- `emu_advisor/routing.py` handles language/corpus/scope routing.
- `emu_advisor/evaluation.py` validates expanded bilingual evaluation sets and computes top-k retrieval metrics.
- `emu_advisor/evaluation.py` also accepts provisional gold-seed cases when they are explicitly marked as pending source binding and excluded from hard quality claims.
- `emu_advisor/pipeline.py` performs official-host crawl/build into canonical ignored artifacts.
- `emu_advisor/metrics.py` runs evaluation and writes dashboard-ready JSON, Markdown, per-case CSV, human-review CSV, failure-analysis summaries, and cheap/balanced/expensive mode comparisons.
- `emu_advisor/corpus.py` loads `artifacts/demo_corpus/latest/chunks.jsonl` when present and falls back to fixture chunks otherwise.
- `emu_advisor/generation.py` provides local Ollama `qwen3:8b` generation with extractive fallback on failure.
- `emu_advisor/embeddings.py`, `store.py`, `retrieval.py`, `modes.py`, and `index.py` provide local retrieval infrastructure plus a Qdrant adapter/build CLI with local fallback.
- `emu_advisor/answer.py` and `citations.py` implement deterministic answerability, refusal, conflict, table answers, scholarship topic bundles, fallback, and citation behavior.
- `emu_advisor/admin.py` provides snapshot/diff/activation workflow.
- `emu_advisor/server.py`, `static/`, `audit_log.py`, and `load_test.py` provide the simple public chatbot at `/`, admin diagnostics at `/admin`, sanitized `/chat`, full `/ask`, LLM status diagnostics, privacy logging, and load simulation.
- `emu_advisor/eval_review.py` exports human-review CSVs and can bind provisional seed cases against a built corpus artifact.
- `emu_advisor/benchmark.py` runs local embedding and generated-mode probes without promoting generated mode by default.
- `emu_advisor/readiness.py` generates `docs/BOARD_DEMO_READINESS.md` with explicit pass, partial, and blocked gates.
- `tools/browser_smoke.py` provides an optional Playwright smoke for desktop/mobile public chat rendering.
- `tests/fixtures/` contains valid and invalid canonical chunk fixtures.

## Verification State

- Sprint 0 repo ownership baseline is complete: root is the primary Git repository and `.old/` is ignored local legacy reference code.
- Root documentation file listing was verified.
- Legacy `.old/` Python syntax scan passed for 15 files.
- Legacy `.old/backend` import smoke failed because `.old/backend/rag_adapter.py` imports `key` from `anyio`, which is not available in the installed AnyIO package.
- Root schema unit tests passed: `python -m unittest discover -s tests`.
- Full root test suite passed: 58 tests after the board-readiness foundation pass.
- Canonical valid chunk fixture passed JSONL validation.
- Canonical invalid chunk fixture failed validation as expected with field-level errors.
- Root package/test/tool syntax scan passed for 35 files.
- Candidate evaluation set validation passed for 60 cases: 30 English, 30 Turkish, 48 answerable, 4 refusal, 4 clarification, and 4 conflict/cross-source cases.
- Provisional gold seed validation is expected to pass for 50 source-binding-pending cases, but those cases are not human-reviewed or adjudicated.
- FastAPI app import smoke passed: app title `EMU Regulation Assistant`.
- Live crawl completed from `https://mevzuat.emu.edu.tr/content.htm` and `https://mevzuat.emu.edu.tr/Content-en.htm`: 123 pages, 22 PDFs, 8,714 chunks, 4 crawl errors.
- Active corpus status: 119 sources/documents, 3,878 English chunks, 4,836 Turkish chunks, 8,599 HTML chunks, 115 PDF chunks.
- Structured evidence status: 493 table summaries, 7,601 table rows, 8 derived salary facts, 497 normal text chunks, and 115 PDF chunks without table metadata.
- Live metrics over the 60-case assistant-curated candidate set are presentable for extractive mode: top-5 retrieval 100%, response accuracy 100%, rejection accuracy 100%, clarification accuracy 100%, citation coverage 100%, extractive latency p50 674 ms / p95 1,267 ms.
- Hard regression metrics over `eval_sets/v1_hard.jsonl` are presentable: 50 cases, top-5 retrieval 100%, response accuracy 100%, rejection accuracy 100%, citation coverage 100%, extractive latency p50 468 ms / p95 2,867 ms, 0 failed cases.
- Generated mode with local Ollama model `qwen3:8b` is implemented and fallback-safe, but the latest bounded 2-second smoke metrics run timed out; generated metrics are marked unavailable in `artifacts/metrics/latest_generated`.
- Mode comparison now has an executable path through `python -m emu_advisor.metrics run --all-modes --cases eval_sets\emu_gold_seed.jsonl --chunks artifacts\demo_corpus\latest\chunks.jsonl --out artifacts\metrics\mode_comparison`.
- Latest provisional seed mode comparison wrote ignored artifacts under `artifacts/metrics/mode_comparison`: balanced total score 0.863 / top-5 84.0% / p50 315 ms / 8 failed cases; expensive total score 0.863 / top-5 84.0% / p50 342 ms / 8 failed cases; cheap total score 0.831 / top-5 80.0% / p50 276 ms / 10 failed cases.
- Embedded local Qdrant indexing was validated with `artifacts/qdrant/latest`, 8,714 chunks, 256 dimensions, and collection `emu_regulations`.
- Board readiness report currently marks the demo as `partial`: presentable locally, but blocked on human-reviewed gold status and service-backed Qdrant validation.
- No campus/server deployment environment is documented yet.

## Known Risks

- The old demo still defaults to `intfloat/e5-base-v2` in multiple places, but active root code now supports hash fallback plus optional local Ollama embeddings.
- Qdrant adapter and index CLI exist in root code; embedded local Qdrant is validated, but a Docker/live Qdrant service build/run has not been validated in this environment.
- Canonical document/chunk schema is implemented and integrated into local ingestion, pipeline build, corpus loading, store, retrieval, metrics, and citation tests.
- PDF handling requirements are stronger than the evidence visible in the old demo code and docs.
- The `.old/` archive contains `__pycache__` files, but `.old/` is ignored by the root repo.
- The `.old/` backend currently fails import in this environment because of an existing AnyIO import issue.
- Generated mode depends on an available local Ollama `qwen3:8b`; the current bounded smoke run timed out at 2 seconds, so extractive fallback remains the validated continuity path.
- Admin/debug endpoints are protected only when `EMU_ADVISOR_ADMIN_TOKEN` is configured; production profile now requires that token at startup.
- Optional Playwright browser smoke depends on local browser availability and is skip-safe when dependencies are unavailable.
- Broad scholarship prompts use deterministic grouped subqueries; p50 remains under 1 second, but p95 is higher than direct extractive questions.
- The 60-case evaluation set and 50-case hard regression set are assistant-curated pending human review; do not label either as human-reviewed.
- The 50-case provisional gold seed is converted from the comprehensive analysis document, but several cases still need exact source/chunk binding and human adjudication before the scores can be presented as gold-standard results.

## Next Actions

1. Human-review `artifacts/metrics/latest/human_review.csv` and promote/repair `eval_sets/v1_gold.jsonl` only after manual labels are complete.
2. Run the all-mode provisional seed benchmark and inspect `artifacts/metrics/mode_comparison/comparison.md`.
3. Manually review the zero-failure candidate and hard-regression metrics for overfitting risk, especially table-derived salary facts and grouped scholarship answers.
4. Bind and adjudicate the provisional gold seed cases before presenting them as gold-standard quality claims.
5. Run the Qdrant index against a Docker/live Qdrant service once Docker or a managed local service is available.
6. Diagnose `qwen3:8b` runtime latency beyond the 2-second smoke limit and benchmark streaming first-token latency on target hardware.
7. Benchmark `qwen3-embedding:4b` indexing on target hardware.
8. Confirm target deployment hardware and local-service permissions with IT before latency or serving commitments.
9. Run the optional Playwright smoke on a machine with browser dependencies installed.
10. Configure `EMU_ADVISOR_ADMIN_TOKEN` before any production-profile demo.
