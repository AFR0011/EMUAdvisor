"""Evaluation set loading and retrieval metrics."""

from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
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
    expected_answer_keywords: List[str]
    category: str
    is_correct: Optional[bool]
    citation_ok: Optional[bool]
    notes: str


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


def evaluate_hits(case: EvaluationCase, hits: List[Dict[str, Any]]) -> RetrievalMetric:
    if case.expected_behavior in {"refuse", "clarify"}:
        return RetrievalMetric(case.case_id, case.expected_behavior, None, False, False, False)

    expected_ids = {value for value in (case.expected_chunk_id, case.expected_document_id) if value}
    rank: Optional[int] = None
    for idx, hit in enumerate(hits, start=1):
        ids = {str(hit.get("chunk_id", "")), str(hit.get("document_id", ""))}
        source_url = str(hit.get("source_url", ""))
        text = str(hit.get("chunk_text", "")).casefold()
        expected_keywords = getattr(case, "expected_answer_keywords", [])
        expected_source_url = getattr(case, "expected_source_url", None)
        keyword_hit = bool(expected_keywords) and all(
            keyword.casefold() in text for keyword in expected_keywords
        )
        source_hit = bool(expected_source_url) and expected_source_url in source_url
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
    return EvaluationCase(
        case_id=str(payload["case_id"]),
        question=str(payload["question"]),
        language=language,
        expected_behavior=behavior,
        expected_corpus=payload.get("expected_corpus"),
        expected_document_id=payload.get("expected_document_id"),
        expected_chunk_id=payload.get("expected_chunk_id"),
        expected_source_url=payload.get("expected_source_url"),
        expected_answer_keywords=[str(item) for item in payload.get("expected_answer_keywords", [])],
        category=str(payload["category"]),
        is_correct=payload.get("is_correct"),
        citation_ok=payload.get("citation_ok"),
        notes=str(payload.get("notes") or ""),
    )


def _reject_mojibake(line: str, *, line_number: int) -> None:
    markers = ("Ã", "Ä", "Å", "Â")
    if any(marker in line for marker in markers):
        raise ValueError(f"line {line_number}: possible mojibake detected")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Validate an EMU Advisor evaluation set.")
    parser.add_argument("cases", type=Path)
    return parser


def main(argv: Optional[List[str]] = None) -> int:
    args = build_parser().parse_args(argv)
    cases = load_cases(args.cases)
    categories = sorted({case.category for case in cases})
    print(json.dumps({"cases": len(cases), "categories": categories}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
