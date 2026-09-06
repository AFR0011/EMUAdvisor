# Experiment Protocol

Workflow schema: `agentic-workflow/v2`

## Objective

Measure retrieval and observable response behavior for separate English/Turkish regulation corpora
without conflating structural proxies with semantic answer quality.

## Inputs and baselines

- Name the exact evaluation set, corpus/run manifest, code commit, dependency lock, configuration,
  mode, embedding/retrieval backend, and local-model status.
- Hash every immutable input/output. A mutable-site rebuild is a new corpus version.
- Keep assistant-curated regression cases distinct from independently held-out/adjudicated cases.

## Metrics

- Valid without human semantic labels: expected-source/chunk retrieval rank, top-k retrieval,
  expected-evidence citation match, response-mode behavior, citation presence, and latency.
- Invalid without independent adjudication: answer correctness, citation precision, groundedness,
  legal correctness, or human-review claims.

## Stopping and publication rules

- Stop on cross-language corpus mixing, out-of-scope source, missing manifest, unsupported label,
  or an overconfident answer unsupported by expected evidence.
- Full crawl/model experiments require explicit authorization because they use network/compute.
- Do not publish a benchmark result until an independent rerun reproduces the named manifest.
