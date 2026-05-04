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

## Historical Old-Demo Git State

- `cee36fc Add files via upload`
- `064058e Initial commit`
