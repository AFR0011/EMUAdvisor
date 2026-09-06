# Repository Map

## Authority

- Product boundary: `EMU_RAG_Current_System_Specs.md`.
- Active workflow: `DEV_STATE.md` and `BLUEPRINT.md`.
- Current implementation/evidence state: `docs/PROJECT_STATE.md`.
- Risks and verification: `RISK_REGISTER.md` and `QA_REPORT.md`.
- Commands: `docs/RUN_PROTOCOL.md`.

`.old/` is absent from this checkout. Any historical README material is non-authoritative even if it exists in Git history.

## Runtime

- `emu_advisor/server.py`: FastAPI routes, explicit corpus/profile startup, admin boundary, capability-protected chat endpoints.
- `emu_advisor/conversation_store.py`: in-memory/default session store, optional bounded persistence, capability hashes.
- `emu_advisor/audit_log.py`: minimized optional audit records.
- `emu_advisor/corpus.py`: explicit fixture/artifact loading and legacy-metric refusal.
- `emu_advisor/routing.py`, `retrieval.py`, `answer.py`, `generation.py`: local query, retrieval, cited answer, and optional local model flow.
- `static/`: user/diagnostic UI; fixture warning and same-tab session capability handling.

## Ingestion and evidence

- `emu_advisor/pipeline.py`: exact-host HTTPS crawl, manual redirect validation, explicit file-fixture provenance.
- `emu_advisor/html_ingest.py`, `pdf_ingest.py`, `schema.py`: canonical record production and validation.
- `emu_advisor/evaluation.py`: protected case loading, retrieval matching, expected-evidence citation matching.
- `emu_advisor/metrics.py`: `emu-advisor-automated-proxy/v2` reports.
- `emu_advisor/eval_review.py`: review export/status tooling.
- `tools/publication_guard.py`: pending-review and claim guard.

## Tests and CI

- `tests/`: unit, regression, security/privacy, provenance, and server tests.
- `tools/browser_smoke.py`: synthetic fixture-mode browser smoke.
- `tools/syntax_check.py`: cross-platform syntax scan.
- `.github/workflows/ci.yml`: Windows/Ubuntu Python 3.12 core checks and Ubuntu browser smoke with immutable action pins.

## Protected/generated paths

- Protected tracked inputs: system specification and evaluation sets.
- Authorized EMU-B001 exception: provenance/adjudication fields only in `eval_sets/v1_gold.jsonl`.
- Generated/private and ignored: `artifacts/**`, `logs/**`, local environments/caches, Qdrant state, corpus, metrics, review work, transcripts.
- Do not inspect, commit, migrate, or delete existing private artifacts during ordinary verification.
