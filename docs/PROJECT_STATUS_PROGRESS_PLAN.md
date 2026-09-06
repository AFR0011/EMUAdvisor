# Project Status and Progress Plan

## Current status

EMUAdvisor has an active local software implementation and a substantial automated test suite. EMU-B001 completed its bounded evidence-label, privacy, corpus-provenance, source-scope, and Windows-portability hardening with an independent `PASS_WITH_RISKS`. This does not make the repository presentation-ready.

## Completed in EMU-B001

- Honest assistant-curated/pending-review evaluation metadata.
- Versioned automated proxy schema with expected-evidence citation matching.
- Capability-isolated public chat sessions and admin-only enumeration.
- Default-off transcript persistence, audit logging, and raw-query logging.
- Explicit, visibly labeled fixture mode and fail-closed artifact mode.
- Exact-host HTTPS redirect validation and non-laundered fixture provenance.
- Platform-aware Python lock and Windows/Ubuntu Python 3.12 CI design.

Local verification passed, including a fresh Windows Python 3.12 environment. Remote Ubuntu CI and
the live/artifact/human/security gates below remain future actions.

## Next milestones after EMU-B001

1. Obtain independent review and a privacy-safe durable attestation for the evaluation set.
2. Implement the immutable run-manifest design from `docs/DATA_MANIFEST.md`.
3. Resolve source-content rights and the lawful artifact-sharing boundary.
4. Perform a controlled live crawl and artifact-backed proxy run with hashes.
5. Validate local services and target hardware, then perform deployment/security review.
6. Reassess presentation/publication only after those gates pass.

Historical project percentages are legacy automated proxy observations and are not used as current semantic evidence.
