# Project Status, Progress, and Plan

Last updated: 2026-05-22

## Executive Summary

EMUAdvisor is now a presentable local-only demo for answering staff-facing questions about official EMU regulations. The root repository is the active implementation surface, while `.old/` is retained only as an ignored legacy reference.

The current system can crawl the official regulation source scope, build canonical chunks, route English and Turkish questions to separate corpora, answer with citations, refuse out-of-scope questions, show conflicts, handle table-derived salary facts, and return grouped extractive answers for broad scholarship questions.

This is not production-ready and must not be described as an official EMU decision system. The strongest current claim is: a local demo has been validated against assistant-curated candidate and hard-regression evaluation sets.

## Product Boundary

V1 is scoped to official EMU regulations from `mevzuat.emu.edu.tr` plus official linked PDFs that belong to that regulation source set.

V1 supports English and Turkish, but the corpora remain separate because the sources are not guaranteed to be one-to-one translations. V1 no longer exposes EN/TR cross-corpus answers or comparison.

V1 does not cover events, advising, course/program information, private records, workflow automation, email, scheduling, or general university chatbot behavior.

## Achieved So Far

- Root repo ownership is established for future `emu-advisor` publication.
- Canonical document/chunk schema and JSONL validation are implemented.
- HTML and PDF ingestion are implemented for official-scope sources.
- Table-aware HTML ingestion now emits table summaries, row-level table chunks, and derived salary facts.
- Live crawl/index pipeline exists at `python -m emu_advisor.pipeline build ...`.
- Corpus loading prefers `artifacts/demo_corpus/latest/chunks.jsonl` and falls back to fixture data only when no live corpus exists.
- English/Turkish routing and out-of-scope routing are implemented without EN/TR corpus mixing.
- Hybrid lexical+dense retrieval is implemented with local hash embeddings and optional Ollama embeddings.
- Qdrant backend support is implemented with local fallback and an index build CLI.
- Deterministic answerability gates handle answer, refusal, clarification, and conflict modes before generation.
- Citation objects preserve chunk, document, URL, version hash, crawl timestamp, and supporting chunk metadata.
- Broad scholarship prompts use deterministic grouped extractive retrieval instead of sending large raw contexts to the LLM.
- Local Ollama `qwen3:8b` generated mode is implemented with immediate extractive fallback.
- FastAPI demo endpoints and static UI are implemented.
- The root UI is now split into a simple deployed-style chatbot at `/` and a diagnostics-heavy admin console at `/admin`.
- A sanitized `POST /chat` endpoint now returns only public answer state, language, citations, and user-facing evidence groups, while `POST /ask` remains the full admin/debug endpoint.
- Metrics runner writes JSON, Markdown, per-case CSV, human-review CSV, and failure analysis.
- Metrics can now compare cheap, balanced, and expensive modes in one run with `--all-modes`.
- `eval_sets/emu_gold_seed.jsonl` captures the provisional 50-case seed from `docs/gold-set-comprehensive-analysis.md`.
- README, release-candidate notes, sprint status, run protocol, demo metrics snapshot, and repo map are tracked.

## Current Demo Evidence

Latest validated corpus snapshot:

| Item | Current Value |
|---|---:|
| Official pages crawled | 123 |
| PDFs crawled | 22 |
| Crawl errors | 4 |
| Sources/documents | 119 |
| Total chunks | 8,714 |
| English chunks | 3,878 |
| Turkish chunks | 4,836 |
| HTML chunks | 8,599 |
| PDF chunks | 115 |
| Table summaries | 493 |
| Table rows | 7,601 |
| Derived salary facts | 8 |

Latest `eval_sets/v1_gold.jsonl` metrics:

| Metric | Value |
|---|---:|
| Cases | 60 |
| Review status | assistant-curated, pending human review |
| Retrieval top-5 | 100% |
| Response accuracy | 100% |
| Rejection accuracy | 100% |
| Clarification accuracy | 100% |
| Citation coverage | 100% |
| Extractive latency p50 | 674 ms |
| Extractive latency p95 | 1,267 ms |
| Failed cases | 0 |

Latest `eval_sets/v1_hard.jsonl` metrics:

| Metric | Value |
|---|---:|
| Cases | 50 |
| Review status | assistant-curated hard regression |
| Salary-table cases | 24 |
| Scholarship-bundle cases | 24 |
| Refusal cases | 2 |
| Retrieval top-5 | 100% |
| Response accuracy | 100% |
| Rejection accuracy | 100% |
| Citation coverage | 100% |
| Extractive latency p50 | 468 ms |
| Extractive latency p95 | 2,867 ms |
| Failed cases | 0 |

Generated-mode status:

- Local Ollama service and `qwen3:8b` were detected.
- The bounded 2-second smoke run timed out.
- Generated metrics are marked unavailable in `artifacts/metrics/latest_generated`.
- Extractive and grouped answers remain the validated demo path.

## Current Architecture

The active root pipeline is:

```text
official EMU HTML/PDF sources
  -> emu_advisor.pipeline
  -> artifacts/demo_corpus/latest/chunks.jsonl
  -> emu_advisor.corpus
  -> emu_advisor.retrieval
  -> emu_advisor.answer
  -> optional emu_advisor.generation
  -> emu_advisor.server + static UI
  -> emu_advisor.metrics
```

Core implementation areas:

- `emu_advisor/html_ingest.py`: HTML/text/table/derived-fact ingestion.
- `emu_advisor/pdf_ingest.py`: PDF text extraction with page metadata.
- `emu_advisor/retrieval.py`: hybrid retrieval, structured-evidence boosts, source quality demotion.
- `emu_advisor/answer.py`: evidence gating, table answers, scholarship topic bundles, conflict/refusal/clarification.
- `emu_advisor/store.py` and `emu_advisor/index.py`: local store plus Qdrant adapter and build CLI.
- `emu_advisor/server.py`: FastAPI app, demo UI endpoints, corpus/metrics/LLM status, ask endpoints.
- `emu_advisor/metrics.py`: evaluation runner and artifact writer.

## Current Limitations

- The evaluation sets are assistant-curated. They need manual review before being called human-reviewed gold metrics.
- The provisional gold seed is useful for mode tuning, but it is explicitly pending exact source/chunk binding and human review.
- Zero-failure metrics are useful for regression tracking, but they may overfit current source labels and need independent review.
- Live Docker/service Qdrant has not been validated in this environment; only embedded local Qdrant has been validated.
- Generated mode is fallback-safe but not currently reliable under the bounded smoke timeout.
- PDF table structure is still weaker than HTML table handling.
- Campus/server deployment constraints and hardware assumptions are not documented yet.
- The `.old/` archive remains useful historically but is not the active implementation path.

## Plan From Here

### Phase 1: Evaluation Credibility

- Human-review `artifacts/metrics/latest/human_review.csv`.
- Review `eval_sets/v1_gold.jsonl` and `eval_sets/v1_hard.jsonl` case by case.
- Bind, repair, and review `eval_sets/emu_gold_seed.jsonl` before calling it gold-standard evaluation.
- Mark incorrect or weak labels and repair expected source URLs/chunk IDs.
- Add failure-analysis notes for any repaired cases.
- Keep the label `assistant_curated_pending_human_review` until manual review is complete.

### Phase 2: Retrieval Quality Hardening

- Continue adding hard regression cases for real observed failures, not broad synthetic expansion.
- Improve table evidence for non-salary numeric facts where HTML export structure is irregular.
- Improve answer extraction so table answers prefer the most relevant derived or row-level evidence and avoid unrelated nearby rows.
- Add more explicit support for multi-source answers where the correct answer spans separate regulations.

### Phase 3: Production Retrieval Path

- Validate Qdrant against a live Docker or service-backed Qdrant instance.
- Decide production profile defaults for `EMU_ADVISOR_VECTOR_BACKEND`, `EMU_ADVISOR_QDRANT_URL`, and collection naming.
- Add operational checks for missing or stale Qdrant indexes.
- Benchmark index build time and query latency on target hardware.

### Phase 4: Local Model Reliability

- Diagnose `qwen3:8b` timeout behavior outside the 2-second smoke limit.
- Benchmark first-token latency and total latency for generated mode.
- Compare generated availability across cheap, balanced, and expensive mode runs only after extractive mode metrics are stable.
- Decide whether generated mode should remain opt-in only for demo usage.
- Benchmark `qwen3-embedding:4b` indexing quality and runtime against the current hash baseline.

### Phase 5: Demo Packaging And Publication

- Keep README and demo docs aligned with the latest metrics.
- Add screenshots or captured sample outputs for GitHub presentation.
- Add a clear "not production / not official decision" warning near demo entry points.
- Prepare a clean GitHub repository as `emu-advisor` once local docs, ignores, and artifacts are reviewed.

### Phase 6: Deployment Planning

- Identify target deployment hardware and local-service permissions.
- Decide whether the demo should run as a simple local Uvicorn service, a Windows service, Docker Compose, or another campus-friendly setup.
- Document backup/rebuild procedures for crawl artifacts, Qdrant index artifacts, and metrics artifacts.
- Define a refresh cadence for official-source crawling and manual evaluation review.

## Immediate Next Actions

1. Run the all-mode provisional seed benchmark and inspect mode failures.
2. Manually label the current human-review CSVs and repair any weak cases.
3. Bind and adjudicate the provisional gold-seed cases.
4. Run a live Qdrant service validation instead of embedded-only Qdrant.
5. Diagnose Ollama `qwen3:8b` latency and decide whether generated mode should be hidden, opt-in, or demo-only.
6. Add more hard cases for table/numeric facts discovered during manual demo testing.
7. Prepare GitHub publication polish: screenshots, sample outputs, and final known-limits wording.

## Current Readiness Judgment

The project is ready for a local, staff-facing demonstration and for continued GitHub publication preparation.

The project is not ready for production use, official policy interpretation, or unattended deployment until the evaluation set is human-reviewed, live Qdrant is validated, local model behavior is characterized, and deployment constraints are documented.
