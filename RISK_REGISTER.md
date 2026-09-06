# Risk Register

Workflow schema: `agentic-workflow/v2`
Project: EMUAdvisor
Repository profile: mixed software/data-ML/research
Initialized: 2026-09-05

## Active risks

| ID | Severity | Status | Risk and evidence | Required control |
| --- | --- | --- | --- | --- |
| EMU-R01 | High | Mitigated in EMU-B001; residual gate open | Unsupported verified/human/university-review labels were removed from all 60 primary rows; the publication guard enforces a durable evidence contract. No independent semantic review or institutional attestation exists. | Keep benchmark/presentation/release blocked until privacy-safe durable human-review evidence is supplied. |
| EMU-R02 | High | Mitigated in EMU-B001; residual gate open | New reports use automated-proxy v2 labels and expected-evidence citation matching; historical semantic percentages are caveated before claims. Automated proxies still do not prove answer correctness or legal reliability. | Permit semantic claims only after independent adjudication and reproducible artifact-backed evaluation. |
| EMU-R03 | High | Mitigated for local use; public deployment gate open | Public session operations now require a server-issued capability and enumeration is minimized/admin-only; negative cross-session tests pass. This is session isolation, not Internet-grade identity. | Complete identity, abuse, and deployment threat-model review before any network-exposed demo. |
| EMU-R04 | High | Mitigated by default; owner-data action open | Persistence, audit logging, and raw-query logging are separate positive opt-ins and privacy tests pass. Existing ignored transcript/log files were intentionally neither read nor deleted. | Keep ignored files protected; owner decides cleanup/migration separately and validates opt-in retention in any deployment. |
| EMU-R05 | High | Mitigated synthetically; live verification open | Exact-host HTTPS, redirect-hop/final validation, credential/port rejection, and non-laundered fixture provenance are covered by tests. No live official-host crawl was run. | Run a separately authorized controlled live crawl and retain redirect/provenance evidence before source claims. |
| EMU-R06 | High | Mitigated in configuration; artifact gate open | Corpus mode is explicit, fixture is dev/test-only and visible, and invalid/unset/production-fixture configurations fail closed. Artifact-backed corpus startup was not exercised. | Validate a hashed nonempty artifact and target-service path before corpus-backed demonstration claims. |
| EMU-R07 | High | Mitigated locally; remote CI gate open | Platform markers, Windows dependencies, Windows/Ubuntu Python 3.12 CI, and immutable Action refs are present; a fresh Windows 3.12 install/full suite passed. Remote Ubuntu CI has not run on this branch. | Require green remote matrix checks after push before merge or release consideration. |
| EMU-R08 | Medium | Partially mitigated — later | Audit tooling and official Actions are pinned, but lock generation inputs/hashes remain incompletely documented. | Record reproducible lock-generation inputs and integrity hashes in a later dependency-maintenance batch. |
| EMU-R09 | High | Open — later | Published benchmark inputs/results lack immutable corpus/eval/commit/environment hashes and the public set has been iterated against implementation. | Add immutable run manifests and a held-out/adjudicated evaluation protocol before publishing benchmark claims. |
| EMU-R10 | Medium | Open — later | MIT covers software, not necessarily redistribution of regulation-derived corpus/evaluation content. | Keep corpus out of Git, publish minimal/synthetic fixtures and source/hash manifests, and obtain rights confirmation before substantial redistribution. |
| EMU-R11 | Medium | Open — later | Corpus/metric writers can overwrite canonical targets without a common staged atomic promotion policy. | Write unique run directories, validate, atomically promote pointers, and retain rollback metadata. |
| EMU-R12 | High | Mitigated — EMU-B001 | Bootstrap audit passed; scope, protected inputs, baseline, one writer, rollback, independent TEST, and docs-QA evidence are recorded. | Preserve the workflow evidence and reacquire a scoped lock for any future batch. |
| EMU-R13 | Medium | Open — later | Current-tree common-secret scan is clean, but a dedicated redacted history-aware scan is not recorded in the publication gate. | Run a history-aware secret/non-public-material review before presentation or release. |
| EMU-R14 | Medium | Open — maintenance | Browser smoke passed twice after one transient timeout; tests also emit a Starlette/httpx deprecation warning. Current evidence supports the batch but not long-term reliability. | Observe remote CI, investigate recurrence, and update the compatible dependency/test-client path before deprecation becomes failure. |

## Release rule

No benchmark, presentation, publication, network-exposed demo, tag, release, deployment, or
production-readiness claim may proceed while the residual gates in EMU-R01 through EMU-R07,
EMU-R09, EMU-R10, and EMU-R13 remain unresolved. A green remote Windows/Ubuntu CI result is also
required before merge consideration. Local implementation/testing may use synthetic fixtures without
reading or publishing ignored user artifacts. Full live crawling, Qdrant/Ollama validation, corpus
redistribution, and deletion of existing local transcripts/logs require separate explicit scope or
owner action.
