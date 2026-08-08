# Publication Checklist

Use this before changing EMUAdvisor from private to public.

## Required before publication

- [x] Publishing rights confirmed by the repository owner.
- [x] MIT license present.
- [x] `eval_sets/v1_gold.jsonl` recorded as human-reviewed and verified by the project author and university staff.
- [x] Admin tokens excluded from URL/query-parameter flows.
- [x] Browser diagnostics use tab-scoped session storage plus authorization headers.
- [x] Pinned dependency snapshot present in `requirements-lock.txt`.
- [x] Core CI and browser smoke are required jobs.
- [ ] Keep `.old/` archive ignored and out of the clean public tree unless explicitly promoted.
- [ ] Keep generated crawl, index, metrics, screenshots, conversations, and logs under ignored artifact paths.
- [ ] Run the final branch through `python tools/publication_guard.py` and GitHub Actions.
- [ ] Refresh `docs/BOARD_DEMO_READINESS.md` when deployment/runtime evidence changes.
- [ ] Confirm README commands match the supported run protocol.
- [ ] Check the current tree and Git history for secrets or non-public university material.

## Required wording

- Describe the project as independent research/software, not an official EMU administrative service.
- State that outputs are informational and are not final university decisions.
- Describe `v1_gold` as the verified human-reviewed 60-case benchmark.
- Keep `v1_hard` identified as a hard regression suite unless separately reviewed/documented as gold.
- Keep `emu_gold_seed` identified as provisional unless it completes the same review process.
- Describe recorded benchmark metrics as fixed local evaluation results, not production guarantees.
- State that production deployment remains unvalidated until service-backed Qdrant and target runtime/hardware are verified.

## Optional publication assets

- Public UI screenshot.
- Diagnostics screenshot with tokens and sensitive local logs excluded.
- Sample output snippets from `docs/DEMO_METRICS_SNAPSHOT.md`.
- Architecture diagram based on the README data flow.
