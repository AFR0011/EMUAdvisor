# Project State

Last updated: 2026-09-06

Active branch: `remediation/evidence-security-portability`

Active batch: none; last closed batch `EMU-B001`

State: EMU-B001 complete with residual risks; presentation/publication/release gates remain blocked

## Product boundary

EMUAdvisor is an independent local-only English/Turkish assistant for public EMU regulations. It is not an official university service or final decision-maker. Runtime retrieval/generation remains local; ingestion alone may contact the exact official source host under the source policy.

## Current implementation

- FastAPI application with static user/diagnostic UI.
- Deterministic routing, hybrid local/Qdrant retrieval, cited extractive answers, refusal/clarification paths, and optional local Ollama generation.
- Explicit `fixture` versus `artifact` corpus mode. Fixture mode is limited to dev/test and visibly labeled; unsafe or missing configurations fail closed.
- Official ingestion requires exact-host HTTPS and validates redirects/final URLs. Local fixtures retain non-official provenance.
- Server-issued per-session capability protects public continuation/read/export/clear. Enumeration is admin-only and message-minimized.
- Transcript persistence, audit logging, and raw-query logging are separate positive opt-ins, all off by default.
- Platform-aware pinned dependencies and Ubuntu/Windows Python 3.12 core CI.

## Evaluation truth

`eval_sets/v1_gold.jsonl` contains 60 assistant-curated regression cases pending independent human review. The filename is retained for compatibility. The previous blanket `human_reviewed_verified` metadata has no durable per-case review evidence and is not relied upon.

New automated output uses `emu-advisor-automated-proxy/v2`. It measures observable retrieval/evidence/behavior/format/latency proxies. It does not semantically grade answer correctness, citation precision, claim grounding, or legal reliability. Historical percentages are legacy/unverified proxy output because their required corpus/metric manifests are unavailable here.

## Active blockers

- Independent human adjudication and evidence reference.
- Implemented immutable run manifests and a reproducible artifact-backed rerun.
- Corpus rights/distribution decision.
- Live Qdrant/Ollama/target hardware and deployment validation.
- Public-Internet identity/threat model beyond local session capabilities.

Therefore benchmark, presentation, publication, tag, release, deployment, and production-readiness claims remain blocked.

## EMU-B001 verification

Fresh independent testing returned `PASS_WITH_RISKS` on repaired snapshot
`d56a5dcdd63dbe2a1be14d42b3e16156250ab0394a849757c4269bac4ec11b26` after an initial
documentation-ordering `FAIL` was repaired and retested. Syntax, focused/full tests, evaluation
validation, review status, publication guard, browser smoke, Windows clean installation, dependency
audit, protected-input comparison, immutable CI refs, and tracked-tree credential scan passed.

Remote Ubuntu CI, live crawling, artifact-backed local services, immutable-run reproduction,
history-aware secret review, human adjudication, source-content rights, and Internet-grade identity
remain unverified or deferred. See `QA_REPORT.md` and `RISK_REGISTER.md`.

## Protected local data

Ignored `artifacts/**` and `logs/**` may contain private transcripts, queries, corpora, indexes, or generated evidence. EMU-B001 neither reads nor deletes existing files. Owner-approved cleanup or migration is a separate operation.

## Workflow authority

Use `DEV_STATE.md` for cycle status, `BLUEPRINT.md` for the accepted batch, `RISK_REGISTER.md` for risk status, and `QA_REPORT.md` for verified evidence.
