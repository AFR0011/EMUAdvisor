# Test Strategy

Workflow schema: `agentic-workflow/v2`

## Levels

- Unit/API: `python -m unittest discover -s tests`.
- Evaluation schema: run `emu_advisor.evaluation` for all three tracked case sets.
- Review/provenance status: `emu_advisor.eval_review status` and publication guard.
- Dependency: clean install, `pip check`, and `pip-audit` from the locked snapshot.
- Browser: `python tools/browser_smoke.py --start-server` at desktop/mobile and light/dark.
- Artifact-backed metrics/live crawl/Qdrant/Ollama: only when explicitly authorized and inputs exist.

## Critical behaviors

- Exact-host source scope and redirect/file-fixture boundaries.
- Separate English/Turkish routing and refusal/clarification behavior.
- Honest proxy metric naming and expected-evidence citation matching.
- No unauthenticated cross-session transcript enumerate/read/export/clear.
- Memory/minimized privacy defaults and expiry behavior.
- Explicit fixture mode; real/production startup refuses a missing real corpus.
- Python 3.12 Windows and Ubuntu installation/core tests.

## Evidence boundary

Fixture/browser smoke proves UI/API behavior only. Schema validation is not a benchmark. Retrieval
metrics require a named corpus/evaluation manifest. Semantic answer correctness or human review
requires independent adjudication evidence and cannot be inferred from proxy tests.

## Release gate

Independent TEST must return PASS or PASS_WITH_RISKS. Presentation remains blocked while any High
evidence/privacy/source/fixture/portability risk lacks direct evidence.
