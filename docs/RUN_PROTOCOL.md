# Run Protocol

All commands run from the repository root. Python 3.12 is the supported verification target.

## Install

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install --upgrade pip
.\.venv\Scripts\python.exe -m pip install -r requirements-lock.txt
.\.venv\Scripts\python.exe -m pip check
```

`requirements-lock.txt` is platform-aware: `uvloop` is excluded on Windows. CI verifies both Windows and Ubuntu. Audit tooling is separately pinned in `requirements-audit.txt`.

## Safe test environment

```powershell
$env:EMU_ADVISOR_PROFILE = "test"
$env:EMU_ADVISOR_CORPUS_MODE = "fixture"
$env:EMU_ADVISOR_QUERY_REWRITE = "deterministic"
$env:EMU_ADVISOR_ENABLE_CHAT_PERSISTENCE = "0"
$env:EMU_ADVISOR_ENABLE_AUDIT_LOGGING = "0"
$env:EMU_ADVISOR_LOG_RAW_QUERY = "0"
```

## Core verification

```powershell
python tools/syntax_check.py
python -m unittest discover -s tests
python -m emu_advisor.evaluation eval_sets/v1_gold.jsonl
python -m emu_advisor.evaluation eval_sets/v1_hard.jsonl
python -m emu_advisor.evaluation eval_sets/emu_gold_seed.jsonl
python -m emu_advisor.eval_review status eval_sets/v1_gold.jsonl eval_sets/v1_hard.jsonl eval_sets/emu_gold_seed.jsonl
python tools/publication_guard.py
python tools/browser_smoke.py --start-server
```

## Dependency audit

```powershell
python -m pip install -r requirements-audit.txt
python -m pip_audit -r requirements-lock.txt
```

Record Python, pip, platform, audit-tool, commit, dependency-lock hash, environment, and command output. Do not write test output into protected `artifacts/**` or `logs/**`.

## Runtime modes

Development fixture mode requires explicit `EMU_ADVISOR_PROFILE=dev` and `EMU_ADVISOR_CORPUS_MODE=fixture`. It displays a synthetic-data warning.

Artifact mode requires explicit `EMU_ADVISOR_CORPUS_MODE=artifact` and a valid nonempty corpus at `artifacts/demo_corpus/latest/chunks.jsonl`. Production additionally requires `EMU_ADVISOR_ADMIN_TOKEN` and service-backed Qdrant. Missing/unknown/unsafe configurations fail closed.

Transcript persistence, audit logging, and raw-query logging are opt-in settings described in `SECURITY.md`. Never use real private questions or credentials in automated verification.
