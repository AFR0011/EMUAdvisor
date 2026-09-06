# Evidence Map

| Claim | Direct evidence | Current status |
| --- | --- | --- |
| Local bilingual regulation retrieval implementation exists | `emu_advisor/**`, tests, system spec | Verified in code/tests |
| English/Turkish corpora stay separate | routing/retrieval/evaluation tests | Verified in code/tests |
| Historical crawl produced 8,714 chunks / 119 sources / 22 PDFs | dated docs plus prior audit fresh crawl | Historical observation; exact old artifact absent |
| Top-5 retrieval reached 100% on named tracked sets | dated outputs and prior audit rerun | Local retrieval result, not answer correctness |
| 60 cases were human-reviewed by university staff | self-asserted row metadata and automated commit only | Unverified; must be retracted or evidenced |
| 100% answer accuracy/precision/groundedness | proxy metric implementation | Unsupported semantic claim |
| Browser UI works responsively | browser smoke and prior audit | Verified on tested Chromium scopes |
| Production transcript boundary is protected | server route policy | False before EMU-B001 |
| Windows locked install works | unguarded Linux-only dependency | False before EMU-B001 |
