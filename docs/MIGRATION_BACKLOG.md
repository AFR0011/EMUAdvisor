# Migration Backlog

Last updated: 2026-04-30

This backlog translates the current spec and old-demo evidence into implementation work. It is not validation that the work is complete.

## P0 - Baseline Decisions

- Decide whether the root `EMUAdvisor/` folder becomes the primary Git repository or whether work continues inside `NLPCrawler (Old Demo)/`.
- Remove or stop tracking generated Python cache files in the old-demo repo if that repo remains active.
- Preserve `EMU_RAG_Current_System_Specs.md` as the product source of truth until superseded by explicit docs.

## P0 - Retrieval Correctness

- Implement the canonical document/chunk schema from the spec as the contract across ingestion, indexing, retrieval, citation, and audit.
- Replace `intfloat/e5-base-v2` defaults with a multilingual embedding model and test English and Turkish separately.
- Enforce language/corpus routing so Turkish and English regulation sources are not silently mixed.
- Build the 50-60 question bilingual evaluation set with expected supporting evidence.

## P1 - Storage And Indexing

- Design the Qdrant migration while preserving hybrid lexical plus dense retrieval behavior.
- Add payload metadata indexes for language, corpus, access tier, source type, source URL/path, version hash, crawl timestamp, section, article, and page.
- Keep prior crawl/index snapshots for audit, reproducibility, and rollback.

## P1 - Source Processing

- Strengthen PDF parsing to preserve page numbers, headings, tables, article hierarchy, and citation metadata.
- Add source version hashing and crawl timestamps to every document and chunk.
- Add changed-source diff reporting before production-like refreshes go live.

## P1 - Answer Behavior

- Implement or harden the answerability gate for strong, medium, weak, and conflict cases.
- Ensure unsupported or ambiguous questions trigger clarification, uncertainty, refusal, or office redirection.
- Add conflict display when sources disagree; do not resolve conflicts without a formal precedence rule.
- Add extractive fallback behavior under slow or queued generation.

## P2 - Runtime And Operations

- Define cheap, balanced, and expensive modes across retrieval fanout, embedding, reranking, context, and local LLM choices.
- Normalize latency measurements into extractive answer time, first generated token time, and full generated answer time.
- Confirm campus/server OS, CPU, RAM, GPU, CUDA, Docker, storage, and local-service permissions with IT.
- Add anonymized query logging for debugging, evaluation improvement, and usage analytics.
- Build CLI admin refresh and approval workflow before production-like deployment.

## P2 - User Interface

- Align the UI with EMU identity: navy/deep blue, gold/yellow, white, and light gray.
- Show source language/corpus indicators.
- Show bottom citations with title, section/article, page number for PDFs, URL/path, and traceability metadata.
- Support streaming and progressive answer display when local generation is slow.
