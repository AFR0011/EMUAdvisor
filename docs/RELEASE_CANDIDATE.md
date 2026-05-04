# V1 Release Candidate Notes

Last updated: 2026-05-04

## Status

The repository now has a root implementation path for every planned sprint plus a presentable real-corpus demo pass. It is still not production-ready, but it is suitable for a local staff-facing demo and GitHub publication as `emu-advisor`.

## Verified Locally

- Canonical schema validation.
- HTML ingestion from official-scope EMU regulation URLs.
- PDF ingestion with page-number metadata using local `pypdf`.
- Language/corpus routing for English and Turkish.
- Machine-readable bilingual evaluation seed set.
- Local deterministic embedding baseline.
- Qdrant-compatible in-memory vector/payload store for offline testing.
- Hybrid lexical+dense retrieval and mode presets.
- Answerability gate, refusal, clarification, conflict display, citations, and extractive fallback.
- Snapshot/diff/activation workflow.
- FastAPI demo endpoints and EMU-branded static UI.
- Privacy-preserving audit log format.
- Active-session load simulation.
- Root live crawl/index CLI for `mevzuat.emu.edu.tr`.
- Corpus artifact loader with demo fallback.
- Metrics runner and saved dashboard artifacts.
- API endpoints for `/metrics` and `/corpus/status`.

## Current Demo Metrics

Latest ignored artifacts:

- Corpus: `artifacts/demo_corpus/latest/chunks.jsonl`
- Metrics: `artifacts/metrics/latest/metrics.json`, `metrics.md`, `per_case.csv`, `human_review.csv`

Measured on 2026-05-04 over the 30-case seed gold set:

- Corpus: 123 crawled pages, 22 PDFs, 2,496 chunks, 119 sources/documents.
- Language split: 1,226 English chunks and 1,270 Turkish chunks.
- Retrieval top-5: 95.83%.
- Response accuracy: 83.33%.
- Rejection accuracy: 100%.
- Clarification accuracy: 100%.
- Citation coverage: 100%.
- Extractive latency: p50 84 ms, p95 145 ms.
- Generated mode: `qwen3:8b` attempted for 23 answerable cases; all timed out in this environment, so generated latency is unavailable and extractive fallback is the verified path.

## Not Yet Validated

- Human-reviewed 50-60 question gold set.
- Qdrant server deployment with `qdrant_client`.
- Local LLM generation quality, streaming latency, or GPU serving.
- Campus server deployment constraints.

## Demo Command

```powershell
python -m emu_advisor.pipeline build --seed https://mevzuat.emu.edu.tr/content.htm --seed https://mevzuat.emu.edu.tr/Content-en.htm --out artifacts\demo_corpus\latest --max-pages 1000 --include-pdfs
python -m emu_advisor.metrics run --cases eval_sets\v1_gold.jsonl --chunks artifacts\demo_corpus\latest\chunks.jsonl --out artifacts\metrics\latest --include-generation --ollama-model qwen3:8b --ollama-timeout-s 2
python -m uvicorn emu_advisor.server:app --host 127.0.0.1 --port 8000
```

Then open `http://127.0.0.1:8000`.

## Release Gate

Do not publish this as production. It is suitable for a presentable local demo, GitHub publication as `emu-advisor`, and continuing implementation toward reviewed metrics and production retrieval infrastructure.
