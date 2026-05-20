# EMU Advisor

Local-only prototype for answering Eastern Mediterranean University regulation questions from official cited sources.

## Scope

EMU Advisor is a demo-first RAG assistant for EMU staff. It answers questions about official EMU rules and regulations from `mevzuat.emu.edu.tr` and official linked PDFs, keeps English and Turkish corpora separate by default, and refuses or asks for clarification when evidence is weak or out of scope.

This is not a production system and does not provide official legal or administrative decisions. All generated crawl, index, and evaluation artifacts are local and ignored under `artifacts/`.

## Current Demo Status

- Live corpus artifact: 8,714 chunks from 119 official sources, including 22 PDFs.
- Structured evidence: table summaries, row-level table chunks, and derived salary facts for academic salary-scale comparisons.
- Candidate evaluation set: 60 assistant-curated cases, pending human review.
- Hard regression set: 50 assistant-curated table/broad-query cases in `eval_sets/v1_hard.jsonl`.
- Provisional gold seed: 50 cases in `eval_sets/emu_gold_seed.jsonl`, converted from the comprehensive analysis doc and pending source binding/human review.
- Latest extractive metrics on `v1_gold`: top-5 retrieval 100%, response accuracy 100%, rejection accuracy 100%, citation coverage 100%, p50 extractive latency 674 ms.
- Latest hard metrics on `v1_hard`: top-5 retrieval 100%, response accuracy 100%, rejection accuracy 100%, citation coverage 100%, p50 extractive latency 468 ms.
- Generated mode: local Ollama `qwen3:8b` is implemented and fallback-safe, but the bounded 2-second smoke metric run timed out on this machine.

See `docs/DEMO_METRICS_SNAPSHOT.md` for the tracked metrics summary and sample outputs.
See `docs/BOARD_DEMO_READINESS.md` for the current board-demo readiness gate.

## Setup

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements-dev.txt
```

Optional local services:

- Ollama for generated answers: `qwen3:8b`
- Ollama embeddings: `qwen3-embedding:4b`
- Qdrant for production-style vector storage

No external answering, embedding, reranking, or generation APIs are used.

## Build A Demo Corpus

```powershell
python -m emu_advisor.pipeline build --seed https://mevzuat.emu.edu.tr/content.htm --seed https://mevzuat.emu.edu.tr/Content-en.htm --out artifacts\demo_corpus\latest --max-pages 1000 --include-pdfs
python -m emu_advisor.validate_jsonl artifacts\demo_corpus\latest\chunks.jsonl --kind chunk
```

The server automatically loads `artifacts/demo_corpus/latest/chunks.jsonl` when present and falls back to a tiny fixture corpus otherwise.

## Evaluate

```powershell
python -m emu_advisor.evaluation eval_sets\v1_gold.jsonl
python -m emu_advisor.evaluation eval_sets\v1_hard.jsonl
python -m emu_advisor.evaluation eval_sets\emu_gold_seed.jsonl
python -m emu_advisor.metrics run --cases eval_sets\v1_gold.jsonl --chunks artifacts\demo_corpus\latest\chunks.jsonl --out artifacts\metrics\latest
python -m emu_advisor.metrics run --cases eval_sets\v1_hard.jsonl --chunks artifacts\demo_corpus\latest\chunks.jsonl --out artifacts\metrics\hard_latest
python -m emu_advisor.metrics run --all-modes --cases eval_sets\emu_gold_seed.jsonl --chunks artifacts\demo_corpus\latest\chunks.jsonl --out artifacts\metrics\mode_comparison
python -m emu_advisor.metrics run --cases eval_sets\v1_gold.jsonl --chunks artifacts\demo_corpus\latest\chunks.jsonl --out artifacts\metrics\latest_generated --include-generation --ollama-model qwen3:8b --ollama-timeout-s 2
```

Metrics outputs are written under ignored `artifacts/metrics/` directories as `metrics.json`, `metrics.md`, `per_case.csv`, and `human_review.csv`. All-mode runs also write `comparison.json` and `comparison.md`.

Human-review helpers:

```powershell
python -m emu_advisor.eval_review status eval_sets\v1_gold.jsonl eval_sets\v1_hard.jsonl eval_sets\emu_gold_seed.jsonl
python -m emu_advisor.eval_review export-csv --cases eval_sets\v1_gold.jsonl --out artifacts\review\v1_gold_review.csv
python -m emu_advisor.eval_review bind-seed --cases eval_sets\emu_gold_seed.jsonl --chunks artifacts\demo_corpus\latest\chunks.jsonl --out artifacts\review\emu_gold_seed.bound.jsonl
```

Local benchmark probes:

```powershell
python -m emu_advisor.benchmark embedding --cases eval_sets\v1_gold.jsonl --chunks artifacts\demo_corpus\latest\chunks.jsonl --embedding hash
python -m emu_advisor.benchmark generation --cases eval_sets\v1_gold.jsonl --chunks artifacts\demo_corpus\latest\chunks.jsonl --model qwen3:8b --timeout-s 30 --limit 5
```

## Run The Demo UI

```powershell
python -m uvicorn emu_advisor.server:app --host 127.0.0.1 --port 8000
```

Open `http://127.0.0.1:8000` for the landing page, then **Open regulation assistant** to reach the chat UI.

Open `http://127.0.0.1:8000/admin?view=user` for the staff-facing chat (User mode).

Open `http://127.0.0.1:8000/admin?view=diagnostics` for the local diagnostics console (metrics, `/ask`, raw hits).

If `EMU_ADVISOR_ADMIN_TOKEN` is set, debug/admin endpoints require `Authorization: Bearer <token>` or `X-EMU-Admin-Token: <token>`. The browser admin console can be opened once with `http://127.0.0.1:8000/admin?admin_token=<token>`; the token is kept in browser session storage for same-session admin calls.

API endpoints:

- `GET /health`
- `GET /whoami`
- `GET /metrics`
- `GET /metrics/modes`
- `GET /analytics`
- `GET /corpus/status`
- `GET /llm/status`
- `POST /chat`
- `POST /ask`
- `POST /ask/stream`

`POST /chat` is the sanitized public endpoint. `POST /ask` supports `answer_style=extractive|generated|both` and returns full diagnostics for the admin console. Generated mode falls back to extractive when the local Ollama model is unavailable or a generation call fails.

## Qdrant Backend

Local development defaults to the in-memory store. Production profile requires Qdrant.

```powershell
$env:EMU_ADVISOR_VECTOR_BACKEND="qdrant"
$env:EMU_ADVISOR_QDRANT_URL="http://localhost:6333"
$env:EMU_ADVISOR_QDRANT_COLLECTION="emu_regulations"
python -m emu_advisor.index build --chunks artifacts\demo_corpus\latest\chunks.jsonl --backend qdrant --collection emu_regulations
```

For an embedded local Qdrant index, useful when Docker or a Qdrant server is unavailable:

```powershell
$env:EMU_ADVISOR_VECTOR_BACKEND="qdrant"
$env:EMU_ADVISOR_QDRANT_PATH="artifacts\qdrant\latest"
python -m emu_advisor.index build --chunks artifacts\demo_corpus\latest\chunks.jsonl --backend qdrant --collection emu_regulations --qdrant-path artifacts\qdrant\latest
```

For production profile:

```powershell
$env:EMU_ADVISOR_PROFILE="production"
$env:EMU_ADVISOR_ADMIN_TOKEN="<local-admin-token>"
python -m uvicorn emu_advisor.server:app --host 127.0.0.1 --port 8000
```

If Qdrant is unavailable in production profile, startup fails. In development/test profile, Qdrant falls back to the local store and `/corpus/status` reports the warning.

Check index connectivity:

```powershell
python -m emu_advisor.index health --backend qdrant --collection emu_regulations --qdrant-url http://localhost:6333
```

## Verification

```powershell
python -m unittest discover -s tests
python -m emu_advisor.validate_jsonl artifacts\demo_corpus\latest\chunks.jsonl --kind chunk
python -m emu_advisor.evaluation eval_sets\v1_gold.jsonl
python -m emu_advisor.evaluation eval_sets\v1_hard.jsonl
python -c "from emu_advisor.server import app; print(app.title)"
python tools\browser_smoke.py --start-server --skip-if-unavailable
python -m emu_advisor.readiness --out docs\BOARD_DEMO_READINESS.md
```

## Known Limits

- The 60-case set and 50-case hard set are assistant-curated and must be manually reviewed before calling either a human-reviewed gold set.
- Generated answers are optional; the latest bounded smoke run detected `qwen3:8b` but timed out at 2 seconds, so extractive fallback is the validated continuity path.
- Broad scholarship prompts run deterministic grouped subqueries; p50 is still under 1 second, but p95 can be higher than direct extractive questions.
- Qdrant adapter and CLI are implemented with mocked unit coverage and an embedded local Qdrant index build; no Docker/live Qdrant server run has been validated in this environment.
- Metrics are local demo metrics, not production service guarantees.
