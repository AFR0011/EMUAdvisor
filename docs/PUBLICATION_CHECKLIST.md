# Publication Checklist

Use this before publishing the repository as `emu-advisor`.

## Required Before Publication

- Keep `.old/` archive ignored and out of the clean public repo unless explicitly promoted.
- Keep generated crawl, index, metrics, screenshots, and logs under ignored artifact paths.
- Run `python -m unittest discover -s tests`.
- Run evaluation validators for `eval_sets/v1_gold.jsonl`, `eval_sets/v1_hard.jsonl`, and `eval_sets/emu_gold_seed.jsonl`.
- Generate or refresh `docs/BOARD_DEMO_READINESS.md`.
- Confirm README commands match `docs/RUN_PROTOCOL.md`.

## Required Wording

- Describe the project as a local-only demo.
- State that it is not an official final university decision system.
- State that evaluation sets are assistant-curated until human review is complete.
- State that production deployment is blocked on live Qdrant and target hardware/service validation.

## Optional Publication Assets

- Public UI screenshot.
- Admin metrics screenshot with sensitive local logs excluded.
- Sample output snippets from `docs/DEMO_METRICS_SNAPSHOT.md`.
- Short architecture diagram or Mermaid rendering from the full analysis.
