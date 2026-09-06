# Publication Policy

Publication, release, and portfolio-presentation readiness are currently blocked.

## What may be published now

- Source code, tests, schemas, and current documentation under the repository license.
- The tracked assistant-curated evaluation questions and labels, with their pending independent-review status stated accurately.
- Automated test results described only as software/regression evidence for the named commit and environment.

## What must not be claimed

- That `v1_gold.jsonl` is verified gold or that university personnel reviewed it.
- That automated proxy values establish semantic answer correctness, citation precision, groundedness, legal reliability, or production quality.
- That fixture-mode output represents the official corpus.
- That historical ignored corpus/metric artifacts are reproducible or immutable without their required manifests and hashes.
- That the application is an official EMU service or ready for public Internet exposure.

## Excluded artifacts

Do not commit or publish corpora, crawled pages, indexes, Qdrant state, generated metrics, review working files, transcripts, audit logs, credentials, private attestations, or machine-local paths. The code license does not determine rights in external source content.

## Gate to revisit publication

Publication needs, at minimum, independent evaluation review with a privacy-safe durable evidence reference; an implemented immutable run manifest; a lawful corpus-distribution decision; reproducible artifact-backed proxy results; live service/deployment validation; and an independent security/QA verdict. EMU-B001 does not satisfy those later gates by itself.
