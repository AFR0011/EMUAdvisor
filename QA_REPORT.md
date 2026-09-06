# QA Report

Workflow schema: `agentic-workflow/v2`
Project: EMUAdvisor
Repository profile: mixed
Initialized: 2026-09-05

## Current cycle

- Batch: EMU-B001
- Verdict: PASS_WITH_RISKS
- Closure: COMPLETE_WITH_RISKS
- Tested snapshot: `d56a5dcdd63dbe2a1be14d42b3e16156250ab0394a849757c4269bac4ec11b26`
- Evidence: Fresh independent TEST passed the repaired frozen diff. Residual external, human, live-service, reproducibility, rights, identity, and maintenance checks remain explicit below.

## Verdict history

1. Initial snapshot `e195f40ca72ebe3bb1491814dc5121066ae58bb737bfbe5c6b9a824d4854a02f`: `FAIL`.
   - `docs/EMUAdvisor Full Analysis.md` presented current-tense official-source/board-readiness language before its historical disclaimer.
   - `docs/SPRINT_PLAN.md` placed its disclaimer after historical readiness content.
   - `docs/VERSION_LOG.md` placed its legacy-metric caveat after historical semantic metric claims.
2. Bounded documentation repair: caveats moved and expanded ahead of the claims in those three files; no product behavior or protected evaluation content changed.
3. Repaired snapshot `d56a5dcdd63dbe2a1be14d42b3e16156250ab0394a849757c4269bac4ec11b26`: fresh `PASS_WITH_RISKS`.
4. Docs-QA recomputed the same repaired aggregate snapshot before reconciliation; no tester-introduced source/product side effect was present.

## Executor evidence

- Syntax: 42 Python files passed.
- Focused tests: 11/11 passed independently.
- Full tests: 81/81 passed twice, including a fresh Windows CPython 3.12 environment.
- Evaluation validation: 60 primary, 50 hard-regression, and 50 provisional-seed cases passed schema checks.
- Review status: 60/60 primary cases and 160/160 combined cases are pending/non-verified.
- Publication guard: passed, including rejection of unsupported human-review evidence.
- Browser smoke: passed twice in explicit fixture mode after one transient timeout.
- Windows clean install: Python 3.12.10 lock/install/import/core checks and `pip check` passed.
- Dependency audit: no known vulnerabilities after `pypdf==6.17.0` update.
- Protected-input comparison: all 60 `v1_gold` records preserved content/order and changed only the four authorized provenance/adjudication fields; other protected paths have no diff.
- CI/source checks: Windows/Ubuntu Python 3.12 matrix and immutable official Action SHAs verified; tracked-tree credential scan found no matches.
- Remote CI: GitHub Actions runs `34011634890` and `34011648717` passed Ubuntu core, Windows core, and browser smoke for commit `9a717d0` / PR #2.

## Bootstrap validation

- First closure audit: `FAIL` on an exact active-batch mismatch between `DEV_STATE.md` and `BLUEPRINT.md`; docs-QA corrected the state field without changing the closure verdict.
- `docs/BOOTSTRAP_AUDIT.md` rerun: `PASS`, no errors or warnings.

## Acceptance mapping

| Acceptance area | Evidence | Result |
| --- | --- | --- |
| Evaluation provenance | 60-row machine comparison; only four authorized fields changed; all primary judgments null/pending | PASS |
| Automated evidence honesty | Proxy-schema tests, evaluation validation, publication guard, and caveat-position retest | PASS |
| Expected-evidence citations | Focused wrong/matching/fallback/conflict tests | PASS |
| Transcript isolation/privacy defaults | Focused capability, cross-session, admin, persistence, legacy-file, and audit-minimization tests | PASS |
| Corpus/source provenance | Explicit-mode startup matrix, fixture provenance, and redirect-prevalidation tests | PASS_WITH_RISKS — live official-host crawl not run |
| Windows/Ubuntu portability | Fresh Windows 3.12 install/full suite; both remote CI matrices passed Ubuntu core, Windows core, and browser smoke | PASS |
| Protected boundaries | Diff comparison, tracked-tree credential scan, and no live/generated/private artifact action | PASS_WITH_RISKS — history-aware scan and owner cleanup remain separate |
| Full verification | Syntax 42 files, full suite 81/81, three evaluation validations, review status, guard, browser smoke, dependency audit | PASS_WITH_RISKS — one transient browser timeout and deprecation warning retained |

## Unavailable or deferred checks

- Live exact-host crawl and redirect chain: perform only in a separately authorized, controlled live-ingestion batch.
- Artifact-backed corpus, Qdrant, Ollama, target hardware, and deployment: reproduce with an implemented immutable run manifest before claims.
- Human semantic review/institutional attestation: obtain privacy-safe durable reviewer evidence; automated checks cannot substitute.
- Corpus redistribution rights: obtain an owner/legal decision before publishing derived corpus content.
- Internet-grade identity and public deployment threat model: complete security review before any network-exposed demo.
- History-aware secret/non-public-material scan: run before presentation, release, or merge to a public successor.
- Maintenance: investigate the transient browser-smoke timeout if it recurs and resolve the Starlette/httpx deprecation before it becomes incompatible.

## QA conclusion

The bounded EMU-B001 implementation meets its acceptance criteria and the independent tester verdict is preserved as `PASS_WITH_RISKS`. No Critical risk is open. This closes the development cycle, not the presentation/publication/release gates.
