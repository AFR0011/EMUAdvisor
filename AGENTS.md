# AGENTS.md

## Repo Identity

- This workspace is the EMUAdvisor project for a local-only EMU Regulation Assistant.
- The root folder is the primary Git repository for future `emu-advisor` work.
- `.old/` is absent in this checkout. If historical prototype material is recovered from Git history, treat it as non-authoritative unless the user explicitly promotes it.
- The project is a research/prototype-to-product workspace, not a finished production app.

## Authority order

Use these sources in order:

1. `EMU_RAG_Current_System_Specs.md` for current product scope, architecture direction, V1 boundaries, and priority work.
2. `docs/PROJECT_STATE.md` for current repo status, active objective, risks, and next actions.
3. `docs/REPO_MAP.md` for structure, entrypoints, data flow, and active-versus-legacy surfaces.
4. `docs/RUN_PROTOCOL.md` for local setup and verification.
5. `.old/README.md` and `.old/backend/README.md` only for old-demo mechanics and commands.

`DEV_STATE.md` is the active workflow-state authority and the **Active batch** section of
`BLUEPRINT.md` is the accepted task/acceptance authority once a batch is planned.

## Product Boundaries

- V1 is a staff-facing demo for answering questions about official EMU rules and regulations.
- V1 source scope is exact-host HTTPS on `mevzuat.emu.edu.tr`; every redirect and final URL must remain in that boundary. File inputs are explicit test fixtures and never official-source evidence.
- Runtime behavior must remain local-only; do not add external API dependencies for answering, retrieval, embeddings, reranking, or generation.
- English and Turkish regulation corpora must remain separate; do not provide cross-corpus EN/TR search or comparison in V1 unless the project scope is explicitly changed.
- Answers must be grounded in retrieved evidence with citations and must refuse, clarify, or state uncertainty when support is insufficient.
- Do not expand V1 into advising, general university information, private records, workflow automation, or student/staff personal support without an explicit scope change.

## Operating Rules

- Prefer minimal, local diffs over broad refactors.
- Do not rename, move, or restructure major files unless necessary for the requested task.
- Distinguish clearly between code changes, experiment runs, result interpretation, and documentation/state updates.
- Update `docs/PROJECT_STATE.md` whenever a task materially changes current state, version status, verification status, or next steps.
- Update `docs/MIGRATION_BACKLOG.md` when migration priorities change or new blockers are discovered.
- Do not claim retrieval, answer quality, latency, or model behavior is validated unless the required crawl/index/model environment was actually run.
- Keep generated crawl, index, evaluation, and cache artifacts out of source control unless the user explicitly asks to preserve an artifact.
- Existing `__pycache__/` files in `.old/` are historical drift; do not use them as evidence of runtime correctness.

## Verification Rules

- The standard core command is `python -m unittest discover -s tests`; follow `docs/RUN_PROTOCOL.md` for the required explicit safe environment and broader checks.
- For documentation-only changes, verify file creation and internal consistency.
- For Python code changes, start with syntax checks that do not write bytecode, then run targeted imports or CLI commands as dependencies allow.
- For retrieval or answer changes, use a built index plus evaluation queries; do not substitute syntax checks for retrieval validation.
- For backend/UI changes, verify FastAPI startup and perform at least one local browser/API smoke check when dependencies and index artifacts exist.

## Protected paths

- `eval_sets/**`: evaluation inputs and review metadata; changes require explicit provenance and claim reconciliation.
- `artifacts/**`, `logs/**`, local Qdrant/index/corpus outputs, and chat transcripts: generated or potentially sensitive; do not commit them by default.
- `.env*`, tokens, local service configuration, reviewer identities, and any non-public university material.
- `EMU_RAG_Current_System_Specs.md`, `LICENSE`, Git history, remote `main`, tags, releases, and deployments.
- `.old/**`: ignored historical prototype evidence; do not promote or rewrite it without explicit scope.

## Required commands

Use the active environment and the narrowest applicable subset from `docs/RUN_PROTOCOL.md`.
Before closing a Python/security/evaluation batch, run at minimum:

```powershell
python tools\syntax_check.py
python -m unittest discover -s tests
python -m emu_advisor.evaluation eval_sets\v1_gold.jsonl
python -m emu_advisor.evaluation eval_sets\v1_hard.jsonl
python -m emu_advisor.evaluation eval_sets\emu_gold_seed.jsonl
python -m emu_advisor.eval_review status eval_sets\v1_gold.jsonl eval_sets\v1_hard.jsonl eval_sets\emu_gold_seed.jsonl
python tools\publication_guard.py
python tools\browser_smoke.py --start-server
```

Also run the dependency audit and platform-specific installation checks defined by the active
batch. Full live crawling, Qdrant, or Ollama work is not implicit and must be separately bounded.

## Done Criteria

End implementation tasks with:

1. Changed files.
2. Commands run.
3. Outputs created or updated.
4. Verification results.
5. Remaining risks or assumptions.
