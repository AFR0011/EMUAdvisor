Tracing "Hi" through the current pipeline:
1. routing.py — "hi" is NOT in OUT_OF_SCOPE_TERMS, so in_scope=True — passes through
2. retrieval.py — retrieves chunks, but "hi" has zero BM25 overlap with regulation docs
3. answer.py — decide_answerability() sees 0 term overlap → refuses: "I could not find reliable support..."
4. Frontend shows this in red

The /chat endpoint is a thin wrapper that forces answer_style="extractive" — no LLM, no memory, no streaming.

Plan Summary

7 phases, 8 files:

1. conversation_store.py (new) — In-memory session store, 30-min TTL, 20-message cap
2. conversation_detection.py (new) — Catches greetings/thanks/farewells in EN+TR with friendly responses; detects and expands follow-up queries
3. server.py — Rewires /chat into a proper chat pipeline with a new _handle_chat(), adds /chat/stream for NDJSON streaming
4. generation.py — build_prompt() accepts conversation history so the LLM can resolve pronouns, references
5. audit_log.py — New answer types for casual/conversation tracking
6. app.js — Session ID via sessionStorage, streaming reader, typing indicator
7. style.css / index.html** — Typing animation, conversational welcome

The key insight: casual messages short-circuit retrieval entirely, follow-ups get query expansion, and the LLM gets full conversation context — all while keeping extractive answers as the citation backbone.
Invalid tool parameters

● User approved Claude's plan
Plan saved to: ~\.claude\plans\cosmic-finding-mitten.md · /plan to edit
Chat Context Memory & Conversational Chatbot Implementation Plan

> **Superseded (2026-05-20):** Public chat at `/` was removed. User-mode chat lives at `/admin?view=user`. Streaming fix is in `emu_advisor/server.py` `_handle_chat_stream`.

Context

The current /chat endpoint only does extractive retrieval — casual messages like "Hi" get refused ("I could not find reliable support…"), and there's no conversation memory for follow-up questions. The user wants a proper chatbot experience: multi-turn memory, friendly responses to casual messages, LLM-generated answers (via local Ollama) with citations as the default, and streaming for better UX. Balanced mode should be used throughout.

Changes Overview

┌─────┬───────────────────────────────────────┬────────┬─────────────────────────────────────────┐
│  #  │                 File                  │ Action │                  What                   │
├─────┼───────────────────────────────────────┼────────┼─────────────────────────────────────────┤
│ 1   │ emu_advisor/conversation_store.py     │ NEW    │ In-memory session store with TTL,       │
│     │                                       │        │ message cap, thread safety              │
├─────┼───────────────────────────────────────┼────────┼─────────────────────────────────────────┤
│ 2   │ emu_advisor/conversation_detection.py │ NEW    │ Casual message detection + follow-up    │
│     │                                       │        │ query expansion                         │
├─────┼───────────────────────────────────────┼────────┼─────────────────────────────────────────┤
│ 3   │ emu_advisor/server.py                 │ MODIFY │ Rewire /chat handler, add /chat/stream, │
│     │                                       │        │  instantiate store                      │
├─────┼───────────────────────────────────────┼────────┼─────────────────────────────────────────┤
│ 4   │ emu_advisor/generation.py             │ MODIFY │ build_prompt() and generate() accept    │
│     │                                       │        │ conversation history                    │
├─────┼───────────────────────────────────────┼────────┼─────────────────────────────────────────┤
│ 5   │ emu_advisor/audit_log.py              │ MINOR  │ New answer_type variants for            │
│     │                                       │        │ casual/conversation                     │
├─────┼───────────────────────────────────────┼────────┼─────────────────────────────────────────┤
│ 6   │ static/app.js                         │ MODIFY │ Session ID management, streaming        │
│     │                                       │        │ reader, typing indicator                │
├─────┼───────────────────────────────────────┼────────┼─────────────────────────────────────────┤
│ 7   │ static/style.css                      │ MINOR  │ Typing indicator animation              │
├─────┼───────────────────────────────────────┼────────┼─────────────────────────────────────────┤
│ 8   │ static/index.html                     │ MINOR  │ Conversational welcome message          │
└─────┴───────────────────────────────────────┴────────┴─────────────────────────────────────────┘

---
Phase 1: Conversation Store (emu_advisor/conversation_store.py — NEW, ~100 lines)

Thread-safe in-memory session store. Each session holds a message list (capped at 20), detected language, creation time. Sessions expire after 30 minutes. Keyed by session_id (UUID).

- get_session() / create_session() / add_message() / get_history() / prune_expired()
- Instantiated in server.py's create_app() alongside the existing HybridRetriever and OllamaGenerator

Phase 2: Casual Detection & Follow-up Expansion (emu_advisor/conversation_detection.py — NEW, ~120 lines)

Two functions:

is_casual_message(query: str) -> (bool, category, response_text)
- Detects greetings, thanks, farewells, generic questions in EN + TR
- Returns friendly bilingual responses that guide users back to regulation topics
- Called at the TOP of the /chat handler — short-circuits retrieval for casual messages

is_follow_up(query: str) -> bool + expand_follow_up_query(query, last_topic) -> str
- Detects follow-ups: pronouns, short questions, "what about X", "and what"
- Expands short queries by appending the last substantive topic's key terms
- Keeps retrieval effective for abbreviated follow-ups like "what about the penalty?"

Phase 3: Rewire /chat Endpoint (emu_advisor/server.py — MODIFY)

Replace the current thin wrapper (lines 191-203) with a dedicated _handle_chat() method:

1. Get or create session via ConversationStore
2. Check is_casual_message() → if casual, respond immediately, log, return
3. Get conversation history, expand query if follow-up
4. Route + retrieve (balanced mode, top-8)
5. Build extractive answer (for citations and grounding)
6. Generate LLM answer with conversation history — prefer generated, fall back to extractive
7. Store user + assistant messages in session
8. Audit log
9. Return sanitized payload with session_id

Add prefer_generated=True parameter to _answer_request() so /ask behavior stays unchanged.

_sanitize_chat_payload() extended to include session_id in response.

Phase 4: LLM Prompt with Conversation History (emu_advisor/generation.py — MODIFY)

Modify build_prompt() to accept optional conversation_history:
- When history exists, insert recent exchanges into the system prompt before evidence
- Cap at last 6 exchanges to stay within 4096 token context with 8 evidence chunks
- When no history, behavior is identical to today

Modify generate() to accept and forward conversation_history.

Phase 5: Streaming /chat/stream (emu_advisor/server.py — ADD)

New endpoint returning StreamingResponse with NDJSON events:
- session event: session ID
- citations event: citation list (from extractive answer)
- delta events: LLM token chunks
- done event: final model info, latency

Reuses the same pipeline as /chat but streams the LLM output via generator.stream().

Phase 6: Frontend Updates

static/app.js — Session ID via sessionStorage, switch to /chat/stream, read streaming NDJSON, update message UI incrementally as deltas arrive. Add typing indicator while waiting for first token.

static/style.css — Typing indicator animation (3 bouncing dots).

static/index.html — Conversational welcome message replacing the current placeholder.

Phase 7: Audit Log Polish (emu_advisor/audit_log.py — MINOR)

Add answer_type variants: "casual", "conversation" so analytics distinguish casual/chat from regular extractive/generated answers.

---
Data Flow After Changes

"Hi"
  -> /chat/stream → session created
  -> is_casual_message("Hi") → True → friendly greeting
  -> Returns immediately, no retrieval needed

"What is the attendance requirement?"
  -> /chat/stream → is_casual → False
  -> route_query → in_scope → retrieve 8 chunks
  -> extractive answer → citations populated
  -> generator.generate(query, hits, history=[]) → streams deltas
  -> Frontend shows citations + streaming text

"what happens if I miss the limit?"
  -> /chat/stream → is_follow_up → True
  -> expand_follow_up_query → appends "attendance requirement"
  -> retrieve with expanded query → relevant penalty chunks
  -> generator.generate(query, hits, history=[prior Q+A]) → streams
  -> LLM resolves "the limit" from context

Verification

1. python -m unittest discover -s tests — existing tests still pass
2. python -m uvicorn emu_advisor.server:app --host 127.0.0.1 --port 8000 — start server
3. Open http://127.0.0.1:8000 in browser:
  - Send "Hi" → should get friendly greeting (no red refusal)
  - Ask regulation question → should stream answer with citations
  - Ask follow-up → should understand context and retrieve relevant chunks
  - Session should persist across page refresh (sessionStorage)
4. Test with Ollama off → should fall back to extractive answers gracefully