# Demo Metrics Snapshot

Last updated: 2026-05-22

## Corpus Snapshot

- Source scope: official `mevzuat.emu.edu.tr` HTML plus linked official PDFs.
- Crawl seeds: `https://mevzuat.emu.edu.tr/content.htm`, `https://mevzuat.emu.edu.tr/Content-en.htm`.
- Crawl size: 123 pages, 22 PDFs, 4 crawl errors.
- Active chunks: 8,714 total; 3,878 English and 4,836 Turkish.
- Source types: 8,599 HTML chunks and 115 PDF chunks.
- Structured evidence: 493 table summaries, 7,601 table rows, 8 derived salary facts, 497 text chunks, 115 PDF chunks without table metadata.
- Active artifact: `artifacts/demo_corpus/latest/chunks.jsonl` (ignored).
- Embedded Qdrant index: `artifacts/qdrant/latest` (ignored), collection `emu_regulations`.

## Evaluation Snapshot

Evaluation set: `eval_sets/v1_gold.jsonl`

Review status: `assistant_curated_pending_human_review`

| Metric | Value |
|---|---:|
| Cases | 60 |
| Answerable/cross-source cases | 52 |
| Refusal cases | 4 |
| Clarification cases | 4 |
| Retrieval top-1 | 92.31% |
| Retrieval top-3 | 98.08% |
| Retrieval top-5 | 100.00% |
| Response accuracy | 100.00% |
| Rejection accuracy | 100.00% |
| Clarification accuracy | 100.00% |
| Citation coverage | 100.00% |
| Extractive latency p50 | 674 ms |
| Extractive latency p95 | 1,267 ms |
| Failed cases | 0 |

Hard regression set: `eval_sets/v1_hard.jsonl`

| Metric | Value |
|---|---:|
| Cases | 50 |
| Salary-table cases | 24 |
| Scholarship-bundle cases | 24 |
| Refusal cases | 2 |
| Retrieval top-1 | 97.92% |
| Retrieval top-3 | 100.00% |
| Retrieval top-5 | 100.00% |
| Response accuracy | 100.00% |
| Rejection accuracy | 100.00% |
| Citation coverage | 100.00% |
| Extractive latency p50 | 468 ms |
| Extractive latency p95 | 2,867 ms |
| Failed cases | 0 |

Generated mode status: local Ollama service and `qwen3:8b` model were detected, but the bounded smoke generation with `--ollama-timeout-s 2` timed out. Generated metrics are therefore marked unavailable in `artifacts/metrics/latest_generated/metrics.json`; extractive and grouped answers remain the validated demo path.

## Failure Analysis

- Gold failed cases: 0.
- Hard-regression failed cases: 0.
- Expected source missing from top-5: 0 in both sets.
- Missing citation: 0 in both sets.
- False refusal: 0 in both sets.
- False answer on refusal cases: 0 in both sets.
- Missing clarification: 0 in the gold set.

Worst failed cases in the latest runs: none.

## Sample Outputs

Question: `What is the salary range of a professor compared to assistant professor?`

Mode: `answer`, answer type `table`. The answer uses a derived salary fact and preserves the numeric ranges: Professor uses scale 7, steps 1-14, from 159,600.00 to 188,200.00; Assistant Professor uses scale 5, steps 1-14, from 107,900.00 to 145,600.00.

Question: `How to get a scholarship?`

Mode: `answer`, answer type `topic_bundle`. The answer returns grouped cited evidence for entrance/incentive scholarships, international discounts, high-honour awards, sports grants, research assistant/postgraduate scholarships, and disability scholarships, then asks which type to expand.

Question: `Lisansüstü burslar hangi oranlarda verilir?`

Mode: `answer`, answer type `table`. The top evidence comes from the Turkish scholarship/discount regulation and cites the postgraduate scholarship rows.

Question: `Araştırma görevlisi burs kuralları farklı veya çelişkili mi?`

Mode: `show_conflict`, answer type `direct`. Retrieval remains within the detected-language corpus and should cite the research-assistant rules rather than only the general scholarship table.

Question: `Bugün kampüste hangi burs etkinlikleri var?`

Mode: `refuse`. The answer refuses because campus events are outside the V1 official-regulation scope, even though the query contains the word `burs`.

## Known Limits

- This snapshot is a publishable demo snapshot, not a human-reviewed quality claim.
- The 60-case candidate set and 50-case hard set are assistant-curated and still need manual labeling before being called gold-standard evaluations.
- Broad scholarship prompts run several deterministic subqueries; p50 remains under 1 second, but p95 is higher than direct extractive queries.
- Generated mode is implemented and fallback-safe, but `qwen3:8b` timed out under a 2-second smoke limit on this machine.
- Qdrant has unit coverage, CLI support, and a validated embedded local Qdrant index at `artifacts/qdrant/latest`; a Docker/live Qdrant service deployment is still not validated here.
