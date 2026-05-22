"""FastAPI app for the EMU Regulation Assistant demo surface."""

from __future__ import annotations

import json
import os
import time
from contextlib import asynccontextmanager
from dataclasses import asdict
from pathlib import Path
from typing import Any, Dict, List, Literal, Mapping, Optional

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import HTMLResponse, JSONResponse, Response, StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, ConfigDict, field_validator

from .answer import (
    SCHOLARSHIP_EVIDENCE_GROUPS,
    build_extractive_answer,
    build_topic_bundle_answer,
    is_scholarship_bundle_query,
    progressive_answer_events,
    scholarship_group_query,
)
from .audit_log import AuditEvent, AuditLogger, summarize_audit_log
from .conversation_detection import expand_follow_up_query, is_casual_message, is_follow_up
from .citations import unique_citations
from .text import tokenize
from .conversation_store import get_store
from .corpus import load_corpus, load_latest_metrics
from .embeddings import create_embedding_model
from .generation import DEFAULT_OLLAMA_LLM, OllamaGenerator
from .modes import MODE_PRESETS
from .retrieval import HybridRetriever
from .routing import detect_query_language, route_query


APP_DIR = Path(__file__).resolve().parent
ROOT_DIR = APP_DIR.parent
STATIC_DIR = ROOT_DIR / "static"
USER_CHAT_RETRIEVAL_MODE = "balanced"


class AskRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    question: str
    mode: str = "balanced"
    session_id: Optional[str] = None
    answer_style: Literal["extractive", "generated", "both"] = "both"

    @field_validator("question")
    @classmethod
    def validate_question(cls, value: str) -> str:
        value = _clean_question(value)
        return value

    @field_validator("mode")
    @classmethod
    def validate_mode(cls, value: str) -> str:
        value = value.strip().casefold()
        if value not in MODE_PRESETS:
            allowed = ", ".join(sorted(MODE_PRESETS))
            raise ValueError(f"mode must be one of: {allowed}")
        return value


class ChatRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    question: str
    session_id: Optional[str] = None

    @field_validator("question")
    @classmethod
    def validate_question(cls, value: str) -> str:
        return _clean_question(value)


def create_app() -> FastAPI:
    corpus = load_corpus()
    chunks = corpus.chunks
    embedder = create_embedding_model(os.getenv("EMU_ADVISOR_EMBEDDING", "hash"))
    runtime_profile = os.getenv("EMU_ADVISOR_PROFILE", "dev").casefold()
    admin_token = os.getenv("EMU_ADVISOR_ADMIN_TOKEN", "").strip()
    if runtime_profile == "production" and not admin_token:
        raise RuntimeError("EMU_ADVISOR_ADMIN_TOKEN is required when EMU_ADVISOR_PROFILE=production")
    vector_backend = os.getenv("EMU_ADVISOR_VECTOR_BACKEND") or ("qdrant" if runtime_profile == "production" else "local")
    require_qdrant = runtime_profile == "production" or os.getenv("EMU_ADVISOR_REQUIRE_QDRANT", "").casefold() in {"1", "true", "yes"}
    retriever = HybridRetriever(
        chunks,
        embedder=embedder,
        vector_backend=vector_backend,
        qdrant_url=os.getenv("EMU_ADVISOR_QDRANT_URL", "http://localhost:6333"),
        qdrant_path=os.getenv("EMU_ADVISOR_QDRANT_PATH") or None,
        qdrant_collection=os.getenv("EMU_ADVISOR_QDRANT_COLLECTION", "emu_regulations"),
        require_qdrant=require_qdrant,
    )
    llm_timeout_s = float(os.getenv("EMU_ADVISOR_LLM_TIMEOUT_S", "30"))
    llm_probe_timeout_s = float(os.getenv("EMU_ADVISOR_LLM_PROBE_TIMEOUT_S", "10"))
    generator = OllamaGenerator(
        model=os.getenv("EMU_ADVISOR_LLM", DEFAULT_OLLAMA_LLM),
        timeout_s=llm_timeout_s,
        num_predict=int(os.getenv("EMU_ADVISOR_LLM_NUM_PREDICT", "320")),
        num_ctx=int(os.getenv("EMU_ADVISOR_LLM_NUM_CTX", "4096")),
    )
    store = get_store()
    logger = AuditLogger(ROOT_DIR / "logs" / "audit.jsonl")

    @asynccontextmanager
    async def lifespan(_app: FastAPI):
        try:
            yield
        finally:
            close = getattr(getattr(retriever, "store", None), "close", None)
            if callable(close):
                close()

    app = FastAPI(title="EMU Regulation Assistant", lifespan=lifespan)
    @app.exception_handler(RequestValidationError)
    async def validation_error_handler(_request: Request, exc: RequestValidationError) -> JSONResponse:
        return JSONResponse(status_code=422, content={"detail": _safe_validation_errors(exc.errors())})

    @app.middleware("http")
    async def board_readiness_middleware(request: Request, call_next):
        if _requires_admin_token(request, configured_token=admin_token):
            provided = _provided_admin_token(request)
            if not provided or provided != admin_token:
                return _with_security_headers(
                    JSONResponse(status_code=401, content={"detail": "admin authentication required"}),
                    request=request,
                )
        response = await call_next(request)
        return _with_security_headers(response, request=request)

    if STATIC_DIR.exists():
        app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")

    @app.get("/", response_class=HTMLResponse)
    def landing() -> str:
        return _static_html("landing.html")

    @app.get("/admin", response_class=HTMLResponse)
    def admin_console() -> str:
        return _static_html("admin.html")

    @app.get("/health")
    def health() -> Dict[str, Any]:
        return {"ok": True, "chunks": len(chunks), "corpus_source": corpus.source}

    @app.get("/whoami")
    def whoami() -> Dict[str, Any]:
        return {
            "app": app.title,
            "runtime": "local-only demo",
            "default_embedding": retriever.embedder.metadata.model_name,
            "default_llm": generator.model,
            "chunk_count": len(chunks),
        }

    @app.get("/corpus/status")
    def corpus_status() -> Dict[str, Any]:
        return {
            "source": corpus.source,
            "runtime_profile": runtime_profile,
            "vector_backend": retriever.vector_backend,
            "vector_backend_warning": retriever.backend_warning,
            "embedding_model": retriever.embedder.metadata.model_name,
            **corpus.status,
        }

    @app.get("/metrics")
    def metrics() -> Dict[str, Any]:
        return load_latest_metrics()

    @app.get("/metrics/modes")
    def mode_metrics() -> Dict[str, Any]:
        return {
            "available": False,
            "path": "artifacts/metrics/mode_comparison/comparison.json",
            "modes": {name: asdict(preset) for name, preset in MODE_PRESETS.items()},
            **_load_json_if_exists(ROOT_DIR / "artifacts" / "metrics" / "mode_comparison" / "comparison.json"),
        }

    @app.get("/analytics")
    def analytics() -> Dict[str, Any]:
        return summarize_audit_log(ROOT_DIR / "logs" / "audit.jsonl")

    @app.get("/llm/status")
    def llm_status(smoke: bool = False) -> Dict[str, Any]:
        return generator.status(timeout_s=llm_probe_timeout_s, smoke=smoke)

    @app.post("/ask")
    def ask(request: AskRequest) -> Dict[str, Any]:
        return _answer_request(request)

    @app.post("/chat")
    def chat(request: ChatRequest) -> Dict[str, Any]:
        return _handle_chat(request, prefer_generated=False)

    @app.post("/chat/stream")
    def chat_stream(request: ChatRequest) -> StreamingResponse:
        return _handle_chat_stream(request)

    def _chat_retrieve_answer(
        expanded_query: str,
        *,
        route: Any,
    ) -> tuple[Any, List[Mapping[str, Any]]]:
        if route.in_scope and is_scholarship_bundle_query(expanded_query):
            grouped_hits = {
                group["key"]: retriever.retrieve(
                    scholarship_group_query(group, expanded_query),
                    mode=USER_CHAT_RETRIEVAL_MODE,
                    route=route_query(scholarship_group_query(group, expanded_query)),
                    top_k=3,
                )
                for group in SCHOLARSHIP_EVIDENCE_GROUPS
            }
            hits = [hit for group_hits in grouped_hits.values() for hit in group_hits]
            return build_topic_bundle_answer(expanded_query, grouped_hits), hits
        hits = retriever.retrieve(expanded_query, mode=USER_CHAT_RETRIEVAL_MODE, route=route, top_k=8)
        return build_extractive_answer(expanded_query, hits), hits

    def _expand_chat_query(question: str, conversation_history: List[Mapping[str, str]]) -> str:
        """Rewrite context-dependent follow-ups into retrievable standalone queries."""
        if not conversation_history or not is_follow_up(question):
            return question

        # Prefer the last substantive user question as the topic anchor. Assistant answers
        # can be long and citation-heavy, which tends to pollute retrieval when appended.
        for msg in reversed(conversation_history):
            if msg.get("role") != "user":
                continue
            candidate = str(msg.get("text", msg.get("content", ""))).strip()
            if not candidate:
                continue
            casual, _, _ = is_casual_message(candidate)
            if casual:
                continue
            if candidate.casefold() == question.casefold():
                continue
            return expand_follow_up_query(question, candidate)

        return question

    def _handle_chat(request: ChatRequest, *, prefer_generated: bool = False) -> Dict[str, Any]:
        """Handle a chat request with session management, casual detection, and full pipeline."""
        # Get or create session
        session_id = request.session_id
        session = store.get_session(session_id)
        if session is None:
            session_id = store.create_session(session_id)
            session = store.get_session(session_id)

        # Get conversation history for LLM
        conversation_history = store.get_history(session_id)

        # Check for casual message first (short-circuit retrieval)
        is_casual, category, casual_response = is_casual_message(request.question)
        if is_casual:
            # Log the casual interaction
            store.add_message(session_id, "user", request.question)
            store.add_message(session_id, "assistant", casual_response)

            total_ms = _elapsed_ms(time.perf_counter())
            logger.log(
                AuditEvent(
                    event_type="chat_casual",
                    query=request.question,
                    session_id=session_id,
                    route={"query_language": detect_query_language(request.question), "in_scope": True},
                    answer_mode="casual",
                    latency_ms=total_ms,
                    citation_ids=[],
                )
            )
            return {
                "session_id": session_id,
                "answer": casual_response,
                "state": "casual",
                "answer_type": category,
                "language": detect_query_language(request.question),
                "citations": [],
                "evidence_groups": [],
            }

        expanded_query = _expand_chat_query(request.question, conversation_history)
        route = route_query(expanded_query)

        if not route.in_scope:
            store.add_message(session_id, "user", request.question)
            store.add_message(session_id, "assistant", "I cannot answer questions outside the scope of EMU regulations.")
            return {
                "session_id": session_id,
                "answer": "I cannot answer questions outside the scope of EMU regulations.",
                "state": "out_of_scope",
                "answer_type": "refusal",
                "language": route.query_language,
                "citations": [],
                "evidence_groups": [],
            }

        extractive_answer, hits = _chat_retrieve_answer(expanded_query, route=route)

        # Generate LLM answer with conversation history
        generated_answer = None
        generated_error = None
        generation_ms = None

        status = generator.status(timeout_s=llm_probe_timeout_s, smoke=False)
        if status.get("model_available"):
            generation_hits = extractive_answer.decision.supported_hits if extractive_answer.mode in {"answer", "answer_uncertain"} else []
            if generation_hits:
                generated = generator.generate(expanded_query, generation_hits, conversation_history)
                generation_ms = generated.latency_ms
                generated_error = generated.error
                generated_answer = generated.text or None

        # Store messages
        store.add_message(session_id, "user", request.question)
        store.add_message(session_id, "assistant", generated_answer or extractive_answer.text)

        final_answer = generated_answer if prefer_generated and generated_answer else extractive_answer.text
        citations = [citation.as_dict() for citation in extractive_answer.citations]

        total_ms = _elapsed_ms(time.perf_counter())
        logger.log(
            AuditEvent(
                event_type="chat",
                query=request.question,
                session_id=session_id,
                route=route.__dict__,
                answer_mode="both",
                latency_ms=total_ms,
                citation_ids=[citation["chunk_id"] for citation in citations],
            )
        )

        return {
            "session_id": session_id,
            "answer": final_answer,
            "extractive_answer": extractive_answer.text,
            "generated_answer": generated_answer,
            "generated_error": generated_error,
            "state": extractive_answer.mode,
            "answer_type": extractive_answer.answer_type,
            "language": route.query_language,
            "citations": citations,
            "evidence_groups": extractive_answer.evidence_groups,
            "latency_ms": total_ms,
        }

    def _generate_suggestions(query: str, hits: List[Mapping[str, Any]]) -> List[str]:
        """Generate context-aware follow-up suggestions based on the query and retrieved hits."""
        suggestions = []
        query_terms = set(tokenize(query))

        # Extract key terms from retrieved evidence
        evidence_terms = set()
        for hit in hits[:5]:
            chunk_text = str(hit.get("chunk_text", ""))
            evidence_terms.update(tokenize(chunk_text))

        # Common suggested questions based on EMU context
        common_suggestions = [
            "What are the eligibility requirements for this?",
            "How do I apply for this benefit?",
            "What documentation is needed?",
            "Where can I find more information?",
        ]

        # Build context-specific suggestions
        if "scholarship" in query_terms or "burs" in query_terms:
            suggestions = [
                "What types of scholarships are available?",
                "How do I apply for a scholarship?",
                "What are the deadlines for scholarship applications?",
            ]
        elif "attendance" in query_terms or "devam" in query_terms:
            suggestions = [
                "What is the maximum absence allowed?",
                "How do I request an excused absence?",
                "What happens if I exceed the absence limit?",
            ]
        elif "grade" in query_terms or "not" in query_terms or "notlandırma" in query_terms:
            suggestions = [
                "How are final grades calculated?",
                "What is the grading scale?",
                "How do I appeal a grade?",
            ]
        elif "exam" in query_terms or "sınav" in query_terms:
            suggestions = [
                "How are exams scheduled?",
                "What items can I bring to exams?",
                "What happens if I miss an exam?",
            ]
        else:
            # Generic suggestions based on evidence
            for suggestion in common_suggestions:
                if len(suggestions) < 3:
                    suggestions.append(suggestion)

        return suggestions[:3]  # Return up to 3 suggestions

    def _handle_chat_stream(request: ChatRequest) -> StreamingResponse:
        """Handle streaming chat request with NDJSON output."""
        session_id = request.session_id
        if store.get_session(session_id) is None:
            session_id = store.create_session(session_id)

        conversation_history = store.get_history(session_id)
        normalized_history = [
            {"role": msg.get("role", "user"), "content": msg.get("text", msg.get("content", ""))}
            for msg in conversation_history
        ]

        is_casual, category, casual_response = is_casual_message(request.question)
        if is_casual:
            store.add_message(session_id, "user", request.question)
            store.add_message(session_id, "assistant", casual_response)

            def casual_events():
                yield json.dumps({"type": "session", "session_id": session_id}, ensure_ascii=False) + "\n"
                yield json.dumps(
                    {"type": "casual", "category": category, "text": casual_response},
                    ensure_ascii=False,
                ) + "\n"
                yield json.dumps({"type": "suggestions", "questions": []}, ensure_ascii=False) + "\n"
                yield json.dumps({"type": "done"}, ensure_ascii=False) + "\n"

            return StreamingResponse(casual_events(), media_type="application/x-ndjson")

        expanded_query = _expand_chat_query(request.question, conversation_history)
        route = route_query(expanded_query)

        if not route.in_scope:
            refusal = "I cannot answer questions outside the scope of EMU regulations."
            store.add_message(session_id, "user", request.question)
            store.add_message(session_id, "assistant", refusal)

            def out_of_scope_events():
                yield json.dumps({"type": "session", "session_id": session_id}, ensure_ascii=False) + "\n"
                yield json.dumps({"type": "retrieving"}, ensure_ascii=False) + "\n"
                yield json.dumps({"type": "refusal", "text": refusal}, ensure_ascii=False) + "\n"
                yield json.dumps({"type": "suggestions", "questions": []}, ensure_ascii=False) + "\n"
                yield json.dumps({"type": "done"}, ensure_ascii=False) + "\n"

            return StreamingResponse(out_of_scope_events(), media_type="application/x-ndjson")

        def stream_events():
            yield json.dumps({"type": "session", "session_id": session_id}, ensure_ascii=False) + "\n"
            yield json.dumps({"type": "retrieving"}, ensure_ascii=False) + "\n"

            extractive_answer, hits = _chat_retrieve_answer(
                expanded_query,
                route=route,
            )
            citations = [citation.as_dict() for citation in extractive_answer.citations]
            suggestions = _generate_suggestions(expanded_query, hits)
            final_assistant_text = extractive_answer.text

            status = generator.status(timeout_s=llm_probe_timeout_s, smoke=False)
            generation_hits = (
                extractive_answer.decision.supported_hits
                if extractive_answer.mode in {"answer", "answer_uncertain"}
                else []
            )

            if status.get("model_available") and generation_hits:
                yield json.dumps({"type": "generating"}, ensure_ascii=False) + "\n"
                generated_parts: List[str] = []
                try:
                    for delta in generator.stream(expanded_query, generation_hits, normalized_history):
                        if delta.get("type") == "generated_delta" and delta.get("text"):
                            generated_parts.append(delta["text"])
                        yield json.dumps(delta, ensure_ascii=False) + "\n"
                except Exception:
                    pass
                if generated_parts:
                    final_assistant_text = "".join(generated_parts)
            else:
                yield json.dumps({"type": "generated_delta", "text": extractive_answer.text}, ensure_ascii=False) + "\n"
                yield json.dumps(
                    {
                        "type": "generated_done",
                        "model": generator.model,
                        "latency_ms": 0,
                        "error": None if status.get("model_available") else "OLLAMA_UNAVAILABLE",
                    },
                    ensure_ascii=False,
                ) + "\n"

            yield json.dumps(
                {
                    "type": "extractive_answer",
                    "text": extractive_answer.text,
                    "mode": extractive_answer.mode,
                    "answer_type": extractive_answer.answer_type,
                    "language": route.query_language,
                    "citations": citations,
                    "evidence_groups": extractive_answer.evidence_groups,
                },
                ensure_ascii=False,
            ) + "\n"
            yield json.dumps({"type": "suggestions", "questions": suggestions}, ensure_ascii=False) + "\n"
            yield json.dumps({"type": "done"}, ensure_ascii=False) + "\n"

            store.add_message(session_id, "user", request.question)
            store.add_message(session_id, "assistant", final_assistant_text)

        return StreamingResponse(stream_events(), media_type="application/x-ndjson")

    def _answer_request(request: AskRequest, *, event_type: str = "ask") -> Dict[str, Any]:
        total_started = time.perf_counter()
        route_started = time.perf_counter()
        route = route_query(request.question)
        route_ms = _elapsed_ms(route_started)
        retrieve_started = time.perf_counter()
        if route.in_scope and is_scholarship_bundle_query(request.question):
            grouped_hits = {
                group["key"]: retriever.retrieve(
                    scholarship_group_query(group, request.question),
                    mode=request.mode,
                    route=route_query(scholarship_group_query(group, request.question)),
                    top_k=3,
                )
                for group in SCHOLARSHIP_EVIDENCE_GROUPS
            }
            hits = [hit for group_hits in grouped_hits.values() for hit in group_hits]
            answer = build_topic_bundle_answer(request.question, grouped_hits)
        else:
            hits = retriever.retrieve(request.question, mode=request.mode, route=route, top_k=8)
            answer = None
        retrieve_ms = _elapsed_ms(retrieve_started)
        extractive_started = time.perf_counter()
        if answer is None:
            answer = build_extractive_answer(request.question, hits)
        extractive_ms = _elapsed_ms(extractive_started)
        citations = [citation.as_dict() for citation in answer.citations]
        generation_ms = None
        generated_answer = None
        generated_error = None
        should_generate = request.answer_style == "generated" or (
            request.answer_style == "both" and answer.answer_type != "topic_bundle"
        )
        if should_generate and answer.mode in {"answer", "answer_uncertain"}:
            status = generator.status(timeout_s=llm_probe_timeout_s, smoke=False)
            if status.get("model_available"):
                generation_hits = answer.decision.supported_hits
                if answer.answer_type == "topic_bundle":
                    generation_hits = [
                        {
                            "source_title": "Structured scholarship evidence bundle",
                            "section_path": "Grouped overview",
                            "source_url": citations[0]["source_url"] if citations else "",
                            "chunk_text": answer.text,
                        }
                    ]
                generated = generator.generate(request.question, generation_hits)
                generation_ms = generated.latency_ms
                generated_error = generated.error
                generated_answer = generated.text or None
            else:
                generation_ms = int(status.get("latency_ms") or 0)
                reason = status.get("error") or f"model not available: {generator.model}"
                generated_error = f"local Ollama generation unavailable: {reason}"
        latency_ms = _elapsed_ms(total_started)
        final_answer = generated_answer if request.answer_style == "generated" and generated_answer else answer.text
        logger.log(
            AuditEvent(
                event_type=event_type,
                query=request.question,
                session_id=request.session_id,
                route=route.__dict__,
                answer_mode=request.answer_style,
                latency_ms=latency_ms,
                citation_ids=[citation["chunk_id"] for citation in citations],
            )
        )
        return {
            "mode": answer.mode,
            "answer_type": answer.answer_type,
            "answer": final_answer,
            "extractive_answer": answer.text,
            "generated_answer": generated_answer,
            "generated_error": generated_error,
            "evidence_groups": answer.evidence_groups,
            "citations": citations,
            "hits": hits,
            "route": route.__dict__,
            "latency_ms": latency_ms,
            "timings": {
                "route_ms": route_ms,
                "retrieve_ms": retrieve_ms,
                "extractive_ms": extractive_ms,
                "generation_ms": generation_ms,
                "total_ms": latency_ms,
            },
        }

    @app.post("/ask/stream")
    def ask_stream(request: AskRequest) -> StreamingResponse:
        route = route_query(request.question)
        if route.in_scope and is_scholarship_bundle_query(request.question):
            grouped_hits = {
                group["key"]: retriever.retrieve(
                    scholarship_group_query(group, request.question),
                    mode=request.mode,
                    route=route_query(scholarship_group_query(group, request.question)),
                    top_k=3,
                )
                for group in SCHOLARSHIP_EVIDENCE_GROUPS
            }
            answer = build_topic_bundle_answer(request.question, grouped_hits)

            def bundle_events():
                yield json.dumps(
                    {
                        "type": "extractive_answer",
                        "mode": answer.mode,
                        "answer_type": answer.answer_type,
                        "text": answer.text,
                        "citations": [citation.as_dict() for citation in answer.citations],
                        "evidence_groups": answer.evidence_groups,
                    },
                    ensure_ascii=False,
                ) + "\n"
                yield json.dumps({"type": "done", "generated": False}, ensure_ascii=False) + "\n"

            return StreamingResponse(bundle_events(), media_type="application/x-ndjson")

        hits = retriever.retrieve(request.question, mode=request.mode, route=route, top_k=8)

        def events():
            for event in progressive_answer_events(request.question, hits):
                yield json.dumps(event, ensure_ascii=False) + "\n"

        return StreamingResponse(events(), media_type="application/x-ndjson")

    @app.get("/chat/sessions")
    def list_chat_sessions() -> List[Dict[str, Any]]:
        """List all active chat sessions with metadata."""
        sessions = store.list_sessions()
        return [
            {
                "session_id": s.session_id,
                "created_at": s.created_at,
                "last_active": s.last_active,
                "message_count": s.message_count,
                "last_user_message": s.last_user_message,
            }
            for s in sessions
        ]


    @app.get("/chat/session/{session_id}")
    def get_chat_session(session_id: str) -> Dict[str, Any]:
        """Return one active chat session's visible transcript."""
        session = store.get_session(session_id)
        if session is None:
            return {"session_id": session_id, "messages": [], "message_count": 0}
        messages = [
            {"role": msg.get("role", "unknown"), "text": msg.get("text", msg.get("content", ""))}
            for msg in session.get("messages", [])
        ]
        return {
            "session_id": session_id,
            "created_at": session.get("created_at"),
            "last_active": session.get("last_active"),
            "message_count": len(messages),
            "messages": messages,
        }

    class ExportRequest(BaseModel):
        session_id: str
        format: str = "markdown"  # "markdown" or "html"

        @field_validator("format")
        @classmethod
        def validate_format(cls, value: str) -> str:
            value = value.lower().strip()
            if value not in ("markdown", "html"):
                raise ValueError("format must be 'markdown' or 'html'")
            return value

    @app.post("/chat/export")
    def export_chat_session(request: ExportRequest) -> JSONResponse:
        """Export a chat session to Markdown or HTML format."""
        export = store.export_session(request.session_id, request.format)
        if export is None:
            return JSONResponse(
                status_code=404,
                content={"error": f"Session '{request.session_id}' not found"},
            )

        content_type = "text/markdown" if request.format == "markdown" else "text/html"
        return Response(content=export, media_type=content_type)

    @app.post("/chat/clear")
    def clear_chat_session(request: ChatRequest) -> Dict[str, Any]:
        """Clear messages from a chat session."""
        success = store.clear_session(request.session_id)
        if not success:
            # Try to create if doesn't exist (for IDempotency)
            store.create_session(request.session_id)
        return {"session_id": request.session_id, "cleared": True, "message_count": 0}

    return app


app = create_app()


def _elapsed_ms(started: float) -> int:
    return int((time.perf_counter() - started) * 1000)


def _static_html(filename: str) -> str:
    path = STATIC_DIR / filename
    if path.exists():
        return path.read_text(encoding="utf-8")
    return "<h1>EMU Regulation Assistant</h1>"


def _load_json_if_exists(path: Path) -> Dict[str, Any]:
    if not path.exists():
        return {}
    payload = json.loads(path.read_text(encoding="utf-8"))
    payload.setdefault("available", True)
    payload.setdefault("path", str(path.relative_to(ROOT_DIR)))
    return payload


def _clean_question(value: str) -> str:
    if not isinstance(value, str):
        raise ValueError("question must be text")
    value = value.strip()
    if not value:
        raise ValueError("question cannot be blank")
    if len(value) > 2000:
        raise ValueError("question must be 2000 characters or fewer")
    return value


def _safe_validation_errors(errors: list[Dict[str, Any]]) -> list[Dict[str, Any]]:
    safe = []
    for error in errors:
        safe.append(
            {
                "loc": list(error.get("loc", [])),
                "msg": error.get("msg", "invalid request"),
                "type": error.get("type", "value_error"),
            }
        )
    return safe


def _provided_admin_token(request: Request) -> Optional[str]:
    bearer = request.headers.get("authorization", "")
    if bearer.casefold().startswith("bearer "):
        return bearer[7:].strip()
    header_token = request.headers.get("x-emu-admin-token")
    if header_token:
        return header_token.strip()
    query_token = request.query_params.get("admin_token")
    if query_token:
        return query_token.strip()
    return None


def _requires_admin_token(request: Request, *, configured_token: str) -> bool:
    if not configured_token:
        return False
    path = request.url.path.rstrip("/") or "/"
    protected_exact = {"/admin", "/ask", "/metrics", "/metrics/modes", "/analytics", "/corpus/status"}
    if path in protected_exact or path.startswith("/ask/"):
        return True
    if path == "/llm/status" and request.query_params.get("smoke", "").casefold() in {"1", "true", "yes"}:
        return True
    return False


def _with_security_headers(response, *, request: Request):
    response.headers.setdefault("Content-Security-Policy", "default-src 'self'; script-src 'self'; style-src 'self'; img-src 'self' data:; connect-src 'self'; frame-ancestors 'none'; base-uri 'self'; form-action 'self'")
    response.headers.setdefault("X-Content-Type-Options", "nosniff")
    response.headers.setdefault("X-Frame-Options", "DENY")
    response.headers.setdefault("Referrer-Policy", "same-origin")
    response.headers.setdefault("Permissions-Policy", "camera=(), microphone=(), geolocation=()")
    if request.url.scheme == "https" or os.getenv("EMU_ADVISOR_ENABLE_HSTS", "").casefold() in {"1", "true", "yes"}:
        response.headers.setdefault("Strict-Transport-Security", "max-age=31536000; includeSubDomains")
    return response
