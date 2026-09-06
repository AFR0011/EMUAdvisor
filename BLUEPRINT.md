# Blueprint

Workflow schema: `agentic-workflow/v2`
Project: EMUAdvisor
Repository profile: mixed
Initialized: 2026-09-05

## Product objective

Maintain a local-only English/Turkish EMU regulation assistant whose source provenance, automated evidence, privacy boundary, and supported development environments are stated and verified honestly.

## Active batch

Status: READY
Batch ID: EMU-B001

### Objective

Correct unsupported evaluation-review claims; label automated measurements as regression/evidence proxies; require expected-evidence citation matches; isolate transcripts with server-issued per-session capabilities; make transcript persistence and raw-query logging opt-in; require an explicit fixture or artifact corpus mode; enforce exact HTTPS official-source scope through redirects; and make the pinned Python 3.12 environment verifiable on Windows and Ubuntu.

### Intended files

- Evaluation/evidence: `eval_sets/v1_gold.jsonl`, `emu_advisor/evaluation.py`, `emu_advisor/metrics.py`, `emu_advisor/eval_review.py`, `emu_advisor/readiness.py`, `tools/publication_guard.py`, and focused tests.
- Transcript/privacy: `emu_advisor/conversation_store.py`, `emu_advisor/audit_log.py`, `emu_advisor/server.py`, relevant static UI files, browser smoke, and focused tests.
- Corpus/source provenance: `emu_advisor/corpus.py`, `emu_advisor/pipeline.py`, ingestion/schema files only as required, and synthetic fixture tests.
- Portability/CI: dependency declarations, `.github/workflows/ci.yml`, and narrowly scoped verification tooling.
- Current claim/governance surfaces: README, publication/security/readiness/state/run/evaluation documentation, this workflow pack, and authorized `shared/**` records.

### Allowed adjacent files

- A small provenance helper or focused security/provenance test module.
- A pinned audit requirements file or narrowly scoped CI-maintenance configuration.
- `static/landing.html`, `static/admin-diagnostics.js`, or `docs/ARCHITECTURE.md` only when needed to expose the accepted corpus/session boundary accurately.

### Out of scope

- Human semantic grading, institutional attestation, or invented reviewer evidence.
- Live crawl, Qdrant/Ollama benchmark, corpus/index/metric publication, or transcript/log inspection.
- Retrieval/model-quality improvements, full identity architecture, manifest signing/implementation, or licensing conclusions.
- Repository/history/name changes, presentation media, tag, release, deployment, merge, or production-readiness claim.
- Any change to `EMU_RAG_Current_System_Specs.md`, `eval_sets/v1_hard.jsonl`, `eval_sets/emu_gold_seed.jsonl`, `.old/**`, `artifacts/**`, or `logs/**`.

### Preconditions

- Record the baseline branch/HEAD/status and pre-existing bootstrap changes.
- Acquire one cooperative root lock before source edits; keep root as canonical writer.
- Preserve evaluation identities/content/order; only provenance/adjudication fields in `v1_gold.jsonl` are authorized.
- Use synthetic fixtures and temporary paths only. Do not read or alter existing ignored transcripts/logs.
- Resolve official GitHub Action releases to real immutable commit SHAs before pinning them.

### Implementation plan

1. Relabel all 60 `v1_gold` rows as assistant-curated and pending independent review; clear unsupported correctness/citation judgments while preserving every protected content field and row order.
2. Require durable evidence references for any future human-reviewed status. Version new metric output as automated proxy evidence and replace semantic-sounding fields with precise retrieval, behavior, citation-presence, expected-evidence citation, format, and latency labels.
3. Match citations to expected chunk evidence, falling back to exact normalized source only when no expected chunks exist; conflict cases require the distinct expected evidence sides.
4. Issue a random session ID and separate random capability server-side. Store only a capability hash; require the capability for continuation/read/export/clear; make enumeration admin-only and omit raw last-message text by default.
5. Disable transcript persistence and raw-query logging by default. Keep opt-ins explicit, bounded, pruned, and tested using temporary paths.
6. Require explicit `fixture` or `artifact` corpus mode. Permit fixture mode only in development/test, fail closed for missing/invalid artifacts and unsafe profiles, expose the mode through status endpoints, and show an unavoidable fixture warning in the user UI.
7. Validate HTTPS, exact host, credentials, port, every redirect target, and final URL before attribution. File fixtures require explicit fixture mode and retain non-laundered, path-safe fixture provenance.
8. Make the lock platform-aware, add Windows and Ubuntu Python 3.12 core CI, pin official actions to verified full SHAs, and pin audit tooling.
9. Add focused negative/regression tests, reconcile current public claims, and define the design-only immutable run-manifest contract without claiming historical reproducibility.
10. Run focused then full verification, freeze the diff, obtain an independent tester verdict, and reconcile QA/state/risk records without removing residual blockers.

### Acceptance criteria

- `v1_gold.jsonl` remains 60 rows with protected fields/order unchanged; all rows are assistant-curated/pending independent review with `is_correct` and `citation_ok` null and no human/university-review claim.
- Validation/review status reports 60 pending cases; a self-asserted verified row without the evidence contract fails publication checks.
- New reports use a versioned automated-proxy schema and do not present response accuracy, answer correctness, citation precision/coverage, groundedness, or presentability as semantic evidence.
- Wrong citations fail expected-evidence matching; matching chunks pass; source fallback applies only without expected chunks; conflict cases require both evidence sides.
- Legacy metrics are labeled legacy/unverified and are not rendered as current semantic claims.
- Public session creation produces a distinct opaque ID and high-entropy capability; only the hash is stored. Continuation/read/export/clear require the matching capability and fail uniformly otherwise.
- Public enumeration is unavailable; admin enumeration requires a configured valid admin token and omits raw last-user-message text by default.
- With no opt-in, no transcript file is loaded or written and audit output contains no raw question, session ID, capability, token, or direct identifier. Explicit opt-ins work only against temporary test paths.
- Corpus mode is explicit. Fixture starts only in dev/test and is visibly reported; artifact mode requires a valid nonempty artifact; unsafe unset/unknown/production fixture configurations fail closed.
- Real requests stay on exact-host HTTPS through every redirect/final URL. File fixtures cannot be attributed to an official EMU URL or expose an absolute local path.
- The lock installs under clean Windows and Ubuntu CPython 3.12; core tests run on both CI platforms, browser smoke remains green on its supported runner, and official action refs are verified immutable SHAs.
- Public/governance docs retain the benchmark/presentation/release block and accurately label historical metrics as legacy automated proxies.
- Protected inputs remain unchanged; no live services, generated private artifacts, tag, release, deployment, or presentation action occurs.
- Full verification passes and the independent tester returns `PASS` or `PASS_WITH_RISKS`.

### Verification

- Baseline/final: `git status --short --branch`, `git rev-parse HEAD`, `git diff --check`, changed-file inventory, and protected-path diff.
- Python 3.12 with explicit test profile/fixture mode: focused tests, full unittest discovery, all three evaluation validations, review status, publication guard, and browser smoke.
- Focused tests for evaluation transformation, proxy schema/citations, capability isolation, admin enumeration, privacy defaults, corpus startup matrix, redirect prevalidation, and fixture provenance.
- Clean temporary Windows Python 3.12 environment: install pinned lock, imports, full core checks, and pinned dependency audit.
- CI structure check: Windows/Ubuntu Python 3.12, explicit safe environment, and 40-character official-action SHAs with release comments.
- Claim scan and independent tester review against a frozen final diff.

### Protected inputs

- `EMU_RAG_Current_System_Specs.md`; all evaluation content except authorized `v1_gold` provenance/adjudication fields; all generated/private `artifacts/**` and `logs/**`; environment files, credentials, identities, private attestations, `.old/**`, `LICENSE`, Git history, remote `main`, tags, releases, and deployments.

### Risks

- The capability boundary is local session isolation, not full Internet identity/authentication.
- Legacy persisted sessions intentionally become unavailable to public callers and remain untouched.
- Expected-source fallback is weaker than chunk matching and must be reported as such.
- Windows resolution may expose further platform incompatibilities; stop rather than loosen reproducibility.
- Source-scope hardening may reject legitimate but out-of-policy redirects; record rather than broaden silently.
- The immutable-manifest work is design-only. Human review, live corpus rerun, corpus rights, deployment, and presentation remain open.

### Rollback

- Use targeted reverts of EMU-B001 commits; never reset or overwrite bootstrap/user work.
- Do not restore unsupported review/semantic claims for compatibility.
- Do not migrate, delete, or rewrite existing private artifacts. Retain fail-closed source/corpus behavior if a legitimate redirect or environment is unsupported, and record `STOP_NEEDS_HUMAN` when a portable lock cannot be proven.

### Evidence required for done

- Matching accepted plan/state, passing bootstrap audit, released-at-close lock, and pre/post file inventory.
- Machine-readable proof that only authorized `v1_gold` fields changed.
- Passing provenance/guard, proxy/citation, transcript/privacy, corpus-mode/source-scope, clean Windows install/audit, full suite, browser smoke, CI, and diff-integrity checks.
- Green independent tester verdict and docs-QA reconciliation that preserves all residual risks and the presentation/release block.
