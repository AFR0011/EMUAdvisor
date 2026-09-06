# Historical Metrics Record

The prior metric snapshots are retained only as historical automated proxy observations. They are not current benchmark evidence and do not establish semantic answer correctness, citation precision, groundedness, institutional review, or production fitness.

Legacy runs reported perfect percentages on several tracked sets and lower values on earlier seed runs. Those labels were too broad: the implementation primarily checked expected-evidence retrieval, answer/refusal/clarification mode, citation presence, format, and latency. The ignored corpus/metric artifacts and immutable input hashes required to reproduce the historical runs are absent from this checkout.

New runs use schema `emu-advisor-automated-proxy/v2` and report:

- expected-evidence retrieval match rates;
- answer-mode plus expected-evidence proxy rate;
- refusal and clarification behavior-match rates;
- citation presence separately from expected-evidence citation match;
- nonempty-format and latency proxies;
- explicit `verified: false` and automated-evidence classification.

No new artifact-backed run was performed in EMU-B001. Presentation remains blocked.
