"""Local query rewriting for language routing and follow-up retrieval."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from typing import Any, List, Mapping, Optional

from .conversation_detection import expand_follow_up_query, is_casual_message, is_follow_up
from .generation import DEFAULT_OLLAMA_LLM
from .routing import detect_query_language


DEFAULT_QUERY_REWRITE_MODE = "llm"
DEFAULT_QUERY_REWRITE_TIMEOUT_S = 3.0
VALID_LANGUAGES = {"en", "tr"}
VALID_CONFIDENCE = {"high", "medium", "low"}
REWRITE_SCHEMA_KEYS = {
    "input_language",
    "retrieval_language",
    "standalone_query",
    "is_follow_up",
    "confidence",
}


@dataclass(frozen=True)
class QueryUnderstandingResult:
    input_language: str
    retrieval_language: str
    standalone_query: str
    is_follow_up: bool
    confidence: str
    method: str
    error: Optional[str] = None

    def as_dict(self) -> dict[str, Any]:
        return {
            "input_language": self.input_language,
            "retrieval_language": self.retrieval_language,
            "standalone_query": self.standalone_query,
            "is_follow_up": self.is_follow_up,
            "confidence": self.confidence,
            "method": self.method,
            "error": self.error,
        }


def understand_query(
    query: str,
    conversation_history: Optional[List[Mapping[str, str]]] = None,
    *,
    mode: str = DEFAULT_QUERY_REWRITE_MODE,
    model: str = DEFAULT_OLLAMA_LLM,
    base_url: str = "http://localhost:11434",
    timeout_s: float = DEFAULT_QUERY_REWRITE_TIMEOUT_S,
) -> QueryUnderstandingResult:
    """Return a standalone retrieval query using only local services."""

    fallback = deterministic_understanding(query, conversation_history, method="deterministic")
    normalized_mode = mode.strip().casefold()
    if normalized_mode in {"0", "false", "off", "none", "deterministic", "disabled"}:
        return fallback
    if normalized_mode != "llm":
        return deterministic_understanding(
            query,
            conversation_history,
            method="deterministic_fallback",
            error=f"unknown query rewrite mode: {mode}",
        )

    try:
        prompt = build_rewrite_prompt(query, conversation_history)
        payload = _call_ollama(prompt, model=model, base_url=base_url, timeout_s=timeout_s)
        result = parse_query_understanding(payload, original_query=query)
        return QueryUnderstandingResult(
            input_language=result.input_language,
            retrieval_language=result.retrieval_language,
            standalone_query=result.standalone_query,
            is_follow_up=result.is_follow_up,
            confidence=result.confidence,
            method="llm",
        )
    except Exception as exc:
        return deterministic_understanding(
            query,
            conversation_history,
            method="deterministic_fallback",
            error=str(exc),
        )


def deterministic_understanding(
    query: str,
    conversation_history: Optional[List[Mapping[str, str]]] = None,
    *,
    method: str = "deterministic",
    error: Optional[str] = None,
) -> QueryUnderstandingResult:
    """Fallback query understanding that never calls a model."""

    language = detect_query_language(query)
    follow_up = bool(conversation_history) and is_follow_up(query)
    standalone_query = query
    if follow_up:
        last_topic = _last_substantive_user_query(conversation_history, current_query=query)
        if last_topic:
            standalone_query = expand_follow_up_query(query, last_topic)
    return QueryUnderstandingResult(
        input_language=language,
        retrieval_language=language,
        standalone_query=_clean_query(standalone_query) or query,
        is_follow_up=follow_up,
        confidence="medium" if follow_up else "high",
        method=method,
        error=error,
    )


def build_rewrite_prompt(
    query: str,
    conversation_history: Optional[List[Mapping[str, str]]] = None,
) -> str:
    history_part = _format_history(conversation_history)
    return (
        "You rewrite user questions for an EMU regulation RAG retriever. "
        "You do not answer the question.\n"
        "Output only one compact JSON object with exactly these keys: "
        "input_language, retrieval_language, standalone_query, is_follow_up, confidence.\n"
        "Allowed languages are 'en' and 'tr'. Allowed confidence values are 'high', 'medium', 'low'.\n"
        "Rules:\n"
        "- If the user writes Turkish without Turkish characters, classify it as 'tr' and restore normal Turkish wording.\n"
        "- If the user switches language mid-conversation, carry the topic forward but set retrieval_language to the current user's language.\n"
        "- Never mix English and Turkish legal corpora; retrieval_language must be a single language.\n"
        "- Use prior visible conversation only to resolve references such as this, that, it, buna, bunun, or previous.\n"
        "- Keep standalone_query short, search-oriented, and in the retrieval_language.\n"
        "- Do not include citations, evidence, explanations, markdown, or extra keys.\n"
        f"{history_part}\n"
        f"Current user question: {query}\n"
        "JSON:"
    )


def parse_query_understanding(payload: str, *, original_query: str) -> QueryUnderstandingResult:
    data = _extract_json_object(payload)
    if set(data) != REWRITE_SCHEMA_KEYS:
        raise ValueError("query rewrite JSON keys did not match expected schema")
    input_language = str(data.get("input_language") or "").strip().casefold()
    retrieval_language = str(data.get("retrieval_language") or "").strip().casefold()
    confidence = str(data.get("confidence") or "").strip().casefold()
    standalone_query = _clean_query(str(data.get("standalone_query") or ""))
    is_followup_raw = data.get("is_follow_up")

    if input_language not in VALID_LANGUAGES:
        raise ValueError("query rewrite returned invalid input_language")
    if retrieval_language not in VALID_LANGUAGES:
        raise ValueError("query rewrite returned invalid retrieval_language")
    if confidence not in VALID_CONFIDENCE:
        raise ValueError("query rewrite returned invalid confidence")
    if not isinstance(is_followup_raw, bool):
        raise ValueError("query rewrite returned non-boolean is_follow_up")
    if not standalone_query:
        raise ValueError("query rewrite returned empty standalone_query")
    if len(standalone_query) > 800:
        raise ValueError("query rewrite returned oversized standalone_query")

    return QueryUnderstandingResult(
        input_language=input_language,
        retrieval_language=retrieval_language,
        standalone_query=standalone_query or original_query,
        is_follow_up=is_followup_raw,
        confidence=confidence,
        method="llm",
    )


def _call_ollama(prompt: str, *, model: str, base_url: str, timeout_s: float) -> str:
    import httpx

    response = httpx.post(
        f"{base_url.rstrip('/')}/api/generate",
        json={
            "model": model,
            "prompt": prompt,
            "stream": False,
            "think": False,
            "keep_alive": "10m",
            "options": {"temperature": 0.0, "num_predict": 180, "num_ctx": 2048},
        },
        timeout=timeout_s,
    )
    response.raise_for_status()
    return str(response.json().get("response", "")).strip()


def _extract_json_object(payload: str) -> Mapping[str, Any]:
    text = payload.strip()
    try:
        data = json.loads(text)
    except json.JSONDecodeError:
        match = re.search(r"\{.*\}", text, flags=re.DOTALL)
        if not match:
            raise ValueError("query rewrite did not return JSON") from None
        data = json.loads(match.group(0))
    if not isinstance(data, Mapping):
        raise ValueError("query rewrite JSON was not an object")
    return data


def _format_history(conversation_history: Optional[List[Mapping[str, str]]]) -> str:
    if not conversation_history:
        return "Previous visible conversation: none"

    lines = []
    for msg in conversation_history[-12:]:
        role = str(msg.get("role") or "user").strip()
        if role not in {"user", "assistant"}:
            continue
        text = _clean_query(str(msg.get("text", msg.get("content", ""))))
        if not text:
            continue
        lines.append(f"{role.title()}: {text[:700]}")
    if not lines:
        return "Previous visible conversation: none"
    return "Previous visible conversation:\n" + "\n".join(lines)


def _last_substantive_user_query(
    conversation_history: Optional[List[Mapping[str, str]]],
    *,
    current_query: str,
) -> str:
    if not conversation_history:
        return ""
    for msg in reversed(conversation_history):
        if msg.get("role") != "user":
            continue
        candidate = _clean_query(str(msg.get("text", msg.get("content", ""))))
        if not candidate or candidate.casefold() == current_query.casefold():
            continue
        casual, _, _ = is_casual_message(candidate)
        if casual:
            continue
        return candidate
    return ""


def _clean_query(value: str) -> str:
    return re.sub(r"\s+", " ", value).strip()
