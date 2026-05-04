"""FastAPI app for the EMU Regulation Assistant demo surface."""

from __future__ import annotations

import json
import os
import time
from pathlib import Path
from typing import Any, Dict, Optional

from fastapi import FastAPI
from fastapi.responses import HTMLResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from .answer import build_extractive_answer, progressive_answer_events
from .audit_log import AuditEvent, AuditLogger
from .corpus import load_corpus, load_latest_metrics
from .embeddings import create_embedding_model
from .generation import DEFAULT_OLLAMA_LLM, OllamaGenerator
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


def create_app() -> FastAPI:
    app = FastAPI(title="EMU Regulation Assistant")
    corpus = load_corpus()
    chunks = corpus.chunks
    embedder = create_embedding_model(os.getenv("EMU_ADVISOR_EMBEDDING", "hash"))
    retriever = HybridRetriever(chunks, embedder=embedder)
    llm_timeout_s = float(os.getenv("EMU_ADVISOR_LLM_TIMEOUT_S", "8"))
    generator = OllamaGenerator(model=os.getenv("EMU_ADVISOR_LLM", DEFAULT_OLLAMA_LLM), timeout_s=llm_timeout_s)
    logger = AuditLogger(ROOT_DIR / "logs" / "audit.jsonl")

    if STATIC_DIR.exists():
        app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")

    @app.get("/", response_class=HTMLResponse)
    def index() -> str:
        path = STATIC_DIR / "index.html"
        if path.exists():
            return path.read_text(encoding="utf-8")
        return "<h1>EMU Regulation Assistant</h1>"

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
        return {"source": corpus.source, **corpus.status}

    @app.get("/metrics")
    def metrics() -> Dict[str, Any]:
        return load_latest_metrics()

    @app.post("/ask")
    def ask(request: AskRequest) -> Dict[str, Any]:
        total_started = time.perf_counter()
        route_started = time.perf_counter()
        route = route_query(request.question, explicit_cross_corpus=request.cross_corpus)
        route_ms = _elapsed_ms(route_started)
        retrieve_started = time.perf_counter()
        hits = retriever.retrieve(request.question, mode=request.mode, route=route, top_k=8)
        retrieve_ms = _elapsed_ms(retrieve_started)
        extractive_started = time.perf_counter()
        answer = build_extractive_answer(request.question, hits)
        extractive_ms = _elapsed_ms(extractive_started)
        citations = [citation.as_dict() for citation in answer.citations]
        generation_ms = None
        generated_answer = None
        generated_error = None
        if request.answer_style in {"generated", "both"} and answer.mode in {"answer", "answer_uncertain"}:
            generated = generator.generate(request.question, answer.decision.supported_hits)
            generation_ms = generated.latency_ms
            generated_error = generated.error
            generated_answer = generated.text or None
        latency_ms = _elapsed_ms(total_started)
        final_answer = generated_answer if request.answer_style == "generated" and generated_answer else answer.text
        logger.log(
            AuditEvent(
                event_type="ask",
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
            "answer": final_answer,
            "extractive_answer": answer.text,
            "generated_answer": generated_answer,
            "generated_error": generated_error,
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
        hits = retriever.retrieve(request.question, mode=request.mode, route=route, top_k=8)

        def events():
            for event in progressive_answer_events(request.question, hits):
                yield json.dumps(event, ensure_ascii=False) + "\n"

        return StreamingResponse(events(), media_type="application/x-ndjson")

    return app


app = create_app()


def _elapsed_ms(started: float) -> int:
    return int((time.perf_counter() - started) * 1000)
