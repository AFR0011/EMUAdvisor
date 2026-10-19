# Model Evaluation

Workflow schema: `agentic-workflow/v2`

## Evaluation sets

`v1_gold` was assembled with assistant support. On 2026-10-19, the project author
attested to manually checking its questions, expected answers, and source references
against the available university regulations. This is an author-reported review of the
reference cases, **not** independent human adjudication of the system's actual answers
or citations, and no reproducible per-case review artifact is committed. University staff
separately tried the application informally; they did not review the gold set. Case-level
pending-independent-review metadata remains conservative on purpose. `v1_hard` is an
assistant-curated regression set and `emu_gold_seed` is provisional. None is an
independently held-out semantic-quality gold standard.

## Current measurable behaviors

- Retrieval rank/top-k against expected source/chunk labels.
- Correct response mode for answer/refusal/clarification/conflict cases.
- Citation presence and, after EMU-B001, expected-evidence citation match.
- Extractive/generation timing and explicit model-unavailable fallback.

Current response/citation/groundedness scores are proxy composites and must not be described as
semantic answer correctness, citation precision, or claim-level grounding.

## Unverified areas

- Per-case human adjudication and reviewer provenance.
- Immutable historical corpus/result reproduction.
- Live Qdrant and current Ollama quality/latency on target hardware.
- Held-out evaluation free from implementation iteration.
- Official/institutional approval and legal interpretation.

## Comparison boundary

Historical recorded numbers may be retained only as dated local observations with their metric
definitions. They may not be compared as model-quality improvements when corpus, inputs, or proxy
definitions differ.
