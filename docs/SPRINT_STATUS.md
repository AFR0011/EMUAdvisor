# Historical Sprint Status and Evidence Correction

The earlier sprint implemented the local FastAPI application, ingestion/retrieval paths, evaluation tooling, CI, browser smoke, and documentation surfaces. Those implementation facts remain useful.

The earlier readiness interpretation does not remain current:

- `v1_gold.jsonl` is assistant-curated and pending independent human review.
- Historical perfect percentages were automated retrieval/behavior/citation-presence proxies, not semantic answer-quality evidence.
- Historical ignored corpus and metric outputs lack the immutable manifest evidence needed for reproduction in this checkout.
- Fixture-backed browser checks establish UI/software behavior only.
- Presentation, publication, release, and deployment remain blocked.

Current execution state belongs in `DEV_STATE.md`; current product/evidence state belongs in `docs/PROJECT_STATE.md`; historical commits remain in Git.
