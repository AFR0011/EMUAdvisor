# Repo Map

Last updated: 2026-05-07

## Workspace Shape

```text
EMUAdvisor/
  EMU_RAG_Current_System_Specs.md
  requirements.txt
  requirements-dev.txt
  AGENTS.md
  docs/
    DEMO_METRICS_SNAPSHOT.md
    eval_spec.md
    PROJECT_STATE.md
    PROJECT_STATUS_PROGRESS_PLAN.md
    REPO_MAP.md
    RUN_PROTOCOL.md
    SCHEMA.md
    SPRINT_PLAN.md
    SPRINT_STATUS.md
    VERSION_LOG.md
    MIGRATION_BACKLOG.md
    RELEASE_CANDIDATE.md
    BOARD_DEMO_READINESS.md
    DEMO_STORYBOARD.md
    PUBLICATION_CHECKLIST.md
  emu_advisor/
    __init__.py
    admin.py
    answer.py
    audit_log.py
    citations.py
    corpus.py
    benchmark.py
    demo.py
    embeddings.py
    evaluation.py
    eval_review.py
    generation.py
    html_ingest.py
    load_test.py
    metrics.py
    modes.py
    pdf_ingest.py
    pipeline.py
    retrieval.py
    readiness.py
    routing.py
    server.py
    schema.py
    store.py
    text.py
    index.py
    validate_jsonl.py
  eval_sets/
    emu_gold_seed.jsonl
    v1_gold.jsonl
    v1_hard.jsonl
  artifacts/              # ignored generated crawl, corpus, metrics, and review outputs
  static/
    landing.html
    admin.html
    shared.js
    user-chat.js
    admin-diagnostics.js
    style.css
  tests/
    fixtures/
      canonical_chunks.valid.jsonl
      canonical_chunks.invalid.jsonl
    test_schema.py
  tools/
    browser_smoke.py
  .github/
    workflows/
      ci.yml
  .old/
    README.md
    requirements-full.txt
    1.BasicCrawlV2.py
    2.ClassifyContentV2.py
    3.ExtractRowsV7.py
    4.CompileDataV6.py
    5.ChunkerV5.py
    5.2.DedupChunks.py
    5.3.PostprocessChunks.py
    6.BuildIndex.py
    6.TestRetrieve.py
    7.RetrieveHybrid.py
    8.RerankMultilingualV7_3.py
    EvaluateRetrieval.py
    bm25_utils.py
    backend/
      README.md
      config.json
      server.py
      rag_adapter.py
      requirements.txt
      static/
        index.html
        app.js
        style.css
```

## Repo Type

- Research/prototype workspace for a RAG assistant.
- Current root is the primary Git repository for future `emu-advisor` work.
- `.old/` is an ignored local archive of the previous runnable Python/FastAPI demo.

## Source Areas

- `EMU_RAG_Current_System_Specs.md`: current product and architecture specification.
- `requirements.txt` and `requirements-dev.txt`: root runtime and test dependencies.
- `docs/`: operating docs for future Codex and human work.
- `docs/SCHEMA.md`: canonical document/chunk schema contract and validation usage.
- `docs/SPRINT_PLAN.md`: 24-48 hour implementation and testing sequence.
- `docs/SPRINT_STATUS.md`: sprint implementation status and validation boundary.
- `docs/PROJECT_STATUS_PROGRESS_PLAN.md`: current status, achieved progress, validated metrics, limitations, and forward plan.
- `docs/RELEASE_CANDIDATE.md`: live demo release notes, measured metrics, and remaining production gaps.
- `docs/DEMO_METRICS_SNAPSHOT.md`: concise tracked snapshot of current demo corpus, metrics, sample outputs, and limits.
- `docs/BOARD_DEMO_READINESS.md`: generated board-demo readiness status with explicit blocked gates.
- `docs/DEMO_STORYBOARD.md`: repeatable stakeholder demo script.
- `docs/PUBLICATION_CHECKLIST.md`: clean GitHub publication checklist and wording guardrails.
- `docs/eval_spec.md`: scoring rubric, case status rules, and mode-comparison instructions.
- `emu_advisor/schema.py`: dependency-free canonical schema validation and legacy chunk mapping.
- `emu_advisor/validate_jsonl.py`: JSONL validator CLI for canonical records.
- `emu_advisor/html_ingest.py` and `pdf_ingest.py`: canonical source ingestion, including table summaries, row-level chunks, and derived salary facts for HTML.
- `emu_advisor/pipeline.py`: polite official-host crawl/build CLI for canonical demo artifacts.
- `emu_advisor/corpus.py`: active corpus artifact loader, fixture fallback, and corpus status reporting.
- `emu_advisor/metrics.py`: evaluation runner that emits JSON/Markdown/CSV metrics, human-review CSV, failure analysis, and cheap/balanced/expensive comparison reports.
- `emu_advisor/eval_review.py`: review-status summary, human-review CSV export, and provisional seed binding helpers.
- `emu_advisor/benchmark.py`: local embedding and generated-mode benchmark probes.
- `emu_advisor/generation.py`: local Ollama generated-answer adapter with extractive fallback.
- `emu_advisor/retrieval.py`, `store.py`, `embeddings.py`, `modes.py`, and `index.py`: local/Qdrant retrieval stack and index build CLI.
- `emu_advisor/answer.py` and `citations.py`: answerability, table answers, scholarship topic bundles, fallback, conflict, and citations.
- `emu_advisor/server.py` and `static/`: FastAPI demo and UI; `/` is a landing page, `/admin` hosts User chat and Diagnostics modes, `/chat` and `/chat/stream` are sanitized public chat APIs, `/ask` remains the full diagnostic endpoint, `/analytics` summarizes local audit logs, and admin/debug routes can be token-protected.
- `emu_advisor/readiness.py`: board-demo readiness report generator.
- `tools/browser_smoke.py`: optional Playwright desktop/mobile browser smoke.
- `eval_sets/emu_gold_seed.jsonl`: 50-case provisional seed converted from `docs/gold-set-comprehensive-analysis.md`, pending exact source/chunk binding and human review.
- `eval_sets/v1_gold.jsonl`: current 60-case assistant-curated bilingual candidate set pending human review.
- `eval_sets/v1_hard.jsonl`: 50-case assistant-curated hard regression set for table-derived salary and broad scholarship failures.
- `artifacts/`: ignored generated crawl metadata, canonical chunks, snapshots, metrics reports, and review CSVs.
- `tests/`: unit tests and schema fixtures.
- `.old/*.py`: old-demo ingestion, processing, indexing, retrieval, reranking, and evaluation scripts.
- `.old/backend/`: FastAPI backend, RAG adapter, configuration, and static frontend.
- `.old/requirements-full.txt`: full old-demo dependency list.
- `.old/backend/requirements.txt`: minimal backend dependency list.

## Pipeline Data Flow

```text
Official EMU regulation HTML/PDF sources
  -> emu_advisor.pipeline
  -> artifacts/demo_corpus/latest/raw
  -> artifacts/demo_corpus/latest/chunks.jsonl
  -> emu_advisor.corpus
  -> emu_advisor.retrieval
  -> emu_advisor.answer and optional emu_advisor.generation
  -> emu_advisor.server and static UI
  -> /chat for simple demo or /ask for admin diagnostics
  -> emu_advisor.metrics
  -> artifacts/metrics/latest/{metrics.json,metrics.md,per_case.csv,human_review.csv}
```

Legacy reference flow:

```text
Official EMU regulation HTML/PDF sources
  -> 1.BasicCrawlV2.py
  -> crawl.sqlite and raw HTML files
  -> 2.ClassifyContentV2.py
  -> classified JSONL
  -> 3.ExtractRowsV7.py
  -> rows JSONL
  -> 4.CompileDataV6.py
  -> document JSONL
  -> 5.ChunkerV5.py
  -> chunk JSONL
  -> 5.2.DedupChunks.py
  -> deduplicated chunks and report
  -> 5.3.PostprocessChunks.py
  -> postprocessed chunks
  -> 6.BuildIndex.py
  -> BM25 and dense FAISS/numpy index directories
  -> 7.RetrieveHybrid.py
  -> hybrid candidates
  -> 8.RerankMultilingualV7_3.py
  -> reranked hits
  -> backend/rag_adapter.py
  -> extraction or local Ollama synthesis
  -> backend/server.py and static UI
```

## Runtime And Build Signals

- Language: Python.
- Active root package: `emu_advisor`.
- Root test runner: `python -m unittest discover -s tests`.
- Root corpus build: `python -m emu_advisor.pipeline build --seed https://mevzuat.emu.edu.tr/content.htm --seed https://mevzuat.emu.edu.tr/Content-en.htm --out artifacts\demo_corpus\latest --max-pages 1000 --include-pdfs`.
- Root metrics run: `python -m emu_advisor.metrics run --cases eval_sets\v1_gold.jsonl --chunks artifacts\demo_corpus\latest\chunks.jsonl --out artifacts\metrics\latest`.
- Root hard metrics run: `python -m emu_advisor.metrics run --cases eval_sets\v1_hard.jsonl --chunks artifacts\demo_corpus\latest\chunks.jsonl --out artifacts\metrics\hard_latest`.
- Root Qdrant index build: `python -m emu_advisor.index build --chunks artifacts\demo_corpus\latest\chunks.jsonl --backend qdrant --collection emu_regulations --qdrant-path artifacts\qdrant\latest` for embedded local Qdrant, or omit `--qdrant-path` for a live Qdrant service.
- Backend framework: FastAPI with Uvicorn.
- Frontend: static HTML, CSS, and JavaScript.
- Crawl storage: ignored raw files plus canonical JSONL artifacts.
- Intermediate data: JSONL and JSON reports.
- Existing retrieval stack: BM25 plus dense embeddings with FAISS when available, numpy fallback otherwise.
- Active root retrieval stack: local/Qdrant lexical+dense hybrid retrieval with hash fallback and optional Ollama embeddings.
- Existing old-demo model tooling: `sentence-transformers`, `transformers`, optional local Ollama.
- Root runtime dependencies: FastAPI, Uvicorn, Pydantic, HTTPX, and pypdf.
- Optional production vector backend dependency: `qdrant-client`.
- Full old-demo dependencies: FastAPI, Uvicorn, Pydantic, Requests, HTTPX, BeautifulSoup, charset-normalizer, numpy, faiss-cpu, sentence-transformers, transformers.
- `torch` is intentionally not pinned because CUDA wheels are platform-specific.

## Active Versus Legacy

- Active product direction is the root system spec.
- Active root implementation covers the live demo pipeline from crawl/build through metrics, answer/API, and UI.
- Legacy runnable code is archived under `.old/`.
- Old-demo READMEs are useful for commands but do not override the current spec.
- Generated root `artifacts/` outputs are ignored by Git and currently hold the live demo corpus and metrics.

## Known Drift

- The root workspace is version-controlled on `main`.
- `.old/` is ignored by the root repo and should not be treated as active implementation code.
- Old-demo config and scripts default to `intfloat/e5-base-v2`, which conflicts with the bilingual V1 requirement.
- Old-demo config points EN and TR indexes to the same path.
- The active root implementation supports local and Qdrant-backed hybrid retrieval; old-demo code still uses BM25 plus FAISS/numpy.
- The spec requires stronger PDF metadata handling than the visible old-demo docs prove.
- The `.old/` archive contains Python cache files that should remain ignored.
- There is no single standard test command.

## Entry Points

- Full legacy pipeline reference: run numbered scripts in `.old/` in sequence.
- Root corpus build: `python -m emu_advisor.pipeline build ...`.
- Root metrics: `python -m emu_advisor.metrics run ...`.
- Root mode comparison: `python -m emu_advisor.metrics run --all-modes --cases eval_sets\emu_gold_seed.jsonl --chunks artifacts\demo_corpus\latest\chunks.jsonl --out artifacts\metrics\mode_comparison`.
- Root Qdrant/local index build: `python -m emu_advisor.index build ...`.
- Root Qdrant health check: `python -m emu_advisor.index health ...`.
- Root review status: `python -m emu_advisor.eval_review status eval_sets\v1_gold.jsonl eval_sets\v1_hard.jsonl eval_sets\emu_gold_seed.jsonl`.
- Root benchmark probe: `python -m emu_advisor.benchmark embedding --cases eval_sets\v1_gold.jsonl --chunks artifacts\demo_corpus\latest\chunks.jsonl --embedding hash`.
- Root readiness report: `python -m emu_advisor.readiness --out docs\BOARD_DEMO_READINESS.md`.
- Retrieval smoke: `6.TestRetrieve.py`, `7.RetrieveHybrid.py`, or `8.RerankMultilingualV7_3.py` with a built index.
- Legacy evaluation: `EvaluateRetrieval.py` with a built index and query set.
- Backend: `python -m uvicorn emu_advisor.server:app --host 127.0.0.1 --port 8000` from the root repo.
- Legacy backend: `python -m uvicorn backend.server:app --host 0.0.0.0 --port 8000` from `.old/`.
- Landing: `http://127.0.0.1:8000` after backend startup.
- User chat: `http://127.0.0.1:8000/admin?view=user`.
- Diagnostics: `http://127.0.0.1:8000/admin?view=diagnostics`.
