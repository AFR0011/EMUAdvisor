"""Evidence gating, extractive answers, and streaming fallback."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, Dict, Iterable, Iterator, List, Mapping, Optional

from .citations import Citation, unique_citations
from .routing import route_query
from .text import tokenize


@dataclass(frozen=True)
class EvidenceDecision:
    level: str
    action: str
    reason: str
    supported_hits: List[Dict[str, Any]]


@dataclass(frozen=True)
class Answer:
    mode: str
    text: str
    citations: List[Citation]
    decision: EvidenceDecision


def decide_answerability(query: str, hits: List[Mapping[str, Any]]) -> EvidenceDecision:
    route = route_query(query)
    if not route.in_scope:
        return EvidenceDecision("weak", "refuse", route.reason, [])
    if not hits:
        return EvidenceDecision("weak", "refuse", "no retrieved evidence", [])

    copied_hits = [dict(hit) for hit in hits]
    if _has_conflict(copied_hits):
        return EvidenceDecision("conflict", "show_conflict", "retrieved sources are marked as conflicting", copied_hits[:5])

    query_terms = set(tokenize(query))
    scored = []
    for hit in copied_hits:
        text_terms = set(tokenize(str(hit.get("chunk_text", ""))))
        overlap = len(query_terms & text_terms)
        score = float(hit.get("score", 0.0))
        scored.append((overlap, score, hit))
    scored.sort(key=lambda item: (item[0], item[1]), reverse=True)
    supported = [hit for overlap, _score, hit in scored if overlap > 0]

    if not supported:
        return EvidenceDecision("weak", "refuse", "retrieved chunks do not overlap the query terms", copied_hits[:3])
    if _looks_ambiguous(query, supported):
        return EvidenceDecision("medium", "clarify", "query is underspecified across multiple sources", supported[:5])
    if scored[0][0] >= 2:
        return EvidenceDecision("strong", "answer", "direct evidence appears in retrieved chunks", supported[:5])
    return EvidenceDecision("medium", "answer_uncertain", "partial evidence exists but support is limited", supported[:5])


def build_extractive_answer(query: str, hits: List[Mapping[str, Any]]) -> Answer:
    decision = decide_answerability(query, hits)
    citations = [] if decision.action == "refuse" else unique_citations(decision.supported_hits)

    if decision.action == "refuse":
        text = (
            "I could not find reliable support in the indexed EMU regulation evidence. "
            "Please verify with the relevant EMU office or narrow the question to a specific regulation."
        )
    elif decision.action == "clarify":
        titles = sorted({str(hit.get("source_title", hit.get("document_id", ""))) for hit in decision.supported_hits})
        options = "\n".join(f"- {title}" for title in titles[:5])
        text = f"The question is ambiguous. Please choose the relevant regulation or topic:\n{options}"
    elif decision.action == "show_conflict":
        text = _conflict_answer(decision.supported_hits)
    else:
        snippets = [_snippet(str(hit.get("chunk_text", ""))) for hit in decision.supported_hits[:3]]
        prefix = "Based on the cited regulation evidence"
        if decision.action == "answer_uncertain":
            prefix = "The indexed evidence is partial, but it suggests"
        text = prefix + ":\n\n" + "\n\n".join(f"- {snippet}" for snippet in snippets)

    return Answer(mode=decision.action, text=text, citations=citations, decision=decision)


def progressive_answer_events(
    query: str,
    hits: List[Mapping[str, Any]],
    *,
    generator: Optional[Callable[[str, List[Mapping[str, Any]]], Iterable[str]]] = None,
) -> Iterator[Dict[str, Any]]:
    """Yield extractive answer first, then optional generated text events."""

    extractive = build_extractive_answer(query, hits)
    yield {
        "type": "extractive_answer",
        "mode": extractive.mode,
        "text": extractive.text,
        "citations": [citation.as_dict() for citation in extractive.citations],
    }

    if generator is None or extractive.decision.action in {"refuse", "clarify", "show_conflict"}:
        yield {"type": "done", "generated": False}
        return

    try:
        for piece in generator(query, extractive.decision.supported_hits):
            yield {"type": "generated_delta", "text": piece}
        yield {"type": "done", "generated": True}
    except Exception as exc:
        yield {"type": "generation_error", "error": str(exc), "fallback_kept": True}
        yield {"type": "done", "generated": False}


def _has_conflict(hits: List[Mapping[str, Any]]) -> bool:
    groups: Dict[str, set[str]] = {}
    for hit in hits:
        metadata = hit.get("metadata") if isinstance(hit.get("metadata"), dict) else {}
        conflict_key = metadata.get("conflict_key")
        conflict_value = metadata.get("conflict_value")
        if conflict_key and conflict_value:
            groups.setdefault(str(conflict_key), set()).add(str(conflict_value))
    return any(len(values) > 1 for values in groups.values())


def _looks_ambiguous(query: str, hits: List[Mapping[str, Any]]) -> bool:
    if len(query.split()) > 3:
        return False
    documents = {hit.get("document_id") for hit in hits}
    return len(documents) > 1


def _snippet(text: str, *, max_chars: int = 420) -> str:
    text = " ".join(text.split())
    if len(text) <= max_chars:
        return text
    return text[: max_chars - 3].rstrip() + "..."


def _conflict_answer(hits: List[Mapping[str, Any]]) -> str:
    lines = ["The retrieved regulation evidence appears to conflict. Do not treat this as a final official interpretation."]
    for hit in hits[:5]:
        title = hit.get("source_title") or hit.get("document_id")
        lines.append(f"- {title}: {_snippet(str(hit.get('chunk_text', '')))}")
    lines.append("Please verify with the relevant EMU office.")
    return "\n".join(lines)
