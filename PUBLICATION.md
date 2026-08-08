# Publication Readiness

EMUAdvisor may be published by the repository owner. The source code is released under the MIT License. The project remains independent research/software work and is not an official Eastern Mediterranean University administrative service.

## Release checklist

- [x] Publishing rights confirmed by the repository owner.
- [x] MIT license added.
- [x] `eval_sets/v1_gold.jsonl` has been reviewed and verified by the project author and university staff.
- [x] Browser/admin authentication no longer accepts credentials from URL query parameters; protected requests use headers and the browser UI stores credentials only in tab-scoped session storage.
- [x] `eval_sets/emu_gold_seed.jsonl` remains explicitly described as provisional unless it completes the same review process.
- [x] Generated crawl, index, audit, review, and conversation artifacts remain outside the committed public-release workflow.
- [x] Pinned Python dependencies and a dependency audit are part of CI.
- [ ] Confirm no secrets or non-public university material exist in Git history before changing repository visibility.
- [ ] Run the required GitHub Actions core and browser-smoke jobs successfully on the final publication branch.
- [x] Keep the README disclaimer that this is independent research software, not an official EMU administrative service.

## Evaluation terminology

`eval_sets/v1_gold.jsonl` is the verified human-reviewed gold evaluation set. Its cases were reviewed by the project author and university staff. Public metrics reported for `v1_gold` should still be described as local evaluation results for this fixed corpus and implementation, not production-service guarantees or evidence of universal model quality.

`eval_sets/v1_hard.jsonl` is a hard regression suite focused on difficult table, grouped-query, and refusal behavior. It is not presented as a second gold benchmark unless separately reviewed and documented as such.

`eval_sets/emu_gold_seed.jsonl` remains a provisional seed set until its source bindings and labels complete the same review process. The historical filename is retained for compatibility; public documentation should call it a provisional evaluation seed rather than a verified gold benchmark.

## Public-release principle

The public repository should demonstrate retrieval, citation, refusal, evaluation, local-generation, and operational safeguards without implying institutional endorsement or production deployment. Claims should distinguish verified benchmark results from regression results, provisional evaluation material, and runtime/deployment limitations.
