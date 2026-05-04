"""FastAPI app for the EMU Regulation Assistant demo surface."""

from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any, Dict, Optional

from fastapi import FastAPI
from fastapi.responses import HTMLResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from .answer import build_extractive_answer, progressive_answer_events
from .audit_log import AuditEvent, AuditLogger
from .demo import demo_chunks
from .embeddings import HashEmbeddingModel
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


def create_app() -> FastAPI:
    app = FastAPI(title="EMU Regulation Assistant")
    chunks = demo_chunks()
    retriever = HybridRetriever(chunks, embedder=HashEmbeddingModel(dimensions=256))
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
        return {"ok": True, "chunks": len(chunks)}

    @app.get("/whoami")
    def whoami() -> Dict[str, Any]:
        return {
            "app": app.title,
            "runtime": "local-only demo",
            "default_embedding": retriever.embedder.metadata.model_name,
            "chunk_count": len(chunks),
        }

    @app.post("/ask")
    def ask(request: AskRequest) -> Dict[str, Any]:
        started = time.perf_counter()
        route = route_query(request.question, explicit_cross_corpus=request.cross_corpus)
        hits = retriever.retrieve(request.question, mode=request.mode, route=route, top_k=8)
        answer = build_extractive_answer(request.question, hits)
        latency_ms = int((time.perf_counter() - started) * 1000)
        citations = [citation.as_dict() for citation in answer.citations]
        logger.log(
            AuditEvent(
                event_type="ask",
                query=request.question,
                session_id=request.session_id,
                route=route.__dict__,
                answer_mode=answer.mode,
                latency_ms=latency_ms,
                citation_ids=[citation["chunk_id"] for citation in citations],
            )
        )
        return {
            "mode": answer.mode,
            "answer": answer.text,
            "citations": citations,
            "hits": hits,
            "route": route.__dict__,
            "latency_ms": latency_ms,
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
