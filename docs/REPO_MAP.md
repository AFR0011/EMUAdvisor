# Repo Map

Last updated: 2026-05-04

## Workspace Shape

```text
EMUAdvisor/
  EMU_RAG_Current_System_Specs.md
  requirements.txt
  requirements-dev.txt
  AGENTS.md
  docs/
    PROJECT_STATE.md
    REPO_MAP.md
    RUN_PROTOCOL.md
    SCHEMA.md
    SPRINT_PLAN.md
    SPRINT_STATUS.md
    VERSION_LOG.md
    MIGRATION_BACKLOG.md
    RELEASE_CANDIDATE.md
  emu_advisor/
    __init__.py
    admin.py
    answer.py
    audit_log.py
    citations.py
    demo.py
    embeddings.py
    evaluation.py
    html_ingest.py
    load_test.py
    modes.py
    pdf_ingest.py
    retrieval.py
    routing.py
    server.py
    schema.py
    store.py
    text.py
    validate_jsonl.py
  eval_sets/
    v1_seed.jsonl
  static/
    index.html
    style.css
    app.js
  tests/
    fixtures/
      canonical_chunks.valid.jsonl
      canonical_chunks.invalid.jsonl
    test_schema.py
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
- `docs/RELEASE_CANDIDATE.md`: demo scaffold release notes and remaining production gaps.
- `emu_advisor/schema.py`: dependency-free canonical schema validation and legacy chunk mapping.
- `emu_advisor/validate_jsonl.py`: JSONL validator CLI for canonical records.
- `emu_advisor/html_ingest.py` and `pdf_ingest.py`: canonical source ingestion.
- `emu_advisor/retrieval.py`, `store.py`, `embeddings.py`, and `modes.py`: local retrieval stack.
- `emu_advisor/answer.py` and `citations.py`: answerability, fallback, conflict, and citations.
- `emu_advisor/server.py` and `static/`: FastAPI demo and UI.
- `tests/`: unit tests and schema fixtures.
- `.old/*.py`: old-demo ingestion, processing, indexing, retrieval, reranking, and evaluation scripts.
- `.old/backend/`: FastAPI backend, RAG adapter, configuration, and static frontend.
- `.old/requirements-full.txt`: full old-demo dependency list.
- `.old/backend/requirements.txt`: minimal backend dependency list.

## Pipeline Data Flow

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
- Backend framework: FastAPI with Uvicorn.
- Frontend: static HTML, CSS, and JavaScript.
- Crawl storage: SQLite plus raw files.
- Intermediate data: JSONL and JSON reports.
- Existing retrieval stack: BM25 plus dense embeddings with FAISS when available, numpy fallback otherwise.
- Existing model tooling: `sentence-transformers`, `transformers`, optional local Ollama.
- Full old-demo dependencies: FastAPI, Uvicorn, Pydantic, Requests, HTTPX, BeautifulSoup, charset-normalizer, numpy, faiss-cpu, sentence-transformers, transformers.
- `torch` is intentionally not pinned because CUDA wheels are platform-specific.

## Active Versus Legacy

- Active product direction is the root system spec.
- Active root implementation covers the local demo pipeline from ingestion through answer/UI scaffolding.
- Legacy runnable code is archived under `.old/`.
- Old-demo READMEs are useful for commands but do not override the current spec.
- Generated folders such as `mevzuat_crawl/`, `eval/`, `old/`, and `snapshots/` are ignored by the old-demo `.gitignore` and are not present in this workspace.

## Known Drift

- The root workspace is version-controlled on `main`.
- `.old/` is ignored by the root repo and should not be treated as active implementation code.
- Old-demo config and scripts default to `intfloat/e5-base-v2`, which conflicts with the bilingual V1 requirement.
- Old-demo config points EN and TR indexes to the same path.
- The spec calls for Qdrant-backed hybrid retrieval, but old-demo code still uses BM25 plus FAISS/numpy.
- The spec requires stronger PDF metadata handling than the visible old-demo docs prove.
- The `.old/` archive contains Python cache files that should remain ignored.
- There is no single standard test command.

## Entry Points

- Full legacy pipeline reference: run numbered scripts in `.old/` in sequence.
- Retrieval smoke: `6.TestRetrieve.py`, `7.RetrieveHybrid.py`, or `8.RerankMultilingualV7_3.py` with a built index.
- Evaluation: `EvaluateRetrieval.py` with a built index and query set.
- Backend: `python -m uvicorn backend.server:app --host 0.0.0.0 --port 8000` from `.old/`.
- UI: `http://127.0.0.1:8000` after backend startup.
