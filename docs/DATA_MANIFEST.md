# Data Manifest

Workflow schema: `agentic-workflow/v2`

## Sources and rights boundary

- Runtime source scope: public HTML/PDF from `https://mevzuat.emu.edu.tr` only.
- Full crawl/corpus/index/metrics/review artifacts remain ignored and are not licensed by the MIT
  software license. Public availability does not establish redistribution permission.
- Tracked test fixtures should be synthetic/minimal. Substantial third-party source text requires
  separate rights confirmation.

## Tracked evaluation inputs

- `eval_sets/v1_gold.jsonl`: 60 assistant-curated bilingual cases pending independent human review;
  external review is not evidenced in the repository.
- `eval_sets/v1_hard.jsonl`: 50 assistant-curated hard regression cases.
- `eval_sets/emu_gold_seed.jsonl`: 50 provisional source-binding/human-review-pending seed cases.

## Generated/protected data

- `artifacts/demo_corpus/**`: canonical chunks and crawl manifests.
- `artifacts/qdrant/**`: local vector state.
- `artifacts/metrics/**`: per-run metrics/results.
- `artifacts/review/**`: review working data, potentially sensitive.
- `artifacts/chat_sessions.json` and `logs/audit.jsonl`: local transcript/query data; never publish.

## Immutable run-manifest design

This is a design contract, not an implemented claim about historical runs. Each future run directory
must be append-only and named by a unique run ID. A canonical JSON manifest must contain:

- manifest schema version, run ID, creation time, and explicit fixture flag;
- requested source URLs, validated final URLs, and complete redirect chains;
- corpus, evaluation-set, dependency-lock, code-commit, configuration, and environment hashes;
- Python/platform/tool versions and all material parameters;
- output filenames, media types, sizes, and SHA-256 hashes;
- evaluation review status plus a privacy-safe evidence reference when independently reviewed;
- the exact command/entry point and deterministic/random seed settings.

Canonical serialization must use UTF-8 JSON, sorted object keys, stable separators, and no absolute
machine paths. Output hashes are computed before the manifest is finalized. A mutable `latest`
pointer may reference an immutable run ID but is never evidence itself.

Signing, transparency logs, a manifest writer, corpus publication, and retroactive historical
validation are out of scope for EMU-B001. Until the design is implemented and independently rerun,
historical numbers remain legacy local automated proxy observations, not reproducible benchmarks.
