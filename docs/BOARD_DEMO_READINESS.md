# Board Demo Readiness

Status: `partial`

The local board demo is presentable with named deployment gaps that must not be described as production-ready.

## Checks

| Check | Status | Detail |
|---|---|---|
| current product spec | `pass` | EMU_RAG_Current_System_Specs.md |
| full analysis | `pass` | docs/EMUAdvisor Full Analysis.md |
| demo storyboard | `pass` | docs/DEMO_STORYBOARD.md |
| publication checklist | `pass` | docs/PUBLICATION_CHECKLIST.md |
| verified gold evaluation set | `pass` | eval_sets/v1_gold.jsonl |
| hard regression set | `pass` | eval_sets/v1_hard.jsonl |
| latest metrics artifact | `pass` | top5=1.0 citation=1.0 |
| verified gold review status | `pass` | 60 cases; 0 pending |
| auxiliary evaluation review status | `partial` | 100 hard/seed cases retain separate review status |
| production admin token | `partial` | not set for this local check |
| live Qdrant service | `blocked` | service-backed Qdrant not documented in environment |
| local analytics log | `pass` | 193 audit events in recorded snapshot |

## Non-Negotiable Limits

- This is a board-demo readiness report, not a production approval.
- `v1_gold` is human-reviewed and verified by the project author and university staff.
- `v1_hard` is a regression suite and `emu_gold_seed` is provisional unless separately reviewed and documented.
- Production-style deployment remains blocked until service-backed Qdrant and target hardware are validated.
- Generated mode remains extractive-first unless local model latency and answer quality are characterized.
