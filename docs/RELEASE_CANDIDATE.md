# V1 Release Candidate Notes

Last updated: 2026-05-05

## Status

The repository now has a root implementation path for every planned sprint plus a presentable real-corpus demo pass. It is still not production-ready, but it is suitable for a local staff-facing demo and GitHub publication as `emu-advisor`.

## Verified Locally

- Canonical schema validation.
- HTML ingestion from official-scope EMU regulation URLs.
- PDF ingestion with page-number metadata using local `pypdf`.
- Language/corpus routing for English and Turkish.
- Machine-readable 60-case assistant-curated bilingual candidate evaluation set.
- Local deterministic embedding baseline.
- Qdrant adapter and local fallback vector/payload store.
- Hybrid lexical+dense retrieval and mode presets.
- Answerability gate, refusal, clarification, conflict display, citations, and extractive fallback.
- Snapshot/diff/activation workflow.
- FastAPI demo endpoints and EMU-branded static UI.
- Privacy-preserving audit log format.
- Active-session load simulation.
- Root live crawl/index CLI for `mevzuat.emu.edu.tr`.
- Corpus artifact loader with demo fallback.
- Metrics runner and saved dashboard artifacts.
- API endpoints for `/metrics`, `/corpus/status`, and `/llm/status`.
- Demo README and tracked metrics snapshot.
- Embedded local Qdrant index build at `artifacts/qdrant/latest`.
- Table-aware HTML ingestion with row-level chunks and derived academic salary facts.
- Scholarship topic-bundle answer path for broad scholarship questions.
- Local Ollama `qwen3:8b` generated-answer fallback and status diagnostics.

## Current Demo Metrics

Latest ignored artifacts:

- Corpus: `artifacts/demo_corpus/latest/chunks.jsonl`
- Metrics: `artifacts/metrics/latest/metrics.json`, `metrics.md`, `per_case.csv`, `human_review.csv`

Measured on 2026-05-05 over the 60-case assistant-curated candidate set:

- Corpus: 123 crawled pages, 22 PDFs, 8,714 chunks, 119 sources/documents.
- Language split: 3,878 English chunks and 4,836 Turkish chunks.
- Structured evidence: 493 table summaries, 7,601 table rows, 8 derived salary facts.
- Retrieval top-5: 100%.
- Response accuracy: 100%.
- Rejection accuracy: 100%.
- Clarification accuracy: 100%.
- Citation coverage: 100%.
- Extractive latency: p50 674 ms, p95 1,267 ms.
- Hard regression set: 50 cases, top-5 retrieval 100%, response accuracy 100%, rejection accuracy 100%, citation coverage 100%, extractive p50 468 ms.
- Generated mode: `qwen3:8b` was detected but the bounded 2-second smoke metric run timed out; extractive fallback remains the validated path.

## Not Yet Validated

- Human-reviewed 50-60 question gold set.
- Docker/live Qdrant service deployment with `qdrant_client`.
- Human-rated local LLM generation quality, streaming first-token latency, or GPU serving.
- Campus server deployment constraints.

## Demo Command

```powershell
python -m emu_advisor.pipeline build --seed https://mevzuat.emu.edu.tr/content.htm --seed https://mevzuat.emu.edu.tr/Content-en.htm --out artifacts\demo_corpus\latest --max-pages 1000 --include-pdfs
python -m emu_advisor.index build --chunks artifacts\demo_corpus\latest\chunks.jsonl --backend qdrant --collection emu_regulations --qdrant-path artifacts\qdrant\latest
python -m emu_advisor.metrics run --cases eval_sets\v1_gold.jsonl --chunks artifacts\demo_corpus\latest\chunks.jsonl --out artifacts\metrics\latest
python -m emu_advisor.metrics run --cases eval_sets\v1_hard.jsonl --chunks artifacts\demo_corpus\latest\chunks.jsonl --out artifacts\metrics\hard_latest
$env:EMU_ADVISOR_VECTOR_BACKEND="qdrant"
$env:EMU_ADVISOR_QDRANT_PATH="artifacts\qdrant\latest"
python -m uvicorn emu_advisor.server:app --host 127.0.0.1 --port 8000
```

Then open `http://127.0.0.1:8000`.

## Release Gate

Do not publish this as production. It is suitable for a presentable local demo, GitHub publication as `emu-advisor`, and continuing implementation toward reviewed metrics and production retrieval infrastructure.
