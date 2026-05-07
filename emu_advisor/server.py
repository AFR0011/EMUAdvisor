"""FastAPI app for the EMU Regulation Assistant demo surface."""

from __future__ import annotations

import json
import os
import time
from contextlib import asynccontextmanager
from dataclasses import asdict
from pathlib import Path
from typing import Any, Dict, Optional

from fastapi import FastAPI
from fastapi.responses import HTMLResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from .answer import (
    SCHOLARSHIP_EVIDENCE_GROUPS,
    build_extractive_answer,
    build_topic_bundle_answer,
    is_scholarship_bundle_query,
    progressive_answer_events,
    scholarship_group_query,
)
from .audit_log import AuditEvent, AuditLogger
from .corpus import load_corpus, load_latest_metrics
from .embeddings import create_embedding_model
from .generation import DEFAULT_OLLAMA_LLM, OllamaGenerator
from .modes import MODE_PRESETS
from .retrieval import HybridRetriever
from .routing import route_query


APP_DIR = Path(__file__).resolve().parent
ROOT_DIR = APP_DIR.parent
STATIC_DIR = ROOT_DIR / "static"


class AskRequest(BaseModel):
    question: str
    mode: str = "balanced"
    session_id: Optional[str] = None
    cross_corpus: bool = False
    answer_style: str = "both"


class ChatRequest(BaseModel):
    question: str
    session_id: Optional[str] = None
    cross_corpus: bool = False


def create_app() -> FastAPI:
    corpus = load_corpus()
    chunks = corpus.chunks
    embedder = create_embedding_model(os.getenv("EMU_ADVISOR_EMBEDDING", "hash"))
    runtime_profile = os.getenv("EMU_ADVISOR_PROFILE", "dev").casefold()
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

    if STATIC_DIR.exists():
        app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")

    @app.get("/", response_class=HTMLResponse)
    def index() -> str:
        return _static_html("index.html")

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

    @app.get("/llm/status")
    def llm_status(smoke: bool = False) -> Dict[str, Any]:
        return generator.status(timeout_s=llm_probe_timeout_s, smoke=smoke)

    @app.post("/ask")
    def ask(request: AskRequest) -> Dict[str, Any]:
        return _answer_request(request)

    @app.post("/chat")
    def chat(request: ChatRequest) -> Dict[str, Any]:
        payload = _answer_request(
            AskRequest(
                question=request.question,
                mode="balanced",
                session_id=request.session_id,
                cross_corpus=request.cross_corpus,
                answer_style="extractive",
            ),
            event_type="chat",
        )
        return _sanitize_chat_payload(payload)

    def _answer_request(request: AskRequest, *, event_type: str = "ask") -> Dict[str, Any]:
        total_started = time.perf_counter()
        route_started = time.perf_counter()
        route = route_query(request.question, explicit_cross_corpus=request.cross_corpus)
        route_ms = _elapsed_ms(route_started)
        retrieve_started = time.perf_counter()
        if route.in_scope and is_scholarship_bundle_query(request.question):
            grouped_hits = {
                group["key"]: retriever.retrieve(
                    scholarship_group_query(group, request.question),
                    mode=request.mode,
                    route=route_query(
                        scholarship_group_query(group, request.question),
                        explicit_cross_corpus=request.cross_corpus,
                    ),
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
        route = route_query(request.question, explicit_cross_corpus=request.cross_corpus)
        if route.in_scope and is_scholarship_bundle_query(request.question):
            grouped_hits = {
                group["key"]: retriever.retrieve(
                    scholarship_group_query(group, request.question),
                    mode=request.mode,
                    route=route_query(
                        scholarship_group_query(group, request.question),
                        explicit_cross_corpus=request.cross_corpus,
                    ),
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


def _sanitize_chat_payload(payload: Dict[str, Any]) -> Dict[str, Any]:
    safe_citations = []
    for citation in payload.get("citations", []):
        safe_citations.append(
            {
                "label": citation.get("label"),
                "source_title": citation.get("source_title"),
                "source_url": citation.get("source_url"),
                "section_path": citation.get("section_path"),
                "article_number": citation.get("article_number"),
                "page_number": citation.get("page_number"),
            }
        )
    return {
        "answer": payload.get("answer") or payload.get("extractive_answer") or "",
        "state": payload.get("mode"),
        "answer_type": payload.get("answer_type"),
        "language": (payload.get("route") or {}).get("query_language"),
        "citations": safe_citations,
        "evidence_groups": _sanitize_evidence_groups(payload.get("evidence_groups") or []),
    }


def _sanitize_evidence_groups(groups: list[Dict[str, Any]]) -> list[Dict[str, Any]]:
    safe_groups = []
    for group in groups:
        safe_groups.append(
            {
                "title": group.get("title"),
                "summary": group.get("summary"),
                "citations": [
                    {
                        "label": citation.get("label"),
                        "source_title": citation.get("source_title"),
                        "source_url": citation.get("source_url"),
                    }
                    for citation in group.get("citations", [])
                ],
            }
        )
    return safe_groups
