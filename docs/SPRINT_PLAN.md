# Sprint Implementation And Testing Plan

Last updated: 2026-04-30

Primary source of truth: `EMU_RAG_Current_System_Specs.md`

## Planning Rules

- Sprint length: 24-48 hours.
- Default output per sprint: code or docs change, tests or verification evidence, updated project state when status changes.
- Do not start broad refactors before the root Git/repo decision is resolved.
- Do not call the system validated until retrieval, answer behavior, citations, latency, and language routing are tested against the agreed evaluation set.
- Keep V1 narrow: official EMU regulations and official linked PDFs only.
- Runtime must remain local-only. Model downloads during setup are allowed; runtime dependency on external APIs is not.
- English and Turkish corpora must remain separate in V1.

## Acceptance Model

Each implementation sprint should end with one of these states:

- `pass`: implementation done and sprint tests passed.
- `partial`: implementation exists but a named verification gate is incomplete.
- `blocked`: work cannot continue without a specific decision, dependency, artifact, or environment.

Do not move to a dependent sprint while a P0 exit gate is `blocked`.

## Test Layers

- Static checks: syntax, imports, config validation, schema validation.
- Fixture checks: small local HTML/PDF/source fixtures with deterministic expected metadata.
- Pipeline checks: crawl, extract, compile, chunk, index, retrieve, rerank.
- Retrieval evaluation: EN/TR gold questions with expected supporting evidence; target is correct evidence in top 5 when it exists.
- Answer behavior checks: strong, medium, weak, ambiguous, out-of-scope, and conflict cases.
- API/UI checks: FastAPI smoke, `/ask`, `/whoami`, refresh/admin paths, browser load, responsive UI.
- Performance checks: extractive answer time, first generated token time, full generated answer time, and queue behavior.

## Roadmap Summary

| Sprint | Duration | Theme | Primary Exit Gate |
|---|---:|---|---|
| 0 | 24h | Repo ownership and baseline verification | Primary Git/workspace decision recorded |
| 1 | 48h | Canonical schema contract | Schema validates representative chunks |
| 2 | 48h | HTML ingestion metadata retrofit | Crawled HTML carries required traceability fields |
| 3 | 48h | PDF ingestion path | PDF pages/sections/tables preserve citation metadata |
| 4 | 24-48h | Language and scope routing | EN/TR and allowed-source routing matrix passes |
| 5 | 48h | Evaluation set v0 | Initial bilingual gold set is runnable |
| 6 | 48h | Multilingual embedding replacement | EN/TR retrieval comparison is recorded |
| 7 | 48h | Qdrant local foundation | Canonical chunks load into filterable Qdrant collections |
| 8 | 48h | Hybrid retrieval on target stack | Top-5 retrieval gate runs against eval set |
| 9 | 48h | Reranking and operating modes | Cheap/balanced/expensive configs are measurable |
| 10 | 48h | Answerability, refusal, clarification, conflict | Behavior fixtures pass before generation |
| 11 | 24-48h | Citation and traceability hardening | Every answer maps to source/version/chunk evidence |
| 12 | 48h | Streaming generation and extractive fallback | Slow local LLM does not block cited fallback |
| 13 | 48h | Admin refresh and snapshot workflow | Refresh can stage changes before approval |
| 14 | 48h | EMU-branded V1 UI | Browser/API smoke passes with citations and states |
| 15 | 24-48h | Privacy logging and triage loop | Anonymized logs support evaluation fixes |
| 16 | 48h | Latency and concurrency pass | 50 active-session model is tested with queueing |
| 17 | 48h | V1 release candidate | Full demo runbook, eval report, and risks are documented |

## Sprint 0 - Repo Ownership And Baseline Verification

Goal: Establish the working surface before implementation begins.

Implementation:

- Decide whether `EMUAdvisor/` becomes the primary Git repository or whether implementation continues inside `NLPCrawler (Old Demo)/`.
- If root becomes primary, preserve the old demo as imported legacy code and define artifact ignore rules.
- If old demo remains primary, document how root specs/docs sync into the nested repo.
- Remove or quarantine tracked generated files only after the Git ownership decision.
- Create a local environment setup note if commands differ from `docs/RUN_PROTOCOL.md`.

Testing:

- Run the no-bytecode Python syntax scan from `docs/RUN_PROTOCOL.md`.
- Run backend import smoke if dependencies are installed.
- Confirm Git status before and after the sprint.

Exit gate:

- Primary worktree decision is documented in `docs/PROJECT_STATE.md`.
- No implementation sprint starts with ambiguous source-control ownership.

## Sprint 1 - Canonical Schema Contract

Goal: Turn the spec schema into the stable contract for ingestion, indexing, retrieval, citations, and audit.

Implementation:

- Add schema definitions for documents, chunks, source metadata, language, corpus, access tier, version hash, crawl timestamp, section path, article number, page number, and citation fields.
- Add validation utilities for JSONL inputs and outputs.
- Create representative fixtures for HTML chunks, PDF chunks, English regulations, Turkish regulations, and out-of-scope sources.
- Map old-demo chunk fields to the canonical schema without changing ranking behavior yet.

Testing:

- Unit-test schema validation with valid and invalid fixtures.
- Validate a small sample of old-demo chunk-like records if generated artifacts are available.
- Confirm every required traceability field is either populated or explicitly marked unavailable.

Exit gate:

- Canonical fixtures validate.
- Missing metadata is reported explicitly rather than silently dropped.

## Sprint 2 - HTML Ingestion Metadata Retrofit

Goal: Make the existing HTML pipeline produce canonical traceability metadata.

Implementation:

- Update crawl/classify/extract/compile/chunk stages to carry source URL, source title, language, corpus, crawl timestamp, version hash, section path, and article number.
- Enforce source scope for `mevzuat.emu.edu.tr`.
- Add deterministic document and chunk IDs.
- Preserve old-demo outputs where needed, but add canonical output as the forward path.

Testing:

- Run a small crawl against 10-20 regulation pages when network access is allowed.
- Validate generated canonical JSONL against the Sprint 1 schema.
- Re-run the same small crawl and confirm unchanged sources produce stable version hashes.

Exit gate:

- HTML-derived chunks can be traced back to URL, crawl timestamp, source version, section/article, and chunk ID.

## Sprint 3 - PDF Ingestion Path

Goal: Add official PDF support with citation-safe metadata.

Implementation:

- Add a PDF parser path that extracts text with page numbers.
- Preserve headings, article/section hierarchy where detectable, and table boundaries.
- Link PDFs to the official regulation source set.
- Emit canonical chunks with `source_type=pdf`, `page_number`, source URL/path, version hash, and crawl timestamp.

Testing:

- Add at least two PDF fixtures: one simple text PDF and one table-heavy or regulation-like PDF.
- Verify page numbers survive chunking.
- Verify table text is not flattened into unusable citations.
- Validate PDF chunks against the canonical schema.

Exit gate:

- PDF citations can include regulation title, section/article when available, page number, and URL/path.

## Sprint 4 - Language And Scope Routing

Goal: Prevent silent corpus mixing and out-of-scope answering.

Implementation:

- Add explicit language/corpus routing before retrieval.
- Default user-language detection should search the matching corpus first.
- Route English and Turkish questions to their detected-language corpus without EN/TR corpus mixing.
- Reject or redirect sources outside V1 scope.
- Label source language in all retrieved hits and citations.

Testing:

- Build a routing matrix for English query, Turkish query, ambiguous query, and out-of-scope query.
- Assert English and Turkish hits are not mixed.
- Test out-of-scope categories: events, programs, course pages, general FAQ, and advising.

Exit gate:

- Language and source-scope tests pass without relying on LLM behavior.

## Sprint 5 - Evaluation Set V0

Goal: Create the quality gate before tuning retrieval.

Implementation:

- Build the initial bilingual evaluation set, starting with 20-30 questions and expanding toward 50-60.
- For each question, record language, expected source, expected section/article/page where known, expected behavior, and out-of-scope/refusal cases.
- Add query categories: direct rule lookup, deadlines/dates, grading/honor, fees/money, staff regulations, ambiguous terms, insufficient evidence, and conflicts.
- Extend or wrap `EvaluateRetrieval.py` so it reports top-1/top-3/top-5 supporting evidence presence.

Testing:

- Run the harness against any available baseline index.
- If no index exists, validate the evaluation file schema and mark retrieval metrics blocked.

Exit gate:

- Evaluation set is machine-readable and can distinguish retrieval failure from answer-generation failure.

## Sprint 6 - Multilingual Embedding Replacement

Goal: Replace the English-focused embedding default with a multilingual baseline.

Implementation:

- Choose an initial multilingual embedder for the local environment, such as BGE-M3, multilingual-E5, gte-multilingual, or a Qwen3 embedding variant.
- Remove `intfloat/e5-base-v2` as the default for bilingual V1 paths.
- Record model name, dimension, device, batch size, and index compatibility in index metadata.
- Rebuild a baseline index from canonical chunks if artifacts exist.

Testing:

- Compare old and new embedding baselines on the evaluation set when both indexes exist.
- Report EN and TR retrieval separately.
- Confirm query/document prefixes match the selected model family.

Exit gate:

- Multilingual baseline is configured and retrieval comparison is recorded, or missing artifacts are documented as the blocker.

## Sprint 7 - Qdrant Local Foundation

Goal: Establish the target vector store without losing lexical retrieval principles.

Implementation:

- Add local Qdrant setup instructions or scripts.
- Define collection shape for canonical chunks, dense vectors, optional sparse vectors, and payload metadata.
- Add payload indexes for language, corpus, access tier, source type, source URL/path, version hash, crawl timestamp, section, article, and page.
- Add an importer from canonical JSONL to Qdrant.
- Keep the old FAISS/BM25 path available until Qdrant retrieval is proven.

Testing:

- Start Qdrant locally.
- Create/recreate collections safely.
- Load fixture chunks and query by payload filters.
- Verify EN/TR filters and source-type filters.

Exit gate:

- Canonical chunks can be inserted and retrieved from Qdrant with metadata filters.

## Sprint 8 - Hybrid Retrieval On Target Stack

Goal: Implement Qdrant-backed retrieval that preserves lexical plus dense behavior.

Implementation:

- Add dense retrieval from Qdrant.
- Add sparse retrieval through Qdrant sparse vectors or a local BM25 sidecar if that is more reliable.
- Implement reciprocal rank fusion or equivalent blending.
- Preserve top-k controls and per-corpus filtering.
- Return canonical hit objects usable by reranking and citations.

Testing:

- Run retrieval smoke tests for English and Turkish.
- Run evaluation top-5 evidence metrics.
- Compare Qdrant hybrid results against old FAISS/BM25 where possible.
- Test metadata filters for language, corpus, source type, and access tier.

Exit gate:

- Hybrid retrieval runs against the evaluation harness and reports EN/TR results separately.

## Sprint 9 - Reranking And Operating Modes

Goal: Make cheap, balanced, and expensive modes concrete across the full pipeline.

Implementation:

- Define mode presets for retrieval fanout, embedding model, reranker model, rerank candidate count, context size, generation model, timeouts, and fallback behavior.
- Add configuration validation so mode settings are explicit and reproducible.
- Keep reranking optional for cheap mode and stronger for balanced/expensive modes.
- Record model and mode metadata in evaluation outputs.

Testing:

- Run retrieval/reranking smoke per mode when models are available.
- Measure candidate retrieval time, reranking time, and total pre-generation time.
- Verify mode changes affect retrieval/reranking behavior, not only LLM size.

Exit gate:

- Each mode has a documented, executable configuration and basic timing output.

## Sprint 10 - Answerability, Refusal, Clarification, And Conflict

Goal: Gate generation with deterministic evidence rules.

Implementation:

- Implement strong, medium, weak, and conflict evidence decisions before LLM generation.
- Add ambiguity detection and clarification prompts for underspecified queries.
- Add refusal/redirection paths for weak evidence and out-of-scope requests.
- Add conflict display behavior that shows disagreeing sources instead of resolving them silently.

Testing:

- Unit-test gate decisions from synthetic hit sets.
- Add evaluation cases for strong support, partial support, no support, ambiguity, out-of-scope, and conflict.
- Verify the LLM is not called for weak/out-of-scope cases unless explicitly allowed for formatting a refusal.

Exit gate:

- Answerability behavior passes without depending on model output quality.

## Sprint 11 - Citation And Traceability Hardening

Goal: Make every answer auditable back to source version and chunk evidence.

Implementation:

- Standardize citation objects for HTML and PDF.
- Include title, section/article, page number for PDFs, URL/path, source language, source version/hash, crawl timestamp, and chunk IDs.
- Add answer metadata that records which chunks were used.
- Ensure bottom citations match the answer text and retrieved evidence.

Testing:

- Test HTML citation formatting.
- Test PDF citation formatting with page numbers.
- Test missing metadata behavior.
- Verify each answer citation maps to an existing canonical chunk.

Exit gate:

- A reviewer can trace each substantive answer from response to source document, source version, crawl timestamp, and chunk.

## Sprint 12 - Streaming Generation And Extractive Fallback

Goal: Keep answers useful when local generation is slow or queued.

Implementation:

- Add extractive answer-first behavior with citations.
- Stream local LLM generation through Ollama, llama.cpp, or vLLM depending on environment.
- Add timeout and queue behavior so the user is not blocked waiting for a full generated answer.
- Preserve citation grounding in generated answers.

Testing:

- Simulate slow/failed local LLM and verify extractive fallback returns.
- Measure extractive answer time, first generated token time, and full answer time.
- Verify no external API calls are required at runtime.

Exit gate:

- Extractive answer is available even when generation is slow, unavailable, or queued.

## Sprint 13 - Admin Refresh And Snapshot Workflow

Goal: Make updates reproducible and reviewable.

Implementation:

- Add CLI admin refresh path for crawl, diff, approval, index build, and activation.
- Keep prior crawl/index snapshots.
- Add changed-source diff reports before production-like activation.
- Harden `/fetch` or replace it with an admin-safe workflow if needed.

Testing:

- Run refresh dry-run against fixtures or a small crawl.
- Verify snapshots are preserved.
- Verify activation can switch to a new index without deleting the old one.
- Test admin token or localhost-only protections for refresh endpoints.

Exit gate:

- A demo refresh can be staged, reviewed, and activated with rollback artifacts preserved.

## Sprint 14 - EMU-Branded V1 UI

Goal: Make the staff-facing demo clear, scoped, and citation-first.

Implementation:

- Refresh the static UI around EMU identity: navy/deep blue, gold/yellow, white, and light gray.
- Show language/source-corpus indicators.
- Show loading, streaming, extractive fallback, refusal, clarification, and error states.
- Present bottom citations with readable source metadata.
- Avoid presenting the assistant as an official final/legal authority.

Testing:

- Browser smoke at `http://127.0.0.1:8000`.
- Test desktop and mobile widths.
- Test clarification flow, refusal flow, answer flow, and slow-generation flow.
- Check basic accessibility: keyboard focus, contrast, readable citation links.

Exit gate:

- Demo UI supports the V1 answer flow without hiding uncertainty, citations, or source language.

## Sprint 15 - Privacy Logging And Triage Loop

Goal: Capture enough operational data to improve quality without storing unnecessary personal information.

Implementation:

- Add anonymized query logging.
- Record retrieval hits, gate decisions, answer mode, latency segments, and citation IDs.
- Add a triage format for bad-answer reports.
- Avoid storing directly identifying user information where possible.

Testing:

- Verify logs omit or hash session identifiers.
- Verify logs include enough retrieval and gate data to debug failures.
- Test log rotation or bounded storage.

Exit gate:

- A failed answer can be investigated without exposing avoidable personal data.

## Sprint 16 - Latency And Concurrency Pass

Goal: Validate the demo under realistic usage assumptions.

Implementation:

- Define active sessions versus simultaneous generations.
- Add queueing behavior for local LLM generation if needed.
- Add caching where it improves retrieval/model latency without hiding stale source versions.
- Record mode-specific latency metrics.

Testing:

- Test 50 active sessions with limited simultaneous generation.
- Measure extractive answer shown by, first generated token by, and full generated answer by.
- Compare results to cheap, balanced, and expensive targets from the spec.
- Verify overload returns extractive answers rather than blocking.

Exit gate:

- Load behavior is documented with measured limits and fallback behavior.

## Sprint 17 - V1 Release Candidate

Goal: Produce a demo-ready V1 package and evidence report.

Implementation:

- Freeze selected mode/config for the demo.
- Run full crawl/index/retrieval/evaluation pipeline.
- Prepare demo script and known limitations.
- Update `docs/PROJECT_STATE.md`, `docs/VERSION_LOG.md`, and backlog status.
- Record hardware, models, index version, crawl timestamp, and evaluation results.

Testing:

- Run full evaluation set.
- Run backend/API/UI smoke.
- Run at least one EN answer, one TR answer, one clarification, one refusal, one conflict or simulated conflict, and one PDF citation case.
- Confirm no external runtime APIs are used.

Exit gate:

- V1 demo can be shown with documented scope, results, limitations, and rollback path.

## Go/No-Go Gates

- After Sprint 1: Do not expand ingestion until canonical schema is stable enough for fixtures.
- After Sprint 5: Do not tune retrieval without an evaluation set.
- After Sprint 8: Do not claim Qdrant migration success without top-5 retrieval metrics.
- After Sprint 10: Do not expose LLM generation before answerability/refusal rules pass.
- After Sprint 14: Do not demo as V1 unless citations, source language, refusal, and clarification are visible in the UI.
- After Sprint 17: Do not call the project production-ready; the spec defines this as a demo-first system until deployment, governance, and IT constraints are resolved.

## Running Sprint Reviews

Each sprint review should record:

- What changed.
- What commands/tests were run.
- What artifacts were created or updated.
- What metrics changed.
- What remains blocked.
- Whether `docs/PROJECT_STATE.md` or `docs/MIGRATION_BACKLOG.md` needs an update.
