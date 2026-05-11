# Board Demo Readiness

Status: `partial`

The local board demo is presentable with named gaps that must not be described as production-ready.

## Checks

| Check | Status | Detail |
|---|---|---|
| current product spec | `pass` | EMU_RAG_Current_System_Specs.md |
| full analysis | `pass` | docs\EMUAdvisor Full Analysis.md |
| demo storyboard | `pass` | docs\DEMO_STORYBOARD.md |
| publication checklist | `pass` | docs\PUBLICATION_CHECKLIST.md |
| candidate evaluation set | `pass` | eval_sets\v1_gold.jsonl |
| hard regression set | `pass` | eval_sets\v1_hard.jsonl |
| latest metrics artifact | `pass` | top5=1.0 citation=1.0 |
| human-reviewed gold status | `blocked` | 160 cases still pending review |
| production admin token | `partial` | not set for this local check |
| live Qdrant service | `blocked` | service-backed Qdrant not documented in environment |
| local analytics log | `pass` | 133 audit events |

## Non-Negotiable Limits

- This is a board-demo readiness report, not a production approval.
- Human-reviewed gold metrics remain blocked until manual labels are complete.
- Production-style deployment remains blocked until service-backed Qdrant and target hardware are validated.
- Generated mode remains extractive-first unless local model latency and answer quality are characterized.
