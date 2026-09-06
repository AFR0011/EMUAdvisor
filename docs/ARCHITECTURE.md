# Architecture

Workflow schema: `agentic-workflow/v2`

## System boundary

EMUAdvisor is a local-only FastAPI/browser research demo over public regulation HTML/PDF from the
exact host `mevzuat.emu.edu.tr`. English and Turkish remain separate corpora. External answering,
embedding, reranking, or generation APIs are out of scope; Ollama and Qdrant are optional local
services. The application is independent and unofficial.

## Components and flow

```text
official HTML/PDF -> pipeline/html_ingest/pdf_ingest -> canonical ignored chunks
  -> local or Qdrant hybrid retrieval -> answerability/extractive answer
  -> optional local Ollama generation -> FastAPI -> static user/admin UI
tracked evaluation cases + ignored corpus -> metrics -> ignored run artifacts -> reviewed summaries
```

- `emu_advisor/schema.py` is the canonical document/chunk contract.
- `emu_advisor/server.py` is the API/UI composition boundary.
- `emu_advisor/conversation_store.py` issues opaque session IDs/capabilities and stores capability
  hashes; persistence is opt-in. `audit_log.py` emits minimized optional records.
- `emu_advisor/evaluation.py`, `metrics.py`, and `eval_review.py` define evaluation behavior.
- `artifacts/**` and `logs/**` are generated/protected, not publication inputs by default.

## Current trust controls and debt

Corpus startup is explicit fixture/artifact mode; fixture records are visibly synthetic and carry
non-official provenance. Real ingestion validates exact-host HTTPS before every request and after the
final response. The browser keeps each cleartext session capability in same-tab storage only.

Remaining debt includes full Internet identity/authentication, opt-in transcript encryption,
implemented immutable run manifests, independent human evaluation, live artifact/service validation,
corpus-rights decisions, and deployment review. Large-module refactoring remains deferred.
