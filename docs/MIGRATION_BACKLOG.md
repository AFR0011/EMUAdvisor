# Migration Backlog

Last updated: 2026-05-04

This backlog translates the current spec and old-demo evidence into implementation work. It is not validation that the work is complete.

## P0 - Baseline Decisions

- Root `EMUAdvisor/` is the primary Git repository.
- `.old/` is an ignored local archive of the previous demo and is not active implementation code.
- The broken `.old` gitlink has been removed from the root index while keeping the local archive ignored.
- Preserve `EMU_RAG_Current_System_Specs.md` as the product source of truth until superseded by explicit docs.

## P0 - Retrieval Correctness

- Initial canonical document/chunk schema validation exists in `emu_advisor/schema.py`; integrate it across ingestion, indexing, retrieval, citation, and audit.
- Local root code now uses a deterministic multilingual hashing baseline instead of `intfloat/e5-base-v2`; replace it with a real local multilingual model before quality claims.
- Language/corpus routing exists in `emu_advisor/routing.py`; validate against real corpus artifacts.
- `eval_sets/v1_seed.jsonl` has 30 machine-readable seed cases; expand to the reviewed 50-60 question bilingual gold set with expected supporting evidence.

## P1 - Storage And Indexing

- Offline Qdrant-compatible store exists in `emu_advisor/store.py`; add real Qdrant adapter while preserving hybrid lexical plus dense retrieval behavior.
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
