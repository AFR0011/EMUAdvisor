# Board Demo Readiness

Status: `blocked`

The repository is not currently approved for board-demo, portfolio-presentation, release, deployment, or production claims.

## Evidence status

| Area | Status | Meaning |
|---|---|---|
| Software regression suite | In progress | Automated checks can verify implementation behavior only. |
| `v1_gold.jsonl` | Blocked | 60 assistant-curated cases pending independent human review. |
| Historical percentages | Legacy/unverified | Automated proxy outputs, not semantic answer-quality evidence. |
| Corpus artifacts | Blocked | Not present in Git; no immutable reproducibility manifest for historical runs. |
| Fixture mode | Test-only | Synthetic data, visibly labeled, never official-corpus evidence. |
| Production services | Blocked | Live Qdrant/Ollama/target hardware/deployment are unverified. |
| Publication rights | Blocked | Code license does not resolve corpus redistribution rights. |

Re-run `python -m emu_advisor.readiness --out docs/BOARD_DEMO_READINESS.md` only in a controlled workspace. The generated report must preserve these blockers while independent review is pending.
