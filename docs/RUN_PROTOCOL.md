# Run Protocol

Last updated: 2026-04-30

## Current Rule

There is no single standard test command. Use the smallest verification level that matches the change, and do not claim higher validation than was actually run.

## Setup

Run commands from the old-demo codebase unless a future root app is created:

```powershell
cd "C:\Users\Ali\Desktop\EMUAdvisor\NLPCrawler (Old Demo)"
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r backend\requirements.txt
```

For full pipeline, retrieval, reranking, and evaluation work:

```powershell
pip install -r requirements-full.txt
```

Install `torch` separately for the target CUDA/CPU environment. Do not assume a CUDA wheel.

## Verification Ladder

1. Documentation-only changes

```powershell
Get-ChildItem -Recurse -File docs,AGENTS.md
```

Check that docs do not contradict `EMU_RAG_Current_System_Specs.md`.

2. Python syntax check without writing bytecode

```powershell
@'
import ast
from pathlib import Path
root = Path(r"C:\Users\Ali\Desktop\EMUAdvisor\NLPCrawler (Old Demo)")
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

3. Backend import/startup smoke, when backend dependencies are installed

```powershell
cd "C:\Users\Ali\Desktop\EMUAdvisor\NLPCrawler (Old Demo)"
python -c "from backend.server import app; print(app.title)"
```

4. Pipeline build smoke, when network access to official EMU sources is allowed

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

5. Retrieval smoke, when an index exists

```powershell
python 6.TestRetrieve.py --index-dir index_v4 --lang en --q "attendance requirement" --k 8
python 7.RetrieveHybrid.py --index-dir index_v4 --q "salary scales" --lang auto --k 8
python 8.RerankMultilingualV7_3.py --index-dir index_v4 --q "high honour criteria" --lang auto --k 8
```

6. Backend/API/UI smoke, when an index and backend dependencies exist

```powershell
python -m uvicorn backend.server:app --host 127.0.0.1 --port 8000
```

Then check:

- `GET http://127.0.0.1:8000/whoami`
- `POST http://127.0.0.1:8000/ask`
- Browser load at `http://127.0.0.1:8000`

7. Evaluation gate, when a built index and query set exist

```powershell
python EvaluateRetrieval.py --index-dir index_v4 --out eval_run --k 8
```

For V1 readiness, evaluate 50-60 English/Turkish questions and verify that correct supporting evidence appears in the top 5 when the answer exists.

## Runtime Service Notes

- Ollama is optional for old-demo answer synthesis but required when `backend/config.json` has `llm.enabled` set to `true`.
- Current config expects Ollama at `http://localhost:11434`.
- Qdrant is a target architecture direction, not an implemented dependency in the old demo.

## Claiming Results

- Syntax checks validate parseability only.
- Backend import checks validate import/startup only.
- Retrieval smoke checks validate that commands run against a present index; they do not prove answer quality.
- Evaluation results are the only acceptable evidence for retrieval-quality claims.
- Manual UI/API checks are required before claiming a user-facing flow works.
