# Repo Map

Last updated: 2026-04-30

## Workspace Shape

```text
EMUAdvisor/
  EMU_RAG_Current_System_Specs.md
  AGENTS.md
  docs/
    PROJECT_STATE.md
    REPO_MAP.md
    RUN_PROTOCOL.md
    SPRINT_PLAN.md
    VERSION_LOG.md
    MIGRATION_BACKLOG.md
  NLPCrawler (Old Demo)/
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
- Current root is an operating workspace and spec holder.
- `NLPCrawler (Old Demo)/` is a runnable legacy Python/FastAPI demo in its own Git repository.

## Source Areas

- `EMU_RAG_Current_System_Specs.md`: current product and architecture specification.
- `docs/`: operating docs for future Codex and human work.
- `docs/SPRINT_PLAN.md`: 24-48 hour implementation and testing sequence.
- `NLPCrawler (Old Demo)/*.py`: old-demo ingestion, processing, indexing, retrieval, reranking, and evaluation scripts.
- `NLPCrawler (Old Demo)/backend/`: FastAPI backend, RAG adapter, configuration, and static frontend.
- `NLPCrawler (Old Demo)/requirements-full.txt`: full old-demo dependency list.
- `NLPCrawler (Old Demo)/backend/requirements.txt`: minimal backend dependency list.

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
- Legacy runnable code is the old demo.
- Old-demo READMEs are useful for commands but do not override the current spec.
- Generated folders such as `mevzuat_crawl/`, `eval/`, `old/`, and `snapshots/` are ignored by the old-demo `.gitignore` and are not present in this workspace.

## Known Drift

- The root workspace is not version-controlled, while the old demo is a nested Git repository.
- Old-demo config and scripts default to `intfloat/e5-base-v2`, which conflicts with the bilingual V1 requirement.
- Old-demo config points EN and TR indexes to the same path.
- The spec calls for Qdrant-backed hybrid retrieval, but old-demo code still uses BM25 plus FAISS/numpy.
- The spec requires stronger PDF metadata handling than the visible old-demo docs prove.
- The old demo tracks Python cache files.
- There is no single standard test command.

## Entry Points

- Full pipeline: run numbered scripts in `NLPCrawler (Old Demo)/` in sequence.
- Retrieval smoke: `6.TestRetrieve.py`, `7.RetrieveHybrid.py`, or `8.RerankMultilingualV7_3.py` with a built index.
- Evaluation: `EvaluateRetrieval.py` with a built index and query set.
- Backend: `python -m uvicorn backend.server:app --host 0.0.0.0 --port 8000` from `NLPCrawler (Old Demo)/`.
- UI: `http://127.0.0.1:8000` after backend startup.
