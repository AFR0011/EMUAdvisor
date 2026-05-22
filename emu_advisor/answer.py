"""Evidence gating, extractive answers, and streaming fallback."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable, Dict, Iterable, Iterator, List, Mapping, Optional

from .citations import Citation, unique_citations
from .routing import route_query
from .text import normalize_text, signal_terms, tokenize


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
    answer_type: str = "direct"
    evidence_groups: List[Dict[str, Any]] = field(default_factory=list)


SCHOLARSHIP_EVIDENCE_GROUPS = [
    {
        "key": "entrance_incentive",
        "title": "Entrance, incentive, and placement scholarships",
        "query": "EMU entrance incentive scholarship first 5000 tuition dormitory pocket money scholarship",
        "query_tr": "tesvik bursu giris bursu ilk 5000 burs yurt cep harcligi ogrenim ucreti",
    },
    {
        "key": "international_discount",
        "title": "International scholarships and tuition discounts",
        "query": "international student scholarship tuition fee discount exemption scholarship EMU",
        "query_tr": "uluslararasi ogrenci burs indirim ogrenim ucreti muafiyet",
    },
    {
        "key": "high_honour",
        "title": "High-honour award",
        "query": "high honour scholarship top 1 percent tuition fee monetary award",
        "query_tr": "yuksek seref akademik basari burs odul ogrenim ucreti para odulu",
    },
    {
        "key": "sports_grant",
        "title": "Sports grant",
        "query": "sports grant scholarship tuition accommodation EMU sports clubs national player",
        "query_tr": "basarili sporcu bursu spor burs ogrenim ucreti yurt milli sporcu",
    },
    {
        "key": "research_assistant",
        "title": "Research assistant and postgraduate scholarships",
        "query": "research assistant postgraduate scholarship category monthly minimum wage tuition exemption",
        "query_tr": "arastirma gorevlisi gorev bursu lisansustu burs asgari ucret ogrenim ucreti muafiyet",
    },
    {
        "key": "disability",
        "title": "Student with disability scholarship",
        "query": "student with disability scholarship tuition fee disabled students",
        "query_tr": "engelli ogrenci bursu ogrenim ucreti engelli ogrenciler",
    },
]


def decide_answerability(query: str, hits: List[Mapping[str, Any]]) -> EvidenceDecision:
    route = route_query(query)
    if not route.in_scope:
        return EvidenceDecision("weak", "refuse", route.reason, [])
    if not hits:
        return EvidenceDecision("weak", "refuse", "no retrieved evidence", [])

    copied_hits = [dict(hit) for hit in hits]
    if _asks_for_official_clarification(query):
        return EvidenceDecision("medium", "clarify", "query asks who should resolve ambiguity", copied_hits[:5])
    if _asks_about_conflict(query):
        return EvidenceDecision("conflict", "show_conflict", "query asks about potentially conflicting rules", copied_hits[:5])
    if _has_conflict(copied_hits):
        return EvidenceDecision("conflict", "show_conflict", "retrieved sources are marked as conflicting", copied_hits[:5])

    query_terms = set(signal_terms(query)) or set(tokenize(query))
    scored = []
    for hit in copied_hits:
        text_terms = set(tokenize(_evidence_text(hit)))
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
    elif _is_table_query(query) and _structured_hits(decision.supported_hits):
        structured_hits = _structured_hits(decision.supported_hits)
        text = _structured_table_answer(structured_hits)
        citations = unique_citations(structured_hits)
        return Answer(mode=decision.action, text=text, citations=citations, decision=decision, answer_type="table")
    else:
        snippets = [_focused_snippet(query, str(hit.get("chunk_text", ""))) for hit in decision.supported_hits[:3]]
        prefix = "Based on the cited regulation evidence"
        if decision.action == "answer_uncertain":
            prefix = "The indexed evidence is partial, but it suggests"
        text = prefix + ":\n\n" + "\n\n".join(f"- {snippet}" for snippet in snippets)

    return Answer(mode=decision.action, text=text, citations=citations, decision=decision)


def is_scholarship_bundle_query(query: str) -> bool:
    lowered = normalize_text(query)
    terms = set(signal_terms(query)) or set(tokenize(query))
    if not ({"scholarship", "scholarships", "burs"} & terms or "scholarship" in lowered or "burs" in lowered):
        return False
    if _scholarship_marker_group_count(lowered) >= 2:
        return True
    specific_markers = (
        "first 5000",
        "sports grant",
        "high honour",
        "research assistant",
        "postgraduate",
        "lisansustu",
        "oran",
        "rate",
        "yuzde",
        "percent",
        "disabled",
        "disability",
        "international",
    )
    if any(marker in lowered for marker in specific_markers):
        return False
    broad_markers = (
        "how to get",
        "how can i get",
        "ways",
        "types",
        "what scholarships",
        "which scholarships",
        "all scholarships",
        "nasıl",
        "nasil",
        "hangi burs",
        "burs al",
    )
    return any(marker in lowered for marker in broad_markers) or len(query.split()) <= 5


def scholarship_group_query(group: Mapping[str, str], original_query: str, *, language_hint: Optional[str] = None) -> str:
    if route_query(original_query, language_hint=language_hint).query_language == "tr":
        return str(group.get("query_tr") or group["query"])
    return str(group["query"])


def _scholarship_marker_group_count(normalized_query: str) -> int:
    groups = [
        ("sport", "spor"),
        ("research assistant", "arastirma gorevlisi", "gorev bursu"),
        ("high honour", "high honor", "yuksek seref", "akademik basari"),
        ("international", "uluslararasi"),
        ("disability", "disabled", "engelli"),
        ("entrance", "incentive", "giris", "tesvik"),
    ]
    return sum(1 for markers in groups if any(marker in normalized_query for marker in markers))


def build_topic_bundle_answer(query: str, grouped_hits: Mapping[str, List[Mapping[str, Any]]]) -> Answer:
    supported_hits: List[Dict[str, Any]] = []
    groups: List[Dict[str, Any]] = []
    lines = [
        "The indexed regulations describe several scholarship or scholarship-like routes. "
        "Here is a fast grouped overview from cited evidence:"
    ]
    for group in SCHOLARSHIP_EVIDENCE_GROUPS:
        hits = [dict(hit) for hit in grouped_hits.get(group["key"], [])]
        if not hits:
            continue
        supported_hits.extend(hits[:2])
        snippet = _focused_snippet(
            query + " " + scholarship_group_query(group, query),
            str(hits[0].get("chunk_text", "")),
            max_chars=360,
        )
        citations = [citation.as_dict() for citation in unique_citations(hits[:2], limit=2)]
        groups.append(
            {
                "key": group["key"],
                "title": group["title"],
                "summary": snippet,
                "citations": citations,
            }
        )
        lines.append(f"- {group['title']}: {snippet}")
    if not groups:
        decision = EvidenceDecision("weak", "refuse", "no scholarship bundle evidence", [])
        text = "I could not find reliable scholarship evidence in the indexed EMU regulations."
        return Answer(mode="refuse", text=text, citations=[], decision=decision, answer_type="topic_bundle")
    lines.append("Which scholarship type should I expand with eligibility, duration, and conditions?")
    decision = EvidenceDecision("strong", "answer", "deterministic scholarship evidence bundle", supported_hits)
    return Answer(
        mode="answer",
        text="\n\n".join(lines),
        citations=unique_citations(supported_hits),
        decision=decision,
        answer_type="topic_bundle",
        evidence_groups=groups,
    )


def _is_table_query(query: str) -> bool:
    lowered = normalize_text(query)
    terms = set(signal_terms(query)) or set(tokenize(query))
    table_terms = {
        "salary",
        "salaries",
        "range",
        "ranges",
        "scale",
        "scales",
        "step",
        "steps",
        "professor",
        "assistant",
        "maas",
        "barem",
        "basamak",
    }
    return bool(terms & table_terms) or any(marker in lowered for marker in ("salary range", "salary scale", "maas", "barem"))


def _structured_hits(hits: List[Mapping[str, Any]]) -> List[Dict[str, Any]]:
    structured = []
    for hit in hits:
        metadata = hit.get("metadata") if isinstance(hit.get("metadata"), Mapping) else {}
        if metadata.get("evidence_kind") in {"derived_fact", "table_row", "table_summary"}:
            structured.append(dict(hit))
    structured.sort(key=lambda hit: _structured_priority(hit), reverse=True)
    return structured


def _structured_priority(hit: Mapping[str, Any]) -> tuple[int, float]:
    metadata = hit.get("metadata") if isinstance(hit.get("metadata"), Mapping) else {}
    kind = metadata.get("evidence_kind")
    priority = {"derived_fact": 3, "table_row": 2, "table_summary": 1}.get(str(kind), 0)
    return priority, float(hit.get("score", 0.0))


def _structured_table_answer(hits: List[Mapping[str, Any]]) -> str:
    lines = ["Based on structured table evidence:"]
    seen = set()
    for hit in hits[:4]:
        text = str(hit.get("chunk_text", ""))
        if text in seen:
            continue
        seen.add(text)
        lines.append(f"- {_snippet(text, max_chars=700)}")
    return "\n\n".join(lines)


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
        "answer_type": extractive.answer_type,
        "text": extractive.text,
        "citations": [citation.as_dict() for citation in extractive.citations],
        "evidence_groups": extractive.evidence_groups,
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
    if _asks_for_official_clarification(query):
        return True
    if len(query.split()) > 2:
        return False
    documents = {hit.get("document_id") for hit in hits}
    return len(documents) > 1


def _asks_for_official_clarification(query: str) -> bool:
    lowered = query.casefold()
    return any(
        marker in lowered
        for marker in (
            "which office",
            "who should verify",
            "verify ambiguous",
            "verify conflict",
            "hangi ofis",
            "hangi ofise",
            "sorulmalı",
            "sorulmali",
            "teyit",
        )
    )


def _asks_about_conflict(query: str) -> bool:
    lowered = query.casefold()
    return any(
        marker in lowered
        for marker in (
            "conflict",
            "conflicting",
            "two rules",
            "different deadlines",
            "çelişkili",
            "celiskili",
            "farklı kurallar",
            "iki kural",
        )
    )


def _snippet(text: str, *, max_chars: int = 420) -> str:
    text = " ".join(text.split())
    if len(text) <= max_chars:
        return text
    return text[: max_chars - 3].rstrip() + "..."


def _evidence_text(hit: Mapping[str, Any]) -> str:
    return " ".join(
        str(hit.get(field, ""))
        for field in ("chunk_text", "source_title", "section_path", "article_number", "source_url")
    )


def _focused_snippet(query: str, text: str, *, max_chars: int = 420) -> str:
    query_terms = set(signal_terms(query)) or {term for term in tokenize(query) if len(term) > 2}
    sentences = _sentences(text)
    if not sentences:
        return _snippet(text, max_chars=max_chars)
    scored = []
    for idx, sentence in enumerate(sentences):
        sentence_terms = set(tokenize(sentence))
        overlap = len(query_terms & sentence_terms)
        scored.append((overlap, -idx, sentence))
    scored.sort(reverse=True)
    best = [sentence for overlap, _idx, sentence in scored if overlap > 0][:2]
    if not best:
        best = [sentences[0]]
    return _snippet(" ".join(best), max_chars=max_chars)


def _sentences(text: str) -> List[str]:
    import re

    cleaned = " ".join(text.split())
    if not cleaned:
        return []
    pieces = re.split(r"(?<=[.!?])\s+(?=[A-ZÇĞİÖŞÜ0-9(])", cleaned)
    return [piece.strip() for piece in pieces if piece.strip()]


def _conflict_answer(hits: List[Mapping[str, Any]]) -> str:
    lines = ["The retrieved regulation evidence appears to conflict. Do not treat this as a final official interpretation."]
    for hit in hits[:5]:
        title = hit.get("source_title") or hit.get("document_id")
        lines.append(f"- {title}: {_snippet(str(hit.get('chunk_text', '')))}")
    lines.append("Please verify with the relevant EMU office.")
    return "\n".join(lines)
