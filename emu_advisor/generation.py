"""Local LLM generation via Ollama with extractive fallback support."""

from __future__ import annotations

import json
import time
from dataclasses import dataclass
from typing import Any, Dict, Iterable, Iterator, List, Mapping, Optional


DEFAULT_OLLAMA_LLM = "qwen3:8b"


@dataclass(frozen=True)
class GenerationResult:
    text: str
    model: str
    latency_ms: int
    first_token_ms: Optional[int]
    error: Optional[str] = None


class OllamaGenerator:
    def __init__(
        self,
        *,
        model: str = DEFAULT_OLLAMA_LLM,
        base_url: str = "http://localhost:11434",
        timeout_s: float = 90.0,
        num_predict: int = 320,
        num_ctx: int = 4096,
        keep_alive: str = "10m",
    ) -> None:
        self.model = model
        self.base_url = base_url.rstrip("/")
        self.timeout_s = timeout_s
        self.num_predict = num_predict
        self.num_ctx = num_ctx
        self.keep_alive = keep_alive

    def generate(self, query: str, hits: List[Mapping[str, Any]], conversation_history: Optional[List[Mapping[str, str]]] = None) -> GenerationResult:
        import httpx

        started = time.perf_counter()
        prompt = build_prompt(query, hits, conversation_history)
        try:
            response = httpx.post(
                f"{self.base_url}/api/generate",
                json={
                    "model": self.model,
                    "prompt": prompt,
                    "stream": False,
                    "think": False,
                    "keep_alive": self.keep_alive,
                    "options": {"temperature": 0.0, "num_predict": self.num_predict, "num_ctx": self.num_ctx},
                },
                timeout=self.timeout_s,
            )
            response.raise_for_status()
            text = str(response.json().get("response", "")).strip()
            latency_ms = int((time.perf_counter() - started) * 1000)
            return GenerationResult(text=text, model=self.model, latency_ms=latency_ms, first_token_ms=None)
        except Exception as exc:
            latency_ms = int((time.perf_counter() - started) * 1000)
            return GenerationResult(text="", model=self.model, latency_ms=latency_ms, first_token_ms=None, error=str(exc))

    def model_available(self, *, timeout_s: float = 1.0) -> bool:
        return bool(self.status(timeout_s=timeout_s).get("model_available"))

    def status(self, *, timeout_s: float = 2.0, smoke: bool = False) -> Dict[str, Any]:
        import httpx

        started = time.perf_counter()
        status: Dict[str, Any] = {
            "base_url": self.base_url,
            "model": self.model,
            "service_available": False,
            "model_available": False,
            "smoke_ok": None,
            "latency_ms": None,
            "error": None,
        }
        try:
            response = httpx.get(f"{self.base_url}/api/tags", timeout=timeout_s)
            response.raise_for_status()
            models = response.json().get("models", [])
            names = {str(item.get("name") or item.get("model")) for item in models if isinstance(item, dict)}
            status["service_available"] = True
            status["model_available"] = self.model in names
            if smoke and status["model_available"]:
                smoke_response = httpx.post(
                    f"{self.base_url}/api/generate",
                    json={
                        "model": self.model,
                        "prompt": "Reply with OK.",
                        "stream": False,
                        "think": False,
                        "keep_alive": self.keep_alive,
                        "options": {"temperature": 0, "num_predict": 16, "num_ctx": 512},
                    },
                    timeout=timeout_s,
                )
                smoke_response.raise_for_status()
                status["smoke_ok"] = bool(str(smoke_response.json().get("response", "")).strip())
        except Exception as exc:
            status["error"] = str(exc)
        status["latency_ms"] = int((time.perf_counter() - started) * 1000)
        return status

    def stream(self, query: str, hits: List[Mapping[str, Any]], conversation_history: Optional[List[Mapping[str, str]]] = None) -> Iterator[Dict[str, Any]]:
        import httpx

        started = time.perf_counter()
        first_token_ms: Optional[int] = None
        prompt = build_prompt(query, hits, conversation_history)
        try:
            with httpx.stream(
                "POST",
                f"{self.base_url}/api/generate",
                json={
                    "model": self.model,
                    "prompt": prompt,
                    "stream": True,
                    "think": False,
                    "keep_alive": self.keep_alive,
                    "options": {"temperature": 0.0, "num_predict": self.num_predict, "num_ctx": self.num_ctx},
                },
                timeout=self.timeout_s,
            ) as response:
                response.raise_for_status()
                for line in response.iter_lines():
                    if not line:
                        continue
                    payload = json.loads(line)
                    piece = str(payload.get("response", ""))
                    if piece and first_token_ms is None:
                        first_token_ms = int((time.perf_counter() - started) * 1000)
                    if piece:
                        yield {"type": "generated_delta", "text": piece}
                    if payload.get("done"):
                        yield {
                            "type": "generation_done",
                            "model": self.model,
                            "first_token_ms": first_token_ms,
                            "latency_ms": int((time.perf_counter() - started) * 1000),
                        }
                        return
        except Exception as exc:
            yield {
                "type": "generation_error",
                "model": self.model,
                "error": str(exc),
                "latency_ms": int((time.perf_counter() - started) * 1000),
            }


def build_prompt(query: str, hits: List[Mapping[str, Any]], conversation_history: Optional[List[Mapping[str, str]]] = None) -> str:
    # Build visible conversation context if provided. This is not chain-of-thought;
    # it is only the user/assistant transcript needed to resolve references like
    # "this", "that", "it", or "what about the documents?".
    conversation_part = ""
    if conversation_history:
        # Cap at last 6 exchanges (12 messages) to stay within the local model context window.
        history = conversation_history[-12:]
        conv_lines = []
        for msg in history:
            role = msg.get("role", "user")
            content = str(msg.get("content", msg.get("text", ""))).strip()
            if not content:
                continue
            if role == "user":
                conv_lines.append(f"User: {content}")
            else:
                conv_lines.append(f"Assistant: {content}")
        if conv_lines:
            conversation_part = "\n\nPrevious visible conversation for context only:\n" + "\n".join(conv_lines)

    evidence = []
    for idx, hit in enumerate(hits[:8], start=1):
        citation = f"{hit.get('source_title')} | {hit.get('section_path') or hit.get('article_number') or ''} | {hit.get('source_url')}"
        evidence.append(f"[{idx}] {citation}\n{hit.get('chunk_text')}")
    return (
        "You are a local-only EMU Regulation Assistant. Answer only from the cited evidence. "
        "Use the previous visible conversation only to resolve references in the current question; "
        "do not answer from chat memory unless the cited evidence supports it. "
        "If evidence is incomplete, say so. Do not claim to be the university's final official answer. "
        "Do not show hidden reasoning or chain-of-thought; write only the final concise answer."
        f"{conversation_part}\n\n"
        f"Question: {query}\n\nEvidence:\n" + "\n\n".join(evidence) + "\n\nAnswer with citations by bracket number."
    )
