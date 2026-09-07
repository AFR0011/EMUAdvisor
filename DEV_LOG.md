# Development Log

Workflow schema: `agentic-workflow/v2`
Project: EMUAdvisor
Repository profile: mixed
Initialized: 2026-09-05

## 2026-09-05 - Repository bootstrap

- Classified as `mixed` with traits: software, data-ml.
- Created missing governance files without modifying product/source artifacts.
- Classification evidence is recorded in `docs/REPO_PROFILE.md`.

## 2026-09-05 - EMU-B001 plan accepted

- Independent repository mapping and risk audit found High evidence, transcript, source-provenance, fixture-mode, and Windows-portability risks.
- Accepted one bounded hardening batch in `BLUEPRINT.md`.
- Benchmark, presentation, release, deployment, live crawl, and human-review claims remain explicitly out of scope.

## 2026-09-05 - EMU-B001 implementation baseline

- Branch: `remediation/evidence-security-portability`.
- Base HEAD: `0eb111abe5310c2f60382366eaf26fdceb24dbb7`.
- Pre-implementation tracked diff SHA-256: `4bec1a7d15745442b5b145682397c819a084c3b335f379745660fd1384ca61ad` (`AGENTS.md` bootstrap repair only).
- Pre-implementation untracked inventory: 25 governance/bootstrap files; sorted-name SHA-256 `9455fd43a12511a41ac2e2bf43d7438fbcfcbe8ab045299af46477d07a702d04`.
- Repository bootstrap audit: `PASS`, no errors or warnings.
- Root acquired the cooperative EMU-B001 writer lock before product changes.

## 2026-09-06 - EMU-B001 executor verification

- Machine comparison passed for all 60 `v1_gold` rows: only authorized provenance/adjudication fields changed; protected content and ordering are identical to base.
- Focused implementation checkpoint passed 53 tests; expanded suite later passed 81 tests.
- All three evaluation sets validate; review status reports all 60 primary cases pending independent review; publication guard passes.
- Browser smoke passes with visible fixture warning and same-tab capability handling.
- Clean Windows CPython 3.12.10 environment installed the platform-aware lock, passed imports, syntax, 79 tests at that checkpoint, all evaluation/guard checks, `pip check`, and dependency audit.
- Upgraded `pypdf` from 6.15.0 to 6.17.0 after the audit identified three fixed 2026 CVEs; the current lock audit reports no known vulnerabilities.
- Official action pins were resolved from the upstream repositories: checkout v6.0.0 and setup-python v6.3.0.
- Presentation, release, deployment, live crawl/services, corpus publication, and semantic human-review claims remain blocked.

## 2026-09-06 - EMU-B001 independent TEST and repair

- The initial frozen snapshot `e195f40ca72ebe3bb1491814dc5121066ae58bb737bfbe5c6b9a824d4854a02f` received `FAIL` because three historical documents placed legacy/unverified caveats after current-tense official-source, board-readiness, or semantic-metric claims.
- The bounded repair moved and expanded the caveats near the top of `docs/EMUAdvisor Full Analysis.md`, `docs/SPRINT_PLAN.md`, and `docs/VERSION_LOG.md`; no product behavior or protected input changed in the repair.
- Fresh independent TEST on repaired snapshot `d56a5dcdd63dbe2a1be14d42b3e16156250ab0394a849757c4269bac4ec11b26` returned `PASS_WITH_RISKS`.
- The repaired snapshot hash matched at docs-QA entry, demonstrating no unexpected product or test side effects between the verdict and reconciliation.

## 2026-09-06 - EMU-B001 docs-QA closure

- Acceptance evidence maps to the bounded EMU-B001 criteria: protected evaluation content/order preserved, evidence claims corrected, proxy/citation checks passed, transcript/corpus/source controls tested, and Windows portability verified locally.
- Recorded unavailable or deferred verification as residual risks: remote Ubuntu CI, live official-host crawl/redirect behavior, artifact-backed corpus/Qdrant/Ollama, history-aware secret scan, human semantic review/institutional attestation, corpus rights, and Internet-grade identity/public deployment security.
- Preserved the transient browser-smoke timeout and Starlette/httpx deprecation warning as maintenance risks; two subsequent browser-smoke passes provide bounded local evidence, not a reliability guarantee.
- Closed the cycle as `COMPLETE_WITH_RISKS`; benchmark, presentation, publication, release, deployment, merge, and production-readiness actions remain blocked.
- The first closure audit returned `FAIL` because `DEV_STATE.md` replaced the canonical batch ID with a descriptive closed value while `BLUEPRINT.md` retained `EMU-B001`; docs-QA restored the exact batch ID without changing the closed cycle status, and the rerun returned `PASS` with no errors or warnings.

## 2026-09-06 - Commit, PR, and remote CI evidence

- Committed the closed batch as `9a717d0` and pushed `remediation/evidence-security-portability` without rewriting history or changing the repository name.
- Opened review PR #2 against `main`; no merge, release, deployment, or publication action was taken.
- GitHub Actions runs `34011634890` and `34011648717` both passed Ubuntu core, Windows core, and browser smoke.
- Remote CI closes the platform-run gate for this commit; the human, live-source, artifact, rights, history-review, identity, and deployment gates remain open.
