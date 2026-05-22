# EMU Regulation Assistant — Current System Specification

**Status:** Working specification based on interview rounds completed so far  
**Project:** EMU local-only RAG assistant / EMU Regulation Assistant  
**Current deliverable:** Demo-first system, not full production yet  
**Primary V1 users:** Eastern Mediterranean University staff  

---

## 1. Project Goal

Build a local-only RAG assistant for Eastern Mediterranean University that answers staff questions about official university rules and regulations using cited evidence from official sources.

The system must answer in detailed plain language, quote exact regulation text when useful, summarize/explain the meaning, and provide citations at the bottom of the answer.

The system must not behave like a general university chatbot in V1.

---

## 2. V1 Product Boundary

### 2.1 V1 Mission

V1 should:

- Answer questions about EMU rules and regulations.
- Explain rules in detailed, plain language.
- Ground every substantive answer in official cited sources.
- Ask clarification questions when the user query is ambiguous.
- Refuse or redirect when evidence is insufficient.
- Show conflicts between sources instead of resolving them silently.

Recommended V1 promise:

> Answer staff questions about indexed EMU regulations using cited official sources, and refuse or clarify when evidence is insufficient.

### 2.2 V1 Non-goals

V1 must not:

- Provide student advising.
- Provide staff advising.
- Answer general university information questions.
- Answer questions about events, activity center items, programs, or course information.
- Use private student/staff records.
- Integrate with student information systems.
- Perform workflow automation.
- Send emails or schedule tasks.
- Use external APIs.
- Claim to be an official final/legal answer.
- Mix English and Turkish legal/regulatory sources in V1.

---

## 3. Authority and Liability Boundary

The assistant is informational only.

Every answer should preserve this authority boundary:

- It may say: “According to the cited regulation…”
- It should remind users to verify with the relevant EMU office when needed.
- It must not say: “This is the university’s official final answer.”
- It must not invent policy interpretation unsupported by retrieved evidence.

When text is ambiguous or missing, default behavior should be:

1. Clarify if the query is underspecified.
2. Answer with uncertainty if partial evidence exists.
3. Refuse/redirect if no reliable evidence exists.
4. Show source conflict if sources disagree.

---

## 4. Source Scope

### 4.1 Allowed V1 Sources

V1 source scope is limited to:

- Official EMU regulations website: `mevzuat.emu.edu.tr`
- Official PDFs linked from or belonging to the regulation source set

### 4.2 Excluded Until Later Versions

The following are excluded from V1:

- Program descriptions
- Course pages
- Faculty pages, unless explicitly part of official regulation corpus later
- Department pages
- Events and announcements
- Activity center information
- General university FAQ content
- Email announcements
- Private handbooks or internal restricted documents
- SIS/student database records

---

## 5. Language Behavior

### 5.1 Launch Languages

V1 supports:

- English
- Turkish

### 5.2 Critical Language Rule

English and Turkish regulations must be treated as separate corpora because they are not one-to-one translations and may contain different rules.

The assistant must not merge Turkish and English regulatory evidence into one answer in V1.

### 5.3 Routing Behavior

Default behavior:

- Detect user query language.
- Search only the matching language corpus.
- Clearly label source language when showing results.

### 5.4 Translation Add-on Later

A future translation add-on may:

- Translate the user query into the source language for retrieval.
- Translate quoted/summarized results into the user’s language.

But it must not mix legal sources across languages in V1.

---

## 6. Answer Style

V1 answers should be:

- Detailed enough to explain the rule.
- Plain-language and readable.
- Evidence-grounded.
- Honest about uncertainty.
- Bottom-cited.
- Able to quote exact regulation text and then explain it.

Recommended structure:

```text
Answer / summary

Relevant quoted rule text

Plain-language explanation

Limitations / uncertainty, if any

Citations
```

---

## 7. Citation Requirements

### 7.1 Citation Placement

For V1, citations appear at the bottom of the answer.

### 7.2 HTML Citation Format

For HTML sources, cite:

```text
Regulation title + section/article + URL
```

### 7.3 PDF Citation Format

For PDF sources, cite:

```text
Regulation title + section/article + page number + URL
```

### 7.4 Traceability Requirement

Every answer must be traceable to:

- Source document
- Source URL/path
- Source version/hash
- Crawl timestamp
- Chunk(s) used

---

## 8. PDF Handling Requirements

Official PDFs must be parsed with enough structure to preserve:

- Page numbers
- Headings
- Tables
- Article/section hierarchy
- Citation-relevant metadata

Plain text extraction alone is not sufficient for reliable regulation QA.

---

## 9. Conflict Policy

If two sources conflict, the system should not decide which one wins unless a formal authority hierarchy is later defined.

Default behavior:

- Show both pieces of evidence.
- Mark the conflict clearly.
- Tell the user to verify with the relevant office.

The system must not hide conflicts or synthesize a false consensus.

---

## 10. Canonical Document Schema

A normalized schema is a hard requirement before expanding beyond V1.

Minimum fields:

```yaml
document_id: string
chunk_id: string
parent_document_id: string | null
source_type: html | pdf | docx | pptx | xlsx | other
source_url: string
source_title: string
language: en | tr
corpus: regulations_en | regulations_tr | future_programs | future_events | other
access_tier: public | staff | student | faculty | department | admin
effective_date: date | null
last_crawled_at: datetime
version_hash: string
section_path: string | null
article_number: string | null
page_number: int | null
chunk_text: string
metadata: object
```

This schema is the stable contract between ingestion, indexing, retrieval, citations, and auditability.

---

## 11. Current Prototype Capabilities

The existing project already includes much of the RAG pipeline:

- Crawler
- Classifier
- Extractor
- Compiler
- Chunker
- Deduplication/postprocessing
- FAISS/BM25 indexing
- Hybrid retrieval
- Multilingual reranker
- FastAPI backend
- Basic web UI
- Ollama local synthesis
- Citations
- Clarification flow
- Refresh endpoint
- Seeded evaluation queries

This means the project is not a toy prototype. The main work is hardening, productization, evaluation, storage migration, model selection, and governance.

---

## 12. Known Technical Correction

The current use of `intfloat/e5-base-v2` is a mismatch for the intended bilingual English/Turkish system because it is English-focused and limited for this use case.

Priority correction:

- Replace with a multilingual embedding model.
- Test retrieval quality separately on English and Turkish regulation questions.

Candidate families:

- BGE-M3
- multilingual-E5 variants
- gte-multilingual variants
- Qwen3 Embedding variants

---

## 13. Storage Direction

The user prefers migration over keeping the current BM25+FAISS setup.

Primary reason:

- Retrieval power matters more than operational simplicity.

Recommended direction:

```text
Qdrant-backed retrieval stack
```

Rationale:

- Payload metadata filtering
- Named vectors
- Sparse/dense/hybrid retrieval options
- Future access tiers
- Multi-corpus retrieval
- More scalable retrieval architecture

Important rule:

> Migrating to Qdrant should not mean abandoning lexical retrieval principles. The system still needs hybrid retrieval behavior.

---

## 14. Target Architecture

Recommended V1 architecture:

```text
[Sources]
  mevzuat HTML
  official PDFs
      ↓
[Ingestion Layer]
  crawler
  PDF parser
  metadata extractor
  deduplication
  version hashing
      ↓
[Canonical Document Store]
  normalized docs/chunks
  language metadata
  source metadata
  version metadata
  citation metadata
      ↓
[Indexing Layer]
  Qdrant dense/sparse/hybrid indexes
  payload indexes
      ↓
[Retrieval Router]
  language detection
  corpus selection
  no EN/TR corpus mixing in V1
  access-tier enforcement later
      ↓
[Mode Preset]
  cheap / balanced / expensive
      ↓
[Answerability Gate]
  strong / medium / weak evidence
  ambiguity detection
  conflict detection
  refusal/clarification decision
      ↓
[Answer Layer]
  extractive fallback
  local LLM streaming generation
  citations
      ↓
[UI]
  EMU-branded web interface
  bottom citations
  source traceability
```

Likely service components:

- FastAPI backend
- Qdrant vector database
- Local embedding service
- Local reranker service
- Local LLM service through Ollama, llama.cpp, or vLLM depending on hardware
- CLI admin tools
- EMU-branded web UI

---

## 15. Local-Only Model and API Policy

The system must use local models only.

No external APIs are allowed.

Local HTTP services are allowed, for example:

- FastAPI backend
- Ollama local server
- llama.cpp server
- vLLM server
- Qdrant server
- Local embedding/reranking service

Models may be downloaded during setup, but runtime should not depend on external APIs.

---

## 16. Hardware and Deployment

### 16.1 Known Demo Hardware

Laptop/demo machine:

```text
CPU: Intel i9-14900KF
RAM: 64GB
GPU: RTX 4090
VRAM: 24GB
```

### 16.2 Campus Server

Currently unknown:

- Server OS
- CPU
- RAM
- GPU
- VRAM
- CUDA availability
- Docker permission
- Whether multiple services are allowed
- Storage capacity/type

### 16.3 Deployment Targets

V1/demo may run on:

- User laptop
- University/lab Windows machines
- Campus server later

Server deployment remains pending IT confirmation.

---

## 17. Operating Modes

The system has three operating modes:

- Cheap
- Balanced
- Expensive

These modes must vary the full pipeline, not only the LLM size.

### 17.1 Cheap Mode

Goal:

- Run on modest hardware.
- Provide acceptable grounded answers.
- Use extractive fallback often.

Characteristics:

- Lower retrieval fanout
- Small multilingual embedder
- Light or no reranker
- Smaller/quantized LLM
- Aggressive caching
- Strict fallback behavior
- Slower full generated answer acceptable

Candidate stack:

```text
Embedding: BGE-M3 / multilingual-E5 / gte-multilingual-base
Reranker: none or small reranker
LLM: small Qwen / Phi / Gemma variant, quantized
Serving: Ollama or llama.cpp
```

### 17.2 Balanced Mode

Goal:

- Normal demo/pilot quality.
- Better retrieval and explanation quality.

Characteristics:

- Hybrid retrieval
- Multilingual reranker
- Moderate context size
- 8B–14B or 24B quantized local LLM
- Good citation discipline

Candidate stack:

```text
Embedding: BGE-M3 or Qwen3-Embedding-0.6B
Reranker: bge-reranker-v2-m3 or Qwen3-Reranker-0.6B
LLM: Qwen 8B–14B / Mistral Small 24B Q4
Serving: Ollama for demo, vLLM if GPU server exists
```

### 17.3 Expensive Mode

Goal:

- Highest quality benchmark mode.
- Not default deployment mode unless hardware supports it.

Characteristics:

- Higher retrieval fanout
- Stronger reranker
- Larger context
- Stronger local LLM
- More expensive compute
- vLLM preferred if proper GPU server exists

Candidate stack:

```text
Embedding/reranker: larger Qwen3 embedding/reranker if hardware allows
LLM: stronger Qwen/Mistral model
Serving: vLLM preferred
```

---

## 18. Latency Targets

Earlier “20 seconds max latency” conflicts with later mode-specific timings. The normalized latency target should use three separate measures:

1. Extractive answer shown by
2. First generated token by
3. Full generated answer by

Recommended normalized targets:

| Mode | Extractive Answer Shown By | First Generated Token By | Full Generated Answer By |
|---|---:|---:|---:|
| Cheap | ≤ 10s | ≤ 20s | ≤ 60s |
| Balanced | ≤ 5s | ≤ 10s | ≤ 30s |
| Expensive | ≤ 3s | ≤ 5s | ≤ 15s |

Streaming is required for V1.

---

## 19. Concurrency

The target of 50 concurrent users means:

```text
50 active sessions
```

It does not mean:

```text
50 simultaneous answer generations
```

The system should support queueing and fallback behavior under load.

---

## 20. Overload Behavior

When the LLM is slow or queued:

1. Return an extractive answer with citations first.
2. Continue streaming or append the LLM-generated answer when available.
3. Do not block the user waiting for a full generated answer if the extractive answer is ready.

---

## 21. Answerability Gate

Before generation, the system should decide whether the retrieved evidence is strong enough.

### 21.1 Strong Evidence

Conditions:

- Direct support appears in top retrieved chunks.
- Relevant evidence appears in top 5 if the answer exists.
- No major source conflict.
- Query is clear.

Behavior:

- Answer normally with citations.

### 21.2 Medium Evidence

Conditions:

- Related evidence exists but may not fully answer the question.
- Query may be underspecified.
- Retrieval confidence is moderate.

Behavior:

- Ask clarification, or answer with explicit uncertainty.

### 21.3 Weak Evidence

Conditions:

- No direct support in top 5.
- Low retrieval/reranking confidence.
- Query is out of scope.

Behavior:

- Refuse or redirect.

### 21.4 Conflict

Conditions:

- Retrieved sources disagree.

Behavior:

- Show the conflict.
- Do not resolve unless a formal precedence rule exists.
- Recommend verification with relevant office.

---

## 22. Logging and Privacy

V1 should store anonymized query logs.

Logs should support:

- Debugging retrieval failures
- Evaluation improvement
- Bad-answer triage
- Usage analytics

Logs should avoid storing directly identifying user information where possible.

---

## 23. Admin and Update Workflow

### 23.1 V1 Admin Tooling

Command-line admin tooling is enough for V1.

Admin dashboard is not required for demo.

### 23.2 Refresh Policy

Supported refresh modes:

- Manual/admin refresh
- Admin-triggered refresh endpoint or CLI command

### 23.3 Production Approval

For production-like deployment:

- Crawl detects changed/new sources.
- System generates diff report.
- User/admin reviews changes.
- Approved changes go live.

Demo may auto-update if needed.

### 23.4 Versioning

Keep previous crawl/index snapshots for:

- Audit
- Debugging
- Reproducibility

V1 does not need user-facing historical Q&A.

---

## 24. Evaluation Plan

### 24.1 Evaluation Set

V1 should be tested with:

```text
50–60 questions across English and Turkish
```

### 24.2 Gold Answer Ownership

Gold answers should be written/reviewed by:

- User
- Head of IT

### 24.3 Retrieval Gate

Core retrieval target:

> If the correct answer exists in the corpus, the correct supporting evidence must appear in the top 5 retrieved chunks.

### 24.4 Response Behavior Gate

Low confidence should trigger one of the following, depending on severity:

1. Clarification
2. Uncertain answer
3. Refusal
4. Redirection to relevant office

### 24.5 Blocker Failures

The following are blocker failures:

- Refusal despite relevant evidence existing.
- Exceeding time limits.
- Mixing Turkish and English corpora without permission.
- Overconfident incorrect answers.
- Incoherent generated answers.
- Incorrect or useless citations.
- Unsupported legal/policy interpretation.

---

## 25. UI Requirements

The UI should match EMU visual identity.

From the provided logo, core palette direction:

- Navy / deep blue
- Gold / yellow
- White
- Light gray

V1 UI should include:

- Chat interface
- Streaming response display
- Extractive fallback area or progressive answer behavior
- Bottom citations
- Source title/section/page metadata
- Clear uncertainty/refusal messages
- Possibly language/source-corpus indicator

---

## 26. Roadmap

### Phase 1 — V1 Regulation Assistant

Scope:

- Staff-only demo
- Rules/regulations only
- EN/TR separate corpora
- HTML + PDF official sources
- Local-only models
- Cited answers
- Answerability gate
- Qdrant migration
- CLI admin tools

### Phase 2 — General University Information Assistant

Possible future corpora:

- Program descriptions
- Course information
- Faculty/department pages
- Announcements
- Events
- FAQs

Requirement:

- Must be separated from policy/regulation answers in routing and UI labels.

### Phase 3 — Advisory Assistant

Possible future capabilities:

- Procedural advice
- Academic planning advice
- Staff workflow guidance
- Personalized student/staff support

Requirements before this phase:

- Authentication
- Authorization
- Access-tiered corpora
- Privacy/data minimization
- Stronger evaluation
- Clear separation from policy mode

---

## 27. Open Questions for IT

Need confirmation from IT:

```text
1. Server OS: Windows or Linux?
2. CPU model and number of cores?
3. RAM amount?
4. GPU model, if any?
5. GPU VRAM amount, if any?
6. Is NVIDIA CUDA available/supported?
7. Available disk storage and whether SSD/NVMe?
8. Is Docker allowed?
9. Can multiple local services run? Example: FastAPI, Qdrant, Ollama/vLLM/llama.cpp.
10. Is localhost/internal HTTP allowed if no external API calls are made?
11. Will the system be accessible only on campus network or externally too?
12. Any security/logging restrictions for anonymized query logs?
```

---

## 28. Immediate Implementation Priorities

Recommended next steps:

1. Define and implement canonical document/chunk schema.
2. Replace English-only embedder with multilingual embedding model.
3. Add robust EN/TR corpus routing.
4. Improve PDF parsing with page/section/article metadata.
5. Add source versioning and crawl timestamps.
6. Implement answerability/refusal gate before generation.
7. Migrate retrieval storage toward Qdrant.
8. Build 50–60 question EN/TR evaluation set.
9. Normalize latency tests by mode.
10. Prepare CLI admin refresh + diff review workflow.

---

## 29. Core Design Rules

1. Keep V1 narrow.
2. Make architecture expandable.
3. Do not mix policy, general information, and advice into one undifferentiated chatbot.
4. Do not mix English and Turkish regulation sources in V1.
5. Do not let the LLM decide unsupported policy interpretation.
6. Do not define cheap/balanced/expensive only by model size.
7. Use retrieval and answerability gates before generation.
8. Make every answer traceable to source version and crawl timestamp.
9. Prefer refusal or clarification over confident hallucination.
10. Evaluate with real EN/TR gold questions before calling the system usable.

---

## 30. Current Working Definition

```text
The V1 EMU Regulation Assistant is a local-only, staff-facing demo RAG system for answering English and Turkish EMU rules/regulations from official mevzuat HTML pages and PDFs.

It uses separate EN/TR corpora, Qdrant-backed hybrid retrieval, multilingual embeddings, optional multilingual reranking, local LLM generation, extractive fallback under load, bottom citations, source-version traceability, anonymized query logs, and CLI-based admin refresh/review.

It does not provide student/staff advice, use private student data, answer general university questions, cover events/program/course information, or mix English and Turkish regulatory sources in V1.
```
