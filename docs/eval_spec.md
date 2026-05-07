# EMU Advisor Evaluation Spec

Last updated: 2026-05-06

## Purpose

The evaluation set is a legal-RAG benchmark for the local-only EMU Regulation Assistant. It must keep retrieval quality, answer correctness, citation precision, groundedness, format compliance, and latency separate so failures can be fixed in the correct layer.

## Case Status

- `assistant_curated_pending_human_review`: runnable candidate cases; useful for regression, not a human-reviewed claim.
- `provisional_gold_seed_pending_source_binding`: cases converted from `docs/gold-set-comprehensive-analysis.md`; useful for mode comparison, but excluded from hard quality claims until source/chunk binding and human review are complete.
- `human_checked`: reviewed by a human reviewer for answer text and citation sufficiency.
- `adjudicated`: reviewed after disagreement or legal/source ambiguity.

## Required Case Fields

Every executable case should include:

- `case_id`, `question`, `language`, `expected_behavior`, `category`, and `review_status`.
- At least one source binding: `expected_chunk_ids`, `expected_source_urls`, or provisional expected-answer support.
- `expected_answer_text`, `expected_citation_paths`, `expected_quote_spans`, `answer_format`, `prompt_type`, and `difficulty` when available.
- `grading.must_include` and `grading.must_not_include` for answer-quality review.

## Scoring

The mode benchmark uses these weights:

| Dimension | Weight |
|---|---:|
| Retrieval correctness | 0.30 |
| Answer correctness | 0.30 |
| Citation precision | 0.20 |
| Groundedness / hallucination proxy | 0.15 |
| Format compliance | 0.05 |

Automated scoring is a proxy. Human review remains required before presenting any score as legal-quality validation.

## Mode Comparison

Run all modes with:

```powershell
python -m emu_advisor.metrics run --all-modes --cases eval_sets\emu_gold_seed.jsonl --chunks artifacts\demo_corpus\latest\chunks.jsonl --out artifacts\metrics\mode_comparison
```

Outputs:

- `artifacts/metrics/mode_comparison/comparison.json`
- `artifacts/metrics/mode_comparison/comparison.md`
- per-mode `metrics.json`, `metrics.md`, `per_case.csv`, and `human_review.csv`

## Review Rules

- A correct legal answer must cite the smallest sufficient provision when the provision is known.
- A correct answer with the wrong citation is capped at partial credit.
- A correct citation with an incomplete rule is capped at partial credit.
- Unsupported thresholds, deadlines, exceptions, offices, or article paths are hallucinations.
- English and Turkish corpora must not be silently mixed; cross-corpus evaluation must be explicit.

## Current Boundary

`eval_sets/emu_gold_seed.jsonl` is provisional. It can drive cheap/balanced/expensive tuning, but the current project must continue to label it as pending source binding and human review.
