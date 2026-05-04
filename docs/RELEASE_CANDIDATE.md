# V1 Release Candidate Notes

Last updated: 2026-05-04

## Status

The repository now has a root implementation path for every planned sprint, but it is not production-ready and has not been validated against a live EMU crawl/index. Treat this as a demo-code release candidate scaffold.

## Verified Locally

- Canonical schema validation.
- HTML ingestion from official-scope EMU regulation URLs.
- PDF ingestion with page-number metadata using local `pypdf`.
- Language/corpus routing for English and Turkish.
- Machine-readable bilingual evaluation seed set.
- Local deterministic embedding baseline.
- Qdrant-compatible in-memory vector/payload store for offline testing.
- Hybrid lexical+dense retrieval and mode presets.
- Answerability gate, refusal, clarification, conflict display, citations, and extractive fallback.
- Snapshot/diff/activation workflow.
- FastAPI demo endpoints and EMU-branded static UI.
- Privacy-preserving audit log format.
- Active-session load simulation.

## Not Yet Validated

- Real crawl of `mevzuat.emu.edu.tr`.
- Real official PDF corpus coverage.
- Retrieval quality against reviewed 50-60 gold questions.
- Qdrant server deployment with `qdrant_client`.
- Local LLM generation quality, streaming latency, or GPU serving.
- Campus server deployment constraints.

## Demo Command

```powershell
python -m uvicorn emu_advisor.server:app --host 127.0.0.1 --port 8000
```

Then open `http://127.0.0.1:8000`.

## Release Gate

Do not publish this as production. It is suitable for GitHub publication as `emu-advisor` and for continuing implementation against a real crawl/index.
