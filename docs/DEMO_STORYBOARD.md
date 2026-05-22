# Board Demo Storyboard

Status: board-demo script, not production approval.

## Slide 1 - Purpose

- EMU Regulation Assistant answers staff-facing questions about indexed EMU regulations.
- Scope is official `mevzuat.emu.edu.tr` HTML plus linked official PDFs.
- The demo is local-only and informational.

## Slide 2 - Trust Model

- English and Turkish corpora remain separate in V1.
- Every substantive answer carries citations.
- Weak, ambiguous, or out-of-scope questions are clarified or refused.

## Slide 3 - Architecture

- Official sources are crawled into canonical chunks.
- Hybrid retrieval selects cited evidence.
- Deterministic answerability gates run before optional local generation.
- Local audit logs and metrics support review without external telemetry.

## Slide 4 - Live Question

Use: `What is the attendance requirement?`

Expected demo behavior:

- Answer from indexed regulation evidence.
- Show source language and bottom citations.
- Keep `/chat` output public-safe without raw hit diagnostics (User mode at `/admin?view=user`).

## Slide 5 - Edge Cases

Use:

- `What about graduation?`
- `Bugun kampuste hangi burs etkinlikleri var?`
- `Arastirma gorevlisi burs kurallari farkli veya celiskili mi?`

Expected demo behavior:

- Clarify vague questions.
- Refuse event/general-campus questions.
- Keep the answer within the detected-language regulation corpus.

## Slide 6 - Evidence And Metrics

- Candidate and hard-regression metrics are useful regression evidence.
- They remain assistant-curated until human review is complete.
- Present extractive latency, top-5 retrieval, citation coverage, refusal behavior, and known generated-mode limits.

## Slide 7 - Roadmap Ask

- Complete human review of the evaluation sets.
- Validate live Qdrant service and target campus hardware.
- Decide whether generated mode remains opt-in or becomes part of the demo.
- Approve pilot constraints before any production-like deployment.
