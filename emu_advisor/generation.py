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
    ) -> None:
        self.model = model
        self.base_url = base_url.rstrip("/")
        self.timeout_s = timeout_s

    def generate(self, query: str, hits: List[Mapping[str, Any]]) -> GenerationResult:
        import httpx

        started = time.perf_counter()
        prompt = build_prompt(query, hits)
        try:
            response = httpx.post(
                f"{self.base_url}/api/generate",
                json={
                    "model": self.model,
                    "prompt": prompt,
                    "stream": False,
                    "options": {"temperature": 0.1, "num_predict": 700},
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

    def stream(self, query: str, hits: List[Mapping[str, Any]]) -> Iterator[Dict[str, Any]]:
        import httpx

        started = time.perf_counter()
        first_token_ms: Optional[int] = None
        prompt = build_prompt(query, hits)
        try:
            with httpx.stream(
                "POST",
                f"{self.base_url}/api/generate",
                json={"model": self.model, "prompt": prompt, "stream": True, "options": {"temperature": 0.1}},
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


def build_prompt(query: str, hits: List[Mapping[str, Any]]) -> str:
    evidence = []
    for idx, hit in enumerate(hits[:8], start=1):
        citation = f"{hit.get('source_title')} | {hit.get('section_path') or hit.get('article_number') or ''} | {hit.get('source_url')}"
        evidence.append(f"[{idx}] {citation}\n{hit.get('chunk_text')}")
    return (
        "You are a local-only EMU Regulation Assistant. Answer only from the cited evidence. "
        "If evidence is incomplete, say so. Do not claim to be the university's final official answer.\n\n"
        f"Question: {query}\n\nEvidence:\n" + "\n\n".join(evidence) + "\n\nAnswer with citations by bracket number."
    )
