# Version Log

Use this log for meaningful project milestones only.

## 2026-04-30 - Repo Mapping Baseline

- Created root operating docs for the EMUAdvisor workspace.
- Identified `EMU_RAG_Current_System_Specs.md` as the current product source of truth.
- Identified the previous NLPCrawler demo as legacy/prototype code.
- Documented the initial workspace state before root Git initialization.
- Documented current verification limitations: no generated crawl/index/evaluation artifacts are present.

## 2026-04-30 - Sprint Plan Baseline

- Added `docs/SPRINT_PLAN.md` with 24-48 hour implementation and testing sprints.
- Updated project state and repo map to reference the sprint plan.

## 2026-05-04 - Sprint 0 Root Repo Baseline

- Recorded root `EMUAdvisor/` as the primary Git repository for future `emu-advisor` work.
- Recorded `.old/` as an ignored local legacy archive of the previous demo.
- Expanded root ignore rules for Python caches, virtual environments, and generated RAG artifacts.
- Removed the broken `.old` gitlink from the root index while leaving the local `.old/` archive on disk.
- Verified legacy Python syntax for 15 files.
- Recorded the legacy backend import blocker caused by `.old/backend/rag_adapter.py` importing `key` from AnyIO.

## 2026-05-04 - Sprint 1 Canonical Schema Baseline

- Added `emu_advisor/schema.py` with canonical document/chunk validation and legacy chunk mapping.
- Added `emu_advisor/validate_jsonl.py` for canonical JSONL validation.
- Added schema documentation and valid/invalid chunk fixtures.
- Added unit tests for canonical validation, legacy mapping, and validator CLI behavior.
- Verified schema tests and JSONL validation.

## 2026-05-04 - Sprints 2-17 Local Demo Scaffold

- Added canonical HTML and PDF ingestion modules with traceability metadata.
- Added language/scope routing and a 30-case bilingual evaluation seed set.
- Added local deterministic multilingual embedding baseline, Qdrant-compatible local vector store, hybrid retrieval, and operating modes.
- Added deterministic answerability gates, conflict display, citation objects, and extractive-first streaming fallback.
- Added admin snapshot/diff/activation workflow.
- Added FastAPI demo app, EMU-branded static UI, anonymized audit logging, active-session load simulation, and release-candidate notes.
- Added root runtime and development dependency manifests.
- Verified the local scaffold with 27 unit/API tests, evaluation seed validation, syntax scan, and FastAPI import smoke.

## 2026-05-04 - Presentable Real-Corpus Demo Metrics

- Added the root live crawl/build CLI for official `mevzuat.emu.edu.tr` HTML and linked PDFs.
- Added corpus artifact loading, corpus status reporting, and active metrics API/UI cards.
- Replaced the seed evaluation file with `eval_sets/v1_gold.jsonl` and added metrics reports for JSON, Markdown, per-case CSV, and human-review CSV.
- Added local Ollama embedding/generation adapters while preserving hash/extractive fallbacks.
- Built the live ignored corpus artifact: 123 pages, 22 PDFs, 2,496 chunks, 119 sources/documents.
- Produced presentable seed-set metrics: top-5 retrieval 95.83%, response accuracy 83.33%, rejection accuracy 100%, citation coverage 100%, extractive p50 84 ms.
- Recorded bounded `qwen3:8b` generation as unavailable in this environment because all attempted generated calls timed out.
- Verified with 38 unit/API tests, canonical JSONL validation, evaluation validation, metrics run, API smoke, syntax scan, and FastAPI import smoke.

## 2026-05-04 - Evaluation-First Hardening Candidate Pass

- Expanded `eval_sets/v1_gold.jsonl` to 60 assistant-curated EN/TR cases with source URLs, chunk IDs, behavior mix, and `assistant_curated_pending_human_review` labels.
- Added stricter evaluation validation for case count, EN/TR balance, answerable source labels, cross-source labels, and mojibake detection.
- Added metrics failure analysis, category metrics, worst failed cases, generated-mode status/unavailable reason, and bounded Ollama smoke gating.
- Added root `README.md` and `docs/DEMO_METRICS_SNAPSHOT.md` for GitHub/demo packaging.
- Added `/llm/status`, UI local-LLM status badge, generated-answer smoke fallback, Qdrant backend envs, and `python -m emu_advisor.index build`.
- Hardened retrieval and extractive answer ordering by demoting TOC/form chunks and using source metadata plus signal terms for scoring.
- Produced 60-case candidate metrics: top-5 retrieval 92.31%, response accuracy 92.31%, rejection accuracy 100%, clarification accuracy 100%, citation coverage 100%, extractive p50 129 ms.
- Recorded `qwen3:8b` generated mode as unavailable because bounded smoke generation timed out despite the model being detected.
- Verified with 45 unit/API tests, evaluation validation, metrics runs, and generated-mode smoke-gated metrics.

## 2026-05-05 - Priority Fix Pass

- Validated the Qdrant backend with an embedded local Qdrant index at `artifacts/qdrant/latest` containing 2,496 chunks in collection `emu_regulations`.
- Fixed Qdrant adapter compatibility for current `qdrant-client` APIs while preserving fake-client unit tests and local fallback behavior.
- Fixed local Ollama `qwen3:8b` generation by disabling qwen thinking mode, reducing bounded generation settings, raising probe timeouts, and clearing a stuck resident Ollama runner.
- Changed `/ask` generated mode to perform a fast model-availability check and rely on extractive fallback if the generation call fails.
- Hardened retrieval scoring/routing for Turkish grade queries, academic staff salary/scale queries, scholarship queries, and index/form chunk demotion.
- Produced updated 60-case candidate metrics: top-5 retrieval 100%, response accuracy 100%, rejection accuracy 100%, clarification accuracy 100%, citation coverage 100%, extractive p50 87 ms.
- Produced generated metrics with `qwen3:8b`: 48 / 48 generated attempts completed, generated p50 14,254 ms, generated p95 16,057 ms.
- Verified with 45 unit/API tests, canonical JSONL validation, evaluation validation, metrics runs, Qdrant index build, and FastAPI import smoke.

## 2026-05-05 - Structured Evidence Hardening

- Rebuilt HTML ingestion around table-aware evidence: table summaries, row-level chunks, table metadata, and derived academic salary facts.
- Added derived academic salary comparisons that link title-to-scale rows with salary-scale rows for professor, associate professor, and assistant professor queries.
- Added `eval_sets/v1_hard.jsonl` with 50 assistant-curated salary-table, scholarship-bundle, and refusal regression cases.
- Added deterministic scholarship topic bundles for broad prompts such as `How to get a scholarship?`, using grouped extractive evidence instead of large raw LLM prompts.
- Added localized Turkish scholarship bundle subqueries and preserved out-of-scope refusals before the bundle planner runs.
- Hardened retrieval normalization, Turkish routing, source-specific boosts for withdrawal/scholarship/research-assistant rules, placeholder form-row demotion, and cross-corpus result diversification.
- Rebuilt the live ignored corpus artifact: 123 pages, 22 PDFs, 8,714 chunks, 119 sources/documents.
- Rebuilt embedded Qdrant at `artifacts/qdrant/latest`: 8,714 chunks, 256 dimensions, collection `emu_regulations`.
- Produced updated 60-case candidate metrics: top-5 retrieval 100%, response accuracy 100%, rejection accuracy 100%, clarification accuracy 100%, citation coverage 100%, extractive p50 674 ms.
- Produced hard-regression metrics: top-5 retrieval 100%, response accuracy 100%, rejection accuracy 100%, citation coverage 100%, extractive p50 468 ms.
- Recorded generated metrics with `qwen3:8b` as unavailable under the 2-second smoke limit despite model detection; extractive fallback remains verified.
- Verified with 49 unit/API tests, JSONL validation, evaluation validation, gold and hard metrics runs, Qdrant index build, API smoke, and FastAPI import smoke.

## 2026-05-07 - Board-Readiness Continuation Foundation

- Added evaluation review helpers for pending human labels, CSV export, and provisional seed chunk binding.
- Added strict request validation, sanitized validation errors, security headers, and optional admin-token protection for admin/debug routes.
- Added local audit-log analytics and surfaced them in the admin console without external telemetry.
- Added optional Playwright browser smoke tooling and a GitHub Actions CI baseline.
- Added Qdrant health, embedding benchmark, generated-mode benchmark, expanded load reporting, and board-readiness report CLIs.
- Polished the public demo UI with scope indicators, answer-state labels, citation metadata, focus-visible styling, and mobile-aware layout constraints.
- Added board-demo, publication, and readiness docs while preserving human-review and live-Qdrant blockers as explicit non-production gates.

## 2026-05-22 - Language Routing And Chat Evidence Reveal

- Removed the V1 EN/TR cross-corpus routing surface from routing, retrieval, metrics, API request models, and UI controls.
- Updated user-mode streaming chat so citations and extractive evidence are emitted only after answer streaming completes and remain hidden behind a source reveal button by default.

## Historical Old-Demo Git State

- `cee36fc Add files via upload`
- `064058e Initial commit`
