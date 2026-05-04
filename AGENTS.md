# AGENTS.md

## Repo Identity

- This workspace is the EMUAdvisor project for a local-only EMU Regulation Assistant.
- The root folder is the primary Git repository for future `emu-advisor` work.
- `.old/` is an ignored local archive of the previous NLPCrawler demo; treat it as legacy/prototype reference code unless the user explicitly promotes or imports it.
- The project is a research/prototype-to-product workspace, not a finished production app.

## Source Of Truth

Use these sources in order:

1. `EMU_RAG_Current_System_Specs.md` for current product scope, architecture direction, V1 boundaries, and priority work.
2. `docs/PROJECT_STATE.md` for current repo status, active objective, risks, and next actions.
3. `docs/REPO_MAP.md` for structure, entrypoints, data flow, and active-versus-legacy surfaces.
4. `docs/RUN_PROTOCOL.md` for local setup and verification.
5. `.old/README.md` and `.old/backend/README.md` only for old-demo mechanics and commands.

## Product Boundaries

- V1 is a staff-facing demo for answering questions about official EMU rules and regulations.
- V1 source scope is `mevzuat.emu.edu.tr` plus official PDFs linked from or belonging to that regulation source set.
- Runtime behavior must remain local-only; do not add external API dependencies for answering, retrieval, embeddings, reranking, or generation.
- English and Turkish regulation corpora must remain separate unless a user explicitly asks for cross-corpus search.
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

- This repo has no single standard test command yet. Follow `docs/RUN_PROTOCOL.md`.
- For documentation-only changes, verify file creation and internal consistency.
- For Python code changes, start with syntax checks that do not write bytecode, then run targeted imports or CLI commands as dependencies allow.
- For retrieval or answer changes, use a built index plus evaluation queries; do not substitute syntax checks for retrieval validation.
- For backend/UI changes, verify FastAPI startup and perform at least one local browser/API smoke check when dependencies and index artifacts exist.

## Done Criteria

End implementation tasks with:

1. Changed files.
2. Commands run.
3. Outputs created or updated.
4. Verification results.
5. Remaining risks or assumptions.
