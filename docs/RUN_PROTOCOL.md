# Run Protocol

Last updated: 2026-05-05

## Current Rule

There is no single standard test command. Use the smallest verification level that matches the change, and do not claim higher validation than was actually run.

## Setup

Run active project commands from the root repo. Use `.old/` only as a legacy reference until code is promoted or replaced.

Root setup:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements-dev.txt
```

Legacy demo setup, if needed:

```powershell
cd "C:\Users\Ali\Desktop\EMUAdvisor\.old"
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r backend\requirements.txt
```

For legacy full pipeline, retrieval, reranking, and evaluation work:

```powershell
pip install -r .old\requirements-full.txt
```

Install `torch` separately for the target CUDA/CPU environment. Do not assume a CUDA wheel.

## Verification Ladder

1. Documentation-only changes

```powershell
Get-ChildItem -Recurse -File docs,AGENTS.md
```

Check that docs do not contradict `EMU_RAG_Current_System_Specs.md`.

2. Python syntax check without writing bytecode

For active root code:

```powershell
@'
import ast
from pathlib import Path
root = Path(r"C:\Users\Ali\Desktop\EMUAdvisor")
failed = []
checked = 0
for base in [root / "emu_advisor", root / "tests"]:
    for path in base.rglob("*.py"):
        checked += 1
        try:
            ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        except Exception as exc:
            failed.append((str(path), repr(exc)))
if failed:
    for path, exc in failed:
        print(path, exc)
    raise SystemExit(1)
print(f"syntax ok: {checked} files")
'@ | python -
```

For legacy `.old/` reference code:

```powershell
@'
import ast
from pathlib import Path
root = Path(r"C:\Users\Ali\Desktop\EMUAdvisor\.old")
failed = []
for path in root.rglob("*.py"):
    if ".git" in path.parts or "__pycache__" in path.parts:
        continue
    try:
        ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    except Exception as exc:
        failed.append((str(path), repr(exc)))
if failed:
    for path, exc in failed:
        print(path, exc)
    raise SystemExit(1)
print("syntax ok")
'@ | python -
```

3. Root schema unit tests

```powershell
python -m unittest discover -s tests
python -m emu_advisor.validate_jsonl tests\fixtures\canonical_chunks.valid.jsonl --kind chunk
python -m emu_advisor.evaluation eval_sets\v1_gold.jsonl
python -m emu_advisor.evaluation eval_sets\v1_hard.jsonl
python -c "from emu_advisor.server import app; print(app.title)"
python -m emu_advisor.eval_review status eval_sets\v1_gold.jsonl eval_sets\v1_hard.jsonl eval_sets\emu_gold_seed.jsonl
```

4. Backend import/startup smoke, when backend dependencies are installed

```powershell
cd "C:\Users\Ali\Desktop\EMUAdvisor\.old"
python -c "from backend.server import app; print(app.title)"
```

5. Root demo corpus build, when network access to official EMU sources is allowed

```powershell
python -m emu_advisor.pipeline build --seed https://mevzuat.emu.edu.tr/content.htm --seed https://mevzuat.emu.edu.tr/Content-en.htm --out artifacts\demo_corpus\latest --max-pages 1000 --include-pdfs
python -m emu_advisor.validate_jsonl artifacts\demo_corpus\latest\chunks.jsonl --kind chunk
```

Generated artifacts are ignored by Git and written under `artifacts/`.

6. Root metrics gate, when a built corpus artifact exists

```powershell
python -m emu_advisor.metrics run --cases eval_sets\v1_gold.jsonl --chunks artifacts\demo_corpus\latest\chunks.jsonl --out artifacts\metrics\latest
python -m emu_advisor.metrics run --cases eval_sets\v1_hard.jsonl --chunks artifacts\demo_corpus\latest\chunks.jsonl --out artifacts\metrics\hard_latest
python -m emu_advisor.metrics run --all-modes --cases eval_sets\emu_gold_seed.jsonl --chunks artifacts\demo_corpus\latest\chunks.jsonl --out artifacts\metrics\mode_comparison
```

Human-review artifact helpers:

```powershell
python -m emu_advisor.eval_review export-csv --cases eval_sets\v1_gold.jsonl --out artifacts\review\v1_gold_review.csv
python -m emu_advisor.eval_review bind-seed --cases eval_sets\emu_gold_seed.jsonl --chunks artifacts\demo_corpus\latest\chunks.jsonl --out artifacts\review\emu_gold_seed.bound.jsonl
```

To attempt local generated-mode metrics with a bounded Ollama timeout:

```powershell
python -m emu_advisor.metrics run --cases eval_sets\v1_gold.jsonl --chunks artifacts\demo_corpus\latest\chunks.jsonl --out artifacts\metrics\latest_generated --include-generation --ollama-model qwen3:8b --ollama-timeout-s 2
```

7. Root Qdrant index build, when Qdrant is available

```powershell
$env:EMU_ADVISOR_VECTOR_BACKEND="qdrant"
$env:EMU_ADVISOR_QDRANT_URL="http://localhost:6333"
$env:EMU_ADVISOR_QDRANT_COLLECTION="emu_regulations"
python -m emu_advisor.index build --chunks artifacts\demo_corpus\latest\chunks.jsonl --backend qdrant --collection emu_regulations
python -m emu_advisor.index health --backend qdrant --collection emu_regulations --qdrant-url http://localhost:6333
```

For embedded local Qdrant storage without a running Qdrant server:

```powershell
$env:EMU_ADVISOR_VECTOR_BACKEND="qdrant"
$env:EMU_ADVISOR_QDRANT_PATH="artifacts\qdrant\latest"
python -m emu_advisor.index build --chunks artifacts\demo_corpus\latest\chunks.jsonl --backend qdrant --collection emu_regulations --qdrant-path artifacts\qdrant\latest
```

For production-profile server startup, Qdrant is required:

```powershell
$env:EMU_ADVISOR_PROFILE="production"
python -m uvicorn emu_advisor.server:app --host 127.0.0.1 --port 8000
```

8. Legacy pipeline reference, when old-demo commands are needed

```powershell
python 1.BasicCrawlV2.py --out mevzuat_crawl --seed https://mevzuat.emu.edu.tr/content.htm --max-pages 20
python 2.ClassifyContentV2.py --crawl-dir mevzuat_crawl --out classified_v2.2.jsonl
python 3.ExtractRowsV7.py --crawl_dir mevzuat_crawl --classified classified_v2.2.jsonl --out rows_v7.jsonl
python 4.CompileDataV6.py --crawl_dir mevzuat_crawl --rows rows_v7.jsonl --out docs_v6.jsonl
python 5.ChunkerV5.py --in docs_v6.jsonl --out chunks_v5.jsonl --max-words 450 --overlap-words 80
python 5.2.DedupChunks.py --in chunks_v5.jsonl --out chunks_dedup.jsonl --report dedup_report.json
python 5.3.PostprocessChunks.py --in chunks_dedup.jsonl --out chunks_post.jsonl --min-short 240 --split-threshold 2200
python 6.BuildIndex.py --in chunks_post.jsonl --out-dir index_v4 --embed-model intfloat/multilingual-e5-base --device cpu
```

9. Legacy retrieval smoke, when an old-demo index exists

```powershell
python 6.TestRetrieve.py --index-dir index_v4 --lang en --q "attendance requirement" --k 8
python 7.RetrieveHybrid.py --index-dir index_v4 --q "salary scales" --lang auto --k 8
python 8.RerankMultilingualV7_3.py --index-dir index_v4 --q "high honour criteria" --lang auto --k 8
```

10. Root Backend/API/UI smoke

```powershell
python -m uvicorn emu_advisor.server:app --host 127.0.0.1 --port 8000
```

Then check:

- `GET http://127.0.0.1:8000/metrics`
- `GET http://127.0.0.1:8000/metrics/modes`
- `GET http://127.0.0.1:8000/analytics`
- `GET http://127.0.0.1:8000/corpus/status`
- `GET http://127.0.0.1:8000/llm/status`
- `POST http://127.0.0.1:8000/chat`
- `POST http://127.0.0.1:8000/ask`
- Browser load at `http://127.0.0.1:8000`
- Browser load at `http://127.0.0.1:8000/admin`

If `EMU_ADVISOR_ADMIN_TOKEN` is set, call admin/debug endpoints with either:

```powershell
$headers = @{ Authorization = "Bearer $env:EMU_ADVISOR_ADMIN_TOKEN" }
Invoke-RestMethod http://127.0.0.1:8000/metrics -Headers $headers
```

For optional browser QA:

```powershell
python tools\browser_smoke.py --start-server --skip-if-unavailable
```

For local load reporting:

```powershell
python -m emu_advisor.load_test --chunks artifacts\demo_corpus\latest\chunks.jsonl --active-sessions 50 --max-workers 4
```

For local model probes:

```powershell
python -m emu_advisor.benchmark embedding --cases eval_sets\v1_gold.jsonl --chunks artifacts\demo_corpus\latest\chunks.jsonl --embedding hash
python -m emu_advisor.benchmark generation --cases eval_sets\v1_gold.jsonl --chunks artifacts\demo_corpus\latest\chunks.jsonl --model qwen3:8b --timeout-s 30 --limit 5
```

For board readiness:

```powershell
python -m emu_advisor.readiness --out docs\BOARD_DEMO_READINESS.md
```

11. Legacy evaluation gate, when an old-demo index and query set exist

```powershell
python EvaluateRetrieval.py --index-dir index_v4 --out eval_run --k 8
```

For V1 readiness, evaluate 50-60 English/Turkish questions and verify that correct supporting evidence appears in the top 5 when the answer exists.

## Runtime Service Notes

- Ollama is optional for old-demo answer synthesis but required when `backend/config.json` has `llm.enabled` set to `true`.
- Root generated-answer mode defaults to local Ollama model `qwen3:8b` at `http://localhost:11434` with `EMU_ADVISOR_LLM_TIMEOUT_S=30` and `EMU_ADVISOR_LLM_PROBE_TIMEOUT_S=10` unless overridden.
- Root demo indexing can use local Ollama embeddings with `EMU_ADVISOR_EMBEDDING=ollama`; otherwise it uses the deterministic hash fallback.
- Qdrant server integration now has a root adapter and index build CLI. Development/test profile falls back to the local store; production profile requires Qdrant.

## Demo UI

```powershell
python -m uvicorn emu_advisor.server:app --host 127.0.0.1 --port 8000
```

Open `http://127.0.0.1:8000`.

## Claiming Results

- Syntax checks validate parseability only.
- Backend import checks validate import/startup only.
- Local retrieval smoke checks validate code paths and demo fixtures; they do not prove real corpus answer quality.
- Live `emu_advisor.metrics` outputs are the acceptable evidence for current demo retrieval, refusal, citation, failure-analysis, and latency claims.
- Manual UI/API checks are required before claiming a user-facing flow works.
