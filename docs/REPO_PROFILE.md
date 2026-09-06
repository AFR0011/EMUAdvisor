# Repository Profile

Workflow schema: `agentic-workflow/v2`
Project: EMUAdvisor
Repository profile: mixed
Initialized: 2026-09-05

## Classification

- Primary type: `mixed`
- Secondary traits: software, data-ml
- Confidence: high
- Files scanned: 84
- Scan truncated: False

## Evidence

```json
{
  "software": [
    "dir:tests",
    "ext:.py(40)",
    "ext:.js(3)",
    "keywords:migration"
  ],
  "data-ml": [
    "file:requirements.txt",
    "keywords:evaluation,metrics"
  ],
  "documentation": [
    "dir:docs"
  ],
  "research": [
    "keywords:citation"
  ]
}
```

## Existing governance discovered

- AGENTS.md
- docs/REPO_MAP.md
- docs/PROJECT_STATE.md
- README.md

## Discovered entry points

- `emu_advisor\index.py`
- `emu_advisor\server.py`

## Discovered commands

- Unit suite: `python -m unittest discover -s tests`
- Evaluation schema validation: `python -m emu_advisor.evaluation <case-set>`
- Review-status summary: `python -m emu_advisor.eval_review status <case-set...>`
- Publication guard: `python tools/publication_guard.py`
- Browser smoke: `python tools/browser_smoke.py --start-server`
- Backend: `python -m uvicorn emu_advisor.server:app --host 127.0.0.1 --port 8000`
- Optional generated artifacts, live crawl, Qdrant, and Ollama commands are documented in `docs/RUN_PROTOCOL.md` and are not implicit verification.

## Protected/generated boundaries

### Protected candidates

- `eval_sets/**`, system specification, license, Git history, remote/release state, credentials,
  reviewer identity, private university material, and ignored `.old/**` prototype evidence.

### Generated-output candidates

- `artifacts/**`, `logs/**`, crawl/index/Qdrant outputs, chat transcripts, caches, and local environments.

## Equivalent-file mappings

- `EMU_RAG_Current_System_Specs.md` is the product/system scope authority.
- Existing `docs/PROJECT_STATE.md`, `docs/REPO_MAP.md`, `docs/RUN_PROTOCOL.md`, and
  `docs/VERSION_LOG.md` satisfy their canonical workflow purposes and were preserved.

## Profile review

- [x] Primary type and traits confirmed from application, tests, evaluation code, and audit evidence.
- [x] Authority and protected/generated paths reconciled with `AGENTS.md`.
- [x] Required commands confirmed from `docs/RUN_PROTOCOL.md` and CI.
