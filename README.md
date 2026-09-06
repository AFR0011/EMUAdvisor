# EMUAdvisor

EMUAdvisor is an independent, local-only English/Turkish retrieval assistant for public Eastern Mediterranean University regulations. It is a research/demo project, not an official university service, decision-maker, or production deployment.

## Current status

The software path is active, but benchmark, board-demo, publication, release, and production-readiness claims are blocked. The tracked 60-case `eval_sets/v1_gold.jsonl` file is an assistant-curated regression set pending independent human review. Its historical filename is retained for compatibility; it is not verified gold evidence.

Historical percentages in older project records were produced by automated retrieval/behavior proxies. They did not semantically grade answer correctness, citation precision, or claim-level grounding. New metric output uses schema `emu-advisor-automated-proxy/v2` and labels those observations explicitly.

## Trust boundary

- Runtime answering and optional generation remain local. No external answering, retrieval, or model API is used.
- Real corpus ingestion accepts only HTTPS URLs on exactly `mevzuat.emu.edu.tr`, validates redirect targets before requesting them, and records the validated final URL.
- Fixture mode is explicit, limited to development/test, visibly labeled, and never attributed to the official source domain.
- Chat sessions use a server-issued opaque ID plus a separate per-session capability. Public callers cannot enumerate sessions.
- Transcript persistence, audit logging, and raw-query logging are disabled by default and require separate positive opt-ins.
- Generated corpora, indexes, metrics, reviews, transcripts, and logs remain outside Git.

## Quick start (explicit fixture mode)

PowerShell:

```powershell
$env:EMU_ADVISOR_PROFILE = "dev"
$env:EMU_ADVISOR_CORPUS_MODE = "fixture"
$env:EMU_ADVISOR_QUERY_REWRITE = "deterministic"
python -m uvicorn emu_advisor.server:app --host 127.0.0.1 --port 8000
```

Fixture mode uses four synthetic records and displays a warning. It is for software verification only.

For an artifact-backed run, set `EMU_ADVISOR_CORPUS_MODE=artifact` and provide a valid nonempty `artifacts/demo_corpus/latest/chunks.jsonl`. Missing or invalid artifacts fail closed. Production also requires an admin token and service-backed Qdrant; those paths are not currently release-validated.

## Verification

```powershell
$env:EMU_ADVISOR_PROFILE = "test"
$env:EMU_ADVISOR_CORPUS_MODE = "fixture"
$env:EMU_ADVISOR_QUERY_REWRITE = "deterministic"
$env:EMU_ADVISOR_ENABLE_CHAT_PERSISTENCE = "0"
$env:EMU_ADVISOR_ENABLE_AUDIT_LOGGING = "0"
python tools/syntax_check.py
python -m unittest discover -s tests
python -m emu_advisor.evaluation eval_sets/v1_gold.jsonl
python -m emu_advisor.evaluation eval_sets/v1_hard.jsonl
python -m emu_advisor.evaluation eval_sets/emu_gold_seed.jsonl
python -m emu_advisor.eval_review status eval_sets/v1_gold.jsonl eval_sets/v1_hard.jsonl eval_sets/emu_gold_seed.jsonl
python tools/publication_guard.py
python tools/browser_smoke.py --start-server
```

See `docs/RUN_PROTOCOL.md` for clean-environment and dependency-audit commands.

## Evidence limits

Passing automated tests establishes software behavior against synthetic/tracked inputs. It does not establish semantic answer quality, institutional approval, corpus redistribution rights, live-source reproducibility, public-Internet security, or production fitness. See `docs/CLAIM_REGISTER.md`, `docs/DATA_MANIFEST.md`, and `RISK_REGISTER.md`.

## License

Code is licensed under `LICENSE`. That license does not grant rights to redistribute source-site content or generated corpus artifacts.
