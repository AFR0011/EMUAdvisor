# EMUAdvisor

Local RAG assistant for answering Eastern Mediterranean University regulation questions from official cited sources.

EMUAdvisor crawls official EMU regulation pages and linked PDFs, builds language-separated retrieval corpora, retrieves and reranks supporting evidence, and produces cited answers with refusal and clarification behavior when evidence is insufficient or the question falls outside the indexed regulation scope.

> **Independent project:** EMUAdvisor is research/software work and is not an official Eastern Mediterranean University administrative service. Its answers are informational and must not be treated as final university decisions.

## What this project demonstrates

- end-to-end RAG ingestion over official HTML and PDF sources;
- English/Turkish corpus routing and query understanding;
- hybrid retrieval with structured table evidence and optional Qdrant storage;
- extractive answers, optional local Ollama generation, and fallback behavior;
- citations, refusal/clarification policies, and conflict-aware responses;
- fixed-set evaluation, human-reviewed gold data, regression suites, and review tooling;
- FastAPI APIs, local diagnostics, browser smoke testing, CI, and reproducible dependency snapshots.

## Architecture

```text
Official EMU HTML/PDF sources
          |
          v
 crawler -> parser/table extraction -> normalized chunks
          |                             |
          |                             v
          |                    local or Qdrant index
          |                             |
          +-----------------------------+
                                        v
question -> language/query understanding -> hybrid retrieval
                                        |
                                        v
                     evidence + answerability decision
                         |                     |
                         v                     v
                 extractive answer       refuse/clarify
                         |
                         +---- optional local Ollama generation
                                        |
                                        v
                              cited user response
```

## Evaluation snapshot

The primary benchmark is `eval_sets/v1_gold.jsonl`, a **60-case human-reviewed and verified gold set** reviewed by the project author and university staff.

Recorded extractive results on the fixed corpus snapshot:

| Metric | `v1_gold` |
|---|---:|
| Cases | 60 |
| Retrieval top-1 | 92.31% |
| Retrieval top-3 | 98.08% |
| Retrieval top-5 | 100.00% |
| Response accuracy | 100.00% |
| Rejection accuracy | 100.00% |
| Clarification accuracy | 100.00% |
| Citation coverage | 100.00% |
| Extractive latency p50 | 674 ms |
| Extractive latency p95 | 1,267 ms |

These are local results on a fixed benchmark and corpus snapshot, **not production-service guarantees or universal model-quality claims**.

Additional evaluation material is intentionally separated:

- `eval_sets/v1_hard.jsonl`: 50-case hard regression suite focused on table/broad-query/refusal behavior;
- `eval_sets/emu_gold_seed.jsonl`: provisional evaluation seed retained under its historical filename until it completes the same review process.

See `docs/DEMO_METRICS_SNAPSHOT.md` for the full recorded snapshot and `PUBLICATION.md` for evaluation/publication terminology.

## Corpus snapshot

The recorded demo corpus contains:

- 8,714 chunks from 119 official sources;
- 22 linked official PDFs;
- 3,878 English and 4,836 Turkish chunks;
- structured table summaries, row-level table chunks, and derived table facts.

Generated crawl/index artifacts are intentionally ignored and are not committed to the repository.

## Setup

Python 3.12 is the CI reference environment.

For the reproducible portfolio/demo environment:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements-lock.txt
```

`requirements.txt` and `requirements-dev.txt` retain the broader dependency declarations; `requirements-lock.txt` records the exact tested snapshot used by CI.

Optional local services:

- Ollama generation model: `qwen3:8b`;
- Ollama embedding model: `qwen3-embedding:4b`;
- Qdrant for service-backed vector storage.

The answering/retrieval path does not require external hosted LLM APIs.

## Build a local corpus

```powershell
python -m emu_advisor.pipeline build `
  --seed https://mevzuat.emu.edu.tr/content.htm `
  --seed https://mevzuat.emu.edu.tr/Content-en.htm `
  --out artifacts\demo_corpus\latest `
  --max-pages 1000 `
  --include-pdfs

python -m emu_advisor.validate_jsonl `
  artifacts\demo_corpus\latest\chunks.jsonl `
  --kind chunk
```

The application loads `artifacts/demo_corpus/latest/chunks.jsonl` when present and otherwise falls back to a small fixture corpus for development/testing.

## Run the application

```powershell
python -m uvicorn emu_advisor.server:app --host 127.0.0.1 --port 8000
```

Then open:

- `http://127.0.0.1:8000` for the landing page;
- `http://127.0.0.1:8000/admin?view=user` for the staff-facing chat;
- `http://127.0.0.1:8000/admin?view=diagnostics` for local diagnostics.

### Admin authentication

Protected profiles use `EMU_ADVISOR_ADMIN_TOKEN`.

```powershell
$env:EMU_ADVISOR_PROFILE="production"
$env:EMU_ADVISOR_ADMIN_TOKEN="<local-admin-token>"
```

API clients send the token through either:

```text
Authorization: Bearer <token>
```

or:

```text
X-EMU-Admin-Token: <token>
```

The browser diagnostics view provides a password-style token field. The value is stored only in the current tab's `sessionStorage` and sent through the `Authorization` header. **Admin tokens are not accepted from URL query parameters.**

See `SECURITY.md` for the security boundary and deployment cautions.

## API surface

Public/user path:

- `GET /health`
- `GET /whoami`
- `POST /chat`
- `POST /chat/stream`

Diagnostics/admin path:

- `GET /metrics`
- `GET /metrics/modes`
- `GET /analytics`
- `GET /corpus/status`
- `GET /llm/status`
- `POST /ask`
- `POST /ask/stream`

`POST /chat` returns the sanitized user-facing response. `POST /ask` exposes richer retrieval/generation diagnostics for the local admin console.

## Qdrant backend

Development defaults to the local in-memory store. A production profile requires Qdrant.

```powershell
$env:EMU_ADVISOR_VECTOR_BACKEND="qdrant"
$env:EMU_ADVISOR_QDRANT_URL="http://localhost:6333"
$env:EMU_ADVISOR_QDRANT_COLLECTION="emu_regulations"

python -m emu_advisor.index build `
  --chunks artifacts\demo_corpus\latest\chunks.jsonl `
  --backend qdrant `
  --collection emu_regulations
```

Embedded local Qdrant can also be used for development when a service is unavailable.

## Evaluation and review

Run the verified gold set:

```powershell
python -m emu_advisor.evaluation eval_sets\v1_gold.jsonl
python -m emu_advisor.eval_review status eval_sets\v1_gold.jsonl
```

Run auxiliary regression/evaluation material:

```powershell
python -m emu_advisor.evaluation eval_sets\v1_hard.jsonl
python -m emu_advisor.evaluation eval_sets\emu_gold_seed.jsonl
python -m emu_advisor.eval_review status eval_sets\v1_hard.jsonl eval_sets\emu_gold_seed.jsonl
```

Metrics runs write ignored artifacts such as `metrics.json`, `per_case.csv`, and review CSVs under `artifacts/`.

## Verification

The GitHub Actions pipeline uses the pinned dependency snapshot and requires both core verification and the browser smoke test.

Equivalent local checks:

```powershell
python tools\publication_guard.py
python -m unittest discover -s tests
python -m emu_advisor.evaluation eval_sets\v1_gold.jsonl
python -m emu_advisor.evaluation eval_sets\v1_hard.jsonl
python -m emu_advisor.evaluation eval_sets\emu_gold_seed.jsonl
python tools\browser_smoke.py --start-server
```

CI additionally audits the pinned Python dependencies with `pip-audit`.

## Known limits

- The recorded metrics describe a fixed local evaluation/corpus snapshot, not production availability.
- `v1_gold` is verified; `v1_hard` and `emu_gold_seed` retain separate review status and should not be silently merged into the gold claim.
- Generated answers are optional and fallback-safe; the recorded bounded `qwen3:8b` smoke run timed out at a 2-second generation limit.
- A service-backed Qdrant production deployment and target production hardware have not yet been validated in the recorded environment.
- The repository is intended for local research, evaluation, and demonstration; public Internet deployment requires an independent security/deployment review.

## License

MIT. See `LICENSE`.
