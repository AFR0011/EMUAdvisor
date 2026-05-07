"""Evaluation set loading and retrieval metrics."""

from __future__ import annotations

import argparse
import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional


@dataclass(frozen=True)
class EvaluationCase:
    case_id: str
    question: str
    language: str
    expected_behavior: str
    expected_corpus: Optional[str]
    expected_document_id: Optional[str]
    expected_chunk_id: Optional[str]
    expected_source_url: Optional[str]
    expected_corpora: List[str]
    expected_chunk_ids: List[str]
    expected_source_urls: List[str]
    expected_answer_keywords: List[str]
    category: str
    is_correct: Optional[bool]
    citation_ok: Optional[bool]
    review_status: str
    notes: str
    expected_answer_text: str = ""
    prompt_type: str = ""
    difficulty: str = ""
    answer_format: str = ""
    expected_citation_paths: List[str] = field(default_factory=list)
    expected_quote_spans: List[str] = field(default_factory=list)
    grading: Dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class RetrievalMetric:
    case_id: str
    expected_behavior: str
    hit_rank: Optional[int]
    top1: bool
    top3: bool
    top5: bool


def load_cases(path: Path) -> List[EvaluationCase]:
    cases: List[EvaluationCase] = []
    with path.open("r", encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, start=1):
            if not line.strip():
                continue
            _reject_mojibake(line, line_number=line_number)
            payload = json.loads(line)
            cases.append(_case_from_payload(payload, line_number=line_number))
    if not cases:
        raise ValueError(f"no evaluation cases found in {path}")
    return cases


def validate_case_set(cases: List[EvaluationCase]) -> None:
    if len(cases) < 50:
        raise ValueError("evaluation set must include at least 50 cases")
    language_counts = {
        "en": sum(1 for case in cases if case.language == "en"),
        "tr": sum(1 for case in cases if case.language == "tr"),
    }
    provisional_seed = all(_is_provisional_seed_case(case) for case in cases)
    if not provisional_seed and (language_counts["en"] < 25 or language_counts["tr"] < 25):
        raise ValueError("evaluation set must include at least 25 English and 25 Turkish cases")
    if not any(case.expected_behavior == "answer" for case in cases):
        raise ValueError("evaluation set must include at least one answerable case")
    if not provisional_seed and not any(case.expected_behavior == "refuse" for case in cases):
        raise ValueError("evaluation set must include at least one refusal case")
    for case in cases:
        if case.expected_behavior in {"answer", "conflict"} and not _has_source_labels(case) and not _has_provisional_support(case):
            raise ValueError(f"{case.case_id}: answerable/conflict cases require expected source or chunk labels")
        if case.expected_behavior == "conflict" and len(set(case.expected_source_urls)) + len(set(case.expected_chunk_ids)) < 2:
            raise ValueError(f"{case.case_id}: conflict/cross-source cases require at least two source or chunk labels")


def evaluate_hits(case: EvaluationCase, hits: List[Dict[str, Any]]) -> RetrievalMetric:
    if case.expected_behavior in {"refuse", "clarify"}:
        return RetrievalMetric(case.case_id, case.expected_behavior, None, False, False, False)

    expected_ids = {value for value in (case.expected_chunk_id, case.expected_document_id) if value}
    expected_ids.update(case.expected_chunk_ids)
    expected_sources = {case.expected_source_url} if case.expected_source_url else set()
    expected_sources.update(case.expected_source_urls)
    rank: Optional[int] = None
    for idx, hit in enumerate(hits, start=1):
        ids = {str(hit.get("chunk_id", "")), str(hit.get("document_id", ""))}
        source_url = str(hit.get("source_url", ""))
        text = str(hit.get("chunk_text", "")).casefold()
        expected_keywords = getattr(case, "expected_answer_keywords", [])
        keyword_hit = bool(expected_keywords) and all(
            keyword.casefold() in text for keyword in expected_keywords
        )
        source_hit = bool(expected_sources) and source_url in expected_sources
        if (expected_ids and expected_ids & ids) or source_hit or keyword_hit:
            rank = idx
            break

    return RetrievalMetric(
        case_id=case.case_id,
        expected_behavior=case.expected_behavior,
        hit_rank=rank,
        top1=rank == 1,
        top3=rank is not None and rank <= 3,
        top5=rank is not None and rank <= 5,
    )


def summarize_metrics(metrics: Iterable[RetrievalMetric]) -> Dict[str, Any]:
    metrics_list = list(metrics)
    answerable = [m for m in metrics_list if m.expected_behavior == "answer"]
    denominator = max(len(answerable), 1)
    return {
        "cases": len(metrics_list),
        "answerable_cases": len(answerable),
        "top1": sum(1 for m in answerable if m.top1) / denominator,
        "top3": sum(1 for m in answerable if m.top3) / denominator,
        "top5": sum(1 for m in answerable if m.top5) / denominator,
    }


def _case_from_payload(payload: Dict[str, Any], *, line_number: int) -> EvaluationCase:
    if "eval_id" in payload and "case_id" not in payload:
        payload["case_id"] = payload["eval_id"]
    if "user_prompt" in payload and "question" not in payload:
        payload["question"] = payload["user_prompt"]
    required = ["case_id", "question", "language", "expected_behavior", "category"]
    for field in required:
        if not payload.get(field):
            raise ValueError(f"line {line_number}: missing {field}")
    language = payload["language"]
    if language not in {"en", "tr"}:
        raise ValueError(f"line {line_number}: language must be en or tr")
    behavior = payload["expected_behavior"]
    if behavior not in {"answer", "clarify", "refuse", "conflict"}:
        raise ValueError(f"line {line_number}: invalid expected_behavior")
    expected_answer = payload.get("expected_answer") if isinstance(payload.get("expected_answer"), dict) else {}
    citation_paths = _citation_paths(expected_answer.get("citations", []))
    quote_spans = [
        str(item.get("quote_span"))
        for item in expected_answer.get("citations", [])
        if isinstance(item, dict) and item.get("quote_span")
    ]
    return EvaluationCase(
        case_id=str(payload["case_id"]),
        question=str(payload["question"]),
        language=language,
        expected_behavior=behavior,
        expected_corpus=payload.get("expected_corpus"),
        expected_document_id=payload.get("expected_document_id"),
        expected_chunk_id=payload.get("expected_chunk_id"),
        expected_source_url=payload.get("expected_source_url"),
        expected_corpora=_string_list(payload.get("expected_corpora"), payload.get("expected_corpus")),
        expected_chunk_ids=_string_list(payload.get("expected_chunk_ids"), payload.get("expected_chunk_id")),
        expected_source_urls=_string_list(payload.get("expected_source_urls"), payload.get("expected_source_url")),
        expected_answer_keywords=[str(item) for item in payload.get("expected_answer_keywords", [])],
        category=str(payload["category"]),
        is_correct=payload.get("is_correct"),
        citation_ok=payload.get("citation_ok"),
        review_status=str(payload.get("review_status") or "unreviewed"),
        notes=str(payload.get("notes") or ""),
        expected_answer_text=str(payload.get("expected_answer_text") or expected_answer.get("answer_text") or ""),
        prompt_type=str(payload.get("prompt_type") or ""),
        difficulty=str(payload.get("difficulty") or ""),
        answer_format=str(payload.get("answer_format") or expected_answer.get("answer_format") or ""),
        expected_citation_paths=_string_list(payload.get("expected_citation_paths")) or citation_paths,
        expected_quote_spans=_string_list(payload.get("expected_quote_spans")) or quote_spans,
        grading=payload.get("grading") if isinstance(payload.get("grading"), dict) else {},
    )


def _string_list(value: Any, fallback: Optional[Any] = None) -> List[str]:
    items: List[str] = []
    if isinstance(value, list):
        items.extend(str(item) for item in value if item)
    elif value:
        items.append(str(value))
    if not items and fallback:
        items.append(str(fallback))
    return items


def _has_source_labels(case: EvaluationCase) -> bool:
    return bool(case.expected_source_urls or case.expected_chunk_ids or case.expected_source_url or case.expected_chunk_id)


def _is_provisional_seed_case(case: EvaluationCase) -> bool:
    return case.review_status.startswith("provisional_gold_seed")


def _has_provisional_support(case: EvaluationCase) -> bool:
    return _is_provisional_seed_case(case) and bool(case.expected_answer_keywords or case.expected_answer_text)


def _citation_paths(citations: Any) -> List[str]:
    paths: List[str] = []
    if not isinstance(citations, list):
        return paths
    for citation in citations:
        if not isinstance(citation, dict):
            continue
        article = citation.get("article")
        paragraph = citation.get("paragraph")
        clause = citation.get("clause")
        if not article:
            continue
        path = f"Art. {article}"
        if paragraph:
            path += f"({paragraph})"
        if clause:
            path += f"({clause})"
        paths.append(path)
    return paths


def _reject_mojibake(line: str, *, line_number: int) -> None:
    markers = ("Ã", "Ä", "Å", "Â", "Ð", "�")
    if any(marker in line for marker in markers):
        raise ValueError(f"line {line_number}: possible mojibake detected")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Validate an EMU Advisor evaluation set.")
    parser.add_argument("cases", type=Path)
    return parser


def main(argv: Optional[List[str]] = None) -> int:
    args = build_parser().parse_args(argv)
    cases = load_cases(args.cases)
    validate_case_set(cases)
    categories = sorted({case.category for case in cases})
    behaviors = {
        behavior: sum(1 for case in cases if case.expected_behavior == behavior)
        for behavior in sorted({case.expected_behavior for case in cases})
    }
    languages = {language: sum(1 for case in cases if case.language == language) for language in ("en", "tr")}
    review_statuses = sorted({case.review_status for case in cases})
    print(
        json.dumps(
            {
                "cases": len(cases),
                "languages": languages,
                "behaviors": behaviors,
                "categories": categories,
                "review_statuses": review_statuses,
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
