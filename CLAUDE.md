# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project

EMUAdvisor is a local-only, demo-first RAG assistant that answers questions about Eastern Mediterranean University (EMU) regulations from official cited sources. It crawls `mevzuat.emu.edu.tr` (HTML + PDFs), builds a bilingual (EN/TR) chunk corpus, retrieves via hybrid lexical+dense search, and returns extractive answers with citations. Generated answers via local Ollama are optional with automatic extractive fallback.

## Key Commands

### Setup

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements-dev.txt
```

### Run the demo server

```powershell
python -m uvicorn emu_advisor.server:app --host 127.0.0.1 --port 8000
```

- UI: `http://127.0.0.1:8000`
- Admin: `http://127.0.0.1:8000/admin`
- Sanitized API: `POST /chat`
- Full diagnostic API: `POST /ask` (supports `answer_style=extractive|generated|both`)

### Run tests

```powershell
python -m unittest discover -s tests
```

### Build a demo corpus

```powershell
python -m emu_advisor.pipeline build --seed https://mevzuat.emu.edu.tr/content.htm --seed https://mevzuat.emu.edu.tr/Content-en.htm --out artifacts\demo_corpus\latest --max-pages 1000 --include-pdfs
python -m emu_advisor.validate_jsonl artifacts\demo_corpus\latest\chunks.jsonl --kind chunk
```

### Run evaluation / metrics

```powershell
python -m emu_advisor.metrics run --cases eval_sets\v1_gold.jsonl --chunks artifacts\demo_corpus\latest\chunks.jsonl --out artifacts\metrics\latest
python -m emu_advisor.metrics run --cases eval_sets\v1_hard.jsonl --chunks artifacts\demo_corpus\latest\chunks.jsonl --out artifacts\metrics\hard_latest
python -m emu_advisor.metrics run --all-modes --cases eval_sets\emu_gold_seed.jsonl --chunks artifacts\demo_corpus\latest\chunks.jsonl --out artifacts\metrics\mode_comparison
```

### Qdrant vector backend

```powershell
$env:EMU_ADVISOR_VECTOR_BACKEND="qdrant"
$env:EMU_ADVISOR_QDRANT_URL="http://localhost:6333"
$env:EMU_ADVISOR_QDRANT_COLLECTION="emu_regulations"
python -m emu_advisor.index build --chunks artifacts\demo_corpus\latest\chunks.jsonl --backend qdrant --collection emu_regulations
```

For embedded local Qdrant (no server): `$env:EMU_ADVISOR_QDRANT_PATH="artifacts\qdrant\latest"` + `--qdrant-path`.

## High-Level Architecture

```
Crawl (pipeline) --> Chunks JSONL (artifacts/) --> Corpus loader (corpus.py)
                                                                      |
Route (routing.py) --> HybridRetriever (retrieval.py) --> Answer builder (answer.py)
                                                                      |
                                                              Citations (citations.py)
                                                              Generation (generation.py, optional)
                                                                      |
                                                              FastAPI server (server.py)
```

### Module map

| Module | Responsibility |
|---|---|
| `schema.py` | Canonical document/chunk Pydantic models + validation |
| `validate_jsonl.py` | CLI for validating canonical JSONL files |
| `html_ingest.py` / `pdf_ingest.py` | Source ingestion: extracts text, table summaries, row-level chunks, derived facts |
| `pipeline.py` | Polite crawl of EMU sources, writes raw files + canonical chunks JSONL |
| `corpus.py` | Loads `chunks.jsonl` from artifacts (with fixture fallback), reports corpus status |
| `routing.py` | Language/corpus/scope routing: decides EN vs TR corpus, scope |
| `embeddings.py` | Embedding model creation (Ollama or deterministic hash fallback) |
| `store.py` | Vector store abstraction (local numpy/FAISS or Qdrant) |
| `retrieval.py` | Hybrid lexical+dense retriever, wraps store |
| `modes.py` | Retrieval mode presets: cheap, balanced, expensive |
| `index.py` | Index build CLI (local or Qdrant backend) |
| `answer.py` | Answerability, refusal, table answers, scholarship topic bundles, progressive answers |
| `citations.py` | Citation formatting from retrieved chunks |
| `generation.py` | Ollama LLM generation adapter with extractive fallback on failure |
| `text.py` | Text normalization, Turkish character transliteration, shared stopwords |
| `demo.py` | Tiny in-memory fixture corpus for API/UI smoke tests (no disk artifacts) |
| `server.py` | FastAPI app: `/`, `/admin`, `/chat`, `/ask`, `/ask/stream`, health, corpus/LLM status |
| `admin.py` | Local diagnostics/admin console logic |
| `audit_log.py` | Privacy-aware request/response logging |
| `load_test.py` | Load simulation: 50 active sessions |
| `metrics.py` | Evaluation runner: JSON, Markdown, CSV outputs, mode comparison |
| `evaluation.py` | Bilingual eval set validation and top-k retrieval metrics |

### Important directories

- `artifacts/` -- ignored. Contains crawl output, chunks, metrics, and review CSVs.
- `eval_sets/` -- evaluation sets: `v1_gold.jsonl` (60 cases), `v1_hard.jsonl` (50 cases), `emu_gold_seed.jsonl` (50 cases). All assistant-curated, pending human review.
- `tests/` -- unit tests and schema fixtures. Run with `python -m unittest discover -s tests`.
- `.old/` -- ignored legacy prototype archive. Do not treat as active code.
- `static/` -- frontend files (HTML, CSS, JS) for demo UI and admin console.

## Operating Rules

- `.old/` is a legacy archive, not active code. Generated artifacts under `artifacts/` are ignored by Git.
- `v1_gold.jsonl` and `v1_hard.jsonl` are assistant-curated -- never present their metrics as gold-standard without the "pending human review" caveat. `emu_gold_seed.jsonl` is source-binding but also pending human review.
- Keep runtime local-only: do not add external API dependencies for answering, retrieval, embeddings, reranking, or generation.
- Preserve EN/TR corpus separation by default; cross-corpus search must be explicit.
- For verification, see `docs/RUN_PROTOCOL.md` for the verification ladder (syntax --> imports --> tests --> corpus build --> metrics).
- For product scope, architecture direction, and sprint plans, see `EMU_RAG_Current_System_Specs.md`, `docs/PROJECT_STATE.md`, `docs/SPRINT_PLAN.md`, and `docs/REPO_MAP.md`.
