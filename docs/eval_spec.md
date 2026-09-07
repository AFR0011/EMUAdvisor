# Evaluation Specification

## Evidence classes

EMUAdvisor separates two evidence classes:

1. Automated regression proxies, produced by software against labeled inputs.
2. Independent human adjudication, recorded through a privacy-safe durable evidence reference.

Automated output must never be described as semantic answer correctness, citation precision, groundedness, legal reliability, or verified gold.

## Tracked sets

- `v1_gold.jsonl`: historical filename; 60 assistant-curated regression cases pending independent review.
- `v1_hard.jsonl`: hard regression cases with their own review state.
- `emu_gold_seed.jsonl`: provisional seed cases, not verified benchmark evidence.

Case IDs, questions, ordering, languages, behaviors, categories, expected corpus/document/chunk/source labels, and keywords are protected evaluation inputs. Review-state changes require traceable evidence.

## Automated proxy schema

New reports use `emu-advisor-automated-proxy/v2` and `verified: false`. They may report:

- expected-evidence retrieval top-k rates;
- answer-mode plus expected-evidence proxy rate;
- refusal and clarification behavior-match rates;
- citation presence rate;
- expected-evidence citation-match rate and evidence level;
- nonempty-format proxy;
- routing, retrieval, extractive, generation, and first-token latency.

Expected chunks are primary. Exact normalized source URLs are a fallback only when a case lacks expected chunks. Keywords may assist retrieval but cannot prove citation or answer quality. Conflict cases require all distinct expected evidence sides.

## Human-review contract

Any future `human_reviewed_verified` row requires explicit correctness judgments plus a durable evidence object containing a reference, dataset SHA-256, review date, and reviewer role. Repository tools must reject self-asserted verified metadata without that contract. Personal reviewer identity need not be public.
