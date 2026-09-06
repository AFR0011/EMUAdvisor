"""Demo evaluation metrics and report generation."""

from __future__ import annotations

import argparse
import csv
import json
import time
from dataclasses import asdict, dataclass
from pathlib import Path
from statistics import median
from typing import Any, Dict, List, Optional

from .answer import (
    SCHOLARSHIP_EVIDENCE_GROUPS,
    build_extractive_answer,
    build_topic_bundle_answer,
    is_scholarship_bundle_query,
    scholarship_group_query,
)
from .corpus import load_chunks_jsonl
from .evaluation import (
    EvaluationCase,
    citation_matches_expected_evidence,
    evaluate_hits,
    load_cases,
    validate_case_set,
)
from .generation import OllamaGenerator
from .modes import MODE_PRESETS
from .retrieval import HybridRetriever
from .routing import route_query


TARGETS = {
    "expected_evidence_retrieval_top5_rate": 0.85,
    "refusal_behavior_match_rate": 0.90,
    "expected_evidence_citation_match_rate": 1.0,
    "extractive_latency_p50_ms": 1000,
}

MODE_LATENCY_TARGETS = {
    "cheap": {"extractive_answer_ms": 10000, "first_token_ms": 20000, "full_generated_ms": 60000},
    "balanced": {"extractive_answer_ms": 5000, "first_token_ms": 10000, "full_generated_ms": 30000},
    "expensive": {"extractive_answer_ms": 3000, "first_token_ms": 5000, "full_generated_ms": 15000},
}

SCORE_WEIGHTS = {
    "retrieval_evidence_proxy": 0.30,
    "behavior_evidence_proxy": 0.30,
    "citation_match_proxy": 0.20,
    "combined_support_proxy": 0.15,
    "nonempty_format_proxy": 0.05,
}


@dataclass(frozen=True)
class CaseResult:
    case_id: str
    mode_name: str
    category: str
    expected_behavior: str
    actual_mode: str
    retrieval_rank: Optional[int]
    retrieval_top1: bool
    retrieval_top3: bool
    retrieval_top5: bool
    behavior_evidence_proxy_pass: bool
    rejection_correct: bool
    clarification_correct: bool
    citation_present: bool
    expected_evidence_citation_match: bool
    citation_evidence_level: str
    route_ms: int
    retrieve_ms: int
    extractive_ms: int
    generation_ms: Optional[int]
    first_token_ms: Optional[int]
    generated_error: Optional[str]
    retrieval_score: float
    behavior_evidence_proxy_score: float
    citation_match_proxy_score: float
    combined_support_proxy_score: float
    nonempty_format_proxy_score: float
    weighted_proxy_score: float
    failure_reason: str
    answer: str
    citations: str
    notes: str


def run_evaluation(
    *,
    cases_path: Path,
    chunks_path: Path,
    out_dir: Path,
    mode: str = "balanced",
    include_generation: bool = False,
    generator: Optional[OllamaGenerator] = None,
) -> Dict[str, Any]:
    cases = load_cases(cases_path)
    validate_case_set(cases)
    chunks = load_chunks_jsonl(chunks_path)
    retriever = HybridRetriever(chunks)
    generator = generator or OllamaGenerator()
    generation_status: Optional[Dict[str, Any]] = None
    generation_skip_reason: Optional[str] = None
    if include_generation and hasattr(generator, "status"):
        generation_status = generator.status(timeout_s=float(getattr(generator, "timeout_s", 10.0)), smoke=True)  # type: ignore[attr-defined]
        if not generation_status.get("model_available"):
            generation_skip_reason = f"local Ollama model unavailable: {getattr(generator, 'model', None)}"
        elif generation_status.get("smoke_ok") is not True:
            generation_skip_reason = generation_status.get("error") or f"local Ollama smoke generation failed: {getattr(generator, 'model', None)}"
    results: List[CaseResult] = []

    for case in cases:
        route_start = time.perf_counter()
        route = route_query(case.question)
        route_ms = _elapsed_ms(route_start)

        retrieve_start = time.perf_counter()
        if route.in_scope and is_scholarship_bundle_query(case.question):
            grouped_hits = {}
            for group in SCHOLARSHIP_EVIDENCE_GROUPS:
                group_query = scholarship_group_query(group, case.question)
                grouped_hits[group["key"]] = retriever.retrieve(
                    group_query,
                    mode=mode,
                    route=route_query(group_query),
                    top_k=3,
                )
            hits = _flatten_grouped_hits(grouped_hits)
        else:
            grouped_hits = None
            hits = retriever.retrieve(case.question, mode=mode, route=route, top_k=8)
        retrieve_ms = _elapsed_ms(retrieve_start)

        extractive_start = time.perf_counter()
        answer = (
            build_topic_bundle_answer(case.question, grouped_hits)
            if grouped_hits is not None
            else build_extractive_answer(case.question, hits)
        )
        extractive_ms = _elapsed_ms(extractive_start)

        metric = evaluate_hits(case, hits)
        citations = [citation.as_dict() for citation in answer.citations]
        generated_ms: Optional[int] = None
        first_token_ms: Optional[int] = None
        generated_error: Optional[str] = None
        if include_generation and answer.mode in {"answer", "answer_uncertain"} and not generation_skip_reason:
            generation_hits = answer.decision.supported_hits
            if answer.answer_type == "topic_bundle":
                generation_hits = [
                    {
                        "source_title": "Structured scholarship evidence bundle",
                        "section_path": "Grouped overview",
                        "source_url": answer.citations[0].source_url if answer.citations else "",
                        "chunk_text": answer.text,
                    }
                ]
            generated = generator.generate(case.question, generation_hits)
            generated_ms = generated.latency_ms
            first_token_ms = generated.first_token_ms
            generated_error = generated.error

        citation_present = bool(citations) if case.expected_behavior in {"answer", "conflict"} else True
        expected_evidence_citation_match, citation_evidence_level = citation_matches_expected_evidence(case, citations)
        if case.expected_behavior not in {"answer", "conflict"}:
            expected_evidence_citation_match = True
            citation_evidence_level = "not_applicable"
        behavior_evidence_proxy_pass = _behavior_evidence_proxy_pass(
            case,
            answer.text,
            metric.top5,
            actual_mode=answer.mode,
            expected_evidence_citation_match=expected_evidence_citation_match,
        )
        rejection_correct = case.expected_behavior == "refuse" and answer.mode == "refuse"
        clarification_correct = case.expected_behavior == "clarify" and answer.mode == "clarify"
        failure_reason = _failure_reason(
            case=case,
            actual_mode=answer.mode,
            metric=metric,
            behavior_evidence_proxy_pass=behavior_evidence_proxy_pass,
            rejection_correct=rejection_correct,
            clarification_correct=clarification_correct,
            citation_present=citation_present,
            expected_evidence_citation_match=expected_evidence_citation_match,
        )
        score_parts = _score_case(
            case=case,
            metric=metric,
            answer_text=answer.text,
            actual_mode=answer.mode,
            behavior_evidence_proxy_pass=behavior_evidence_proxy_pass,
            rejection_correct=rejection_correct,
            clarification_correct=clarification_correct,
            expected_evidence_citation_match=expected_evidence_citation_match,
            failure_reason=failure_reason,
        )
        results.append(
            CaseResult(
                case_id=case.case_id,
                mode_name=mode,
                category=case.category,
                expected_behavior=case.expected_behavior,
                actual_mode=answer.mode,
                retrieval_rank=metric.hit_rank,
                retrieval_top1=metric.top1,
                retrieval_top3=metric.top3,
                retrieval_top5=metric.top5,
                behavior_evidence_proxy_pass=behavior_evidence_proxy_pass,
                rejection_correct=rejection_correct,
                clarification_correct=clarification_correct,
                citation_present=citation_present,
                expected_evidence_citation_match=expected_evidence_citation_match,
                citation_evidence_level=citation_evidence_level,
                route_ms=route_ms,
                retrieve_ms=retrieve_ms,
                extractive_ms=extractive_ms,
                generation_ms=generated_ms,
                first_token_ms=first_token_ms,
                generated_error=generated_error,
                retrieval_score=score_parts["retrieval_evidence_proxy"],
                behavior_evidence_proxy_score=score_parts["behavior_evidence_proxy"],
                citation_match_proxy_score=score_parts["citation_match_proxy"],
                combined_support_proxy_score=score_parts["combined_support_proxy"],
                nonempty_format_proxy_score=score_parts["nonempty_format_proxy"],
                weighted_proxy_score=score_parts["weighted_proxy"],
                failure_reason=failure_reason,
                answer=answer.text,
                citations=json.dumps(citations, ensure_ascii=False),
                notes=case.notes,
            )
        )

    summary = summarize_case_results(results)
    summary["mode"] = mode
    summary["mode_preset"] = asdict(MODE_PRESETS[mode])
    summary["mode_latency_targets"] = MODE_LATENCY_TARGETS[mode]
    summary["score_weights"] = SCORE_WEIGHTS
    summary["generated_model"] = getattr(generator, "model", None) if include_generation else None
    summary["generated_status"] = generation_status
    summary["generated_unavailable_reason"] = generation_skip_reason
    write_reports(results, summary, out_dir=out_dir)
    return summary


def run_all_modes(
    *,
    cases_path: Path,
    chunks_path: Path,
    out_dir: Path,
    include_generation: bool = False,
    generator_factory=None,
) -> Dict[str, Any]:
    out_dir.mkdir(parents=True, exist_ok=True)
    results: Dict[str, Any] = {}
    for mode in MODE_PRESETS:
        generator = generator_factory() if generator_factory else None
        results[mode] = run_evaluation(
            cases_path=cases_path,
            chunks_path=chunks_path,
            out_dir=out_dir / mode,
            mode=mode,
            include_generation=include_generation,
            generator=generator,
        )
    comparison = {
        "schema_version": "emu-advisor-automated-proxy/v2",
        "evidence_class": "automated_regression_proxy",
        "verified": False,
        "available": True,
        "cases_path": str(cases_path),
        "chunks_path": str(chunks_path),
        "modes": {name: asdict(preset) for name, preset in MODE_PRESETS.items()},
        "results": results,
        "ranking": _rank_modes(results),
        "score_weights": SCORE_WEIGHTS,
        "mode_latency_targets": MODE_LATENCY_TARGETS,
    }
    (out_dir / "comparison.json").write_text(json.dumps(comparison, ensure_ascii=False, indent=2, sort_keys=True), encoding="utf-8")
    (out_dir / "comparison.md").write_text(_mode_comparison_markdown(comparison), encoding="utf-8")
    return comparison


def summarize_case_results(results: List[CaseResult]) -> Dict[str, Any]:
    answerable = [result for result in results if result.expected_behavior in {"answer", "conflict"}]
    refusals = [result for result in results if result.expected_behavior == "refuse"]
    clarifications = [result for result in results if result.expected_behavior == "clarify"]
    extractive_latencies = [result.extractive_ms + result.retrieve_ms + result.route_ms for result in results]
    generation_attempts = [result for result in results if result.generation_ms is not None or result.generated_error]
    successful_generations = [result for result in generation_attempts if not result.generated_error and result.generation_ms is not None]
    generation_latencies = [result.generation_ms for result in successful_generations]
    first_token_latencies = [result.first_token_ms for result in successful_generations if result.first_token_ms is not None]

    summary = {
        "schema_version": "emu-advisor-automated-proxy/v2",
        "evidence_class": "automated_regression_proxy",
        "verified": False,
        "available": True,
        "cases": len(results),
        "answerable_cases": len(answerable),
        "rejection_cases": len(refusals),
        "clarification_cases": len(clarifications),
        "expected_evidence_retrieval_top1_rate": _rate(answerable, lambda result: result.retrieval_top1),
        "expected_evidence_retrieval_top3_rate": _rate(answerable, lambda result: result.retrieval_top3),
        "expected_evidence_retrieval_top5_rate": _rate(answerable, lambda result: result.retrieval_top5),
        "answer_mode_and_evidence_proxy_rate": _rate(answerable, lambda result: result.behavior_evidence_proxy_pass),
        "refusal_behavior_match_rate": _rate(refusals, lambda result: result.rejection_correct),
        "clarification_behavior_match_rate": _rate(clarifications, lambda result: result.clarification_correct),
        "citation_presence_rate": _rate(answerable, lambda result: result.citation_present),
        "expected_evidence_citation_match_rate": _rate(answerable, lambda result: result.expected_evidence_citation_match),
        "extractive_latency_p50_ms": int(median(extractive_latencies)) if extractive_latencies else None,
        "extractive_latency_p95_ms": _percentile(extractive_latencies, 0.95),
        "generated_latency_p50_ms": int(median(generation_latencies)) if generation_latencies else None,
        "generated_latency_p95_ms": _percentile(generation_latencies, 0.95),
        "generated_first_token_p50_ms": int(median(first_token_latencies)) if first_token_latencies else None,
        "generated_first_token_p95_ms": _percentile(first_token_latencies, 0.95),
        "generated_cases_attempted": len(generation_attempts),
        "generated_cases_completed": len(successful_generations),
        "generated_error_cases": len([result for result in generation_attempts if result.generated_error]),
        "generated_available": bool(successful_generations),
        "retrieval_evidence_proxy_score": _average(results, lambda result: result.retrieval_score),
        "behavior_evidence_proxy_score": _average(results, lambda result: result.behavior_evidence_proxy_score),
        "citation_match_proxy_score": _average(results, lambda result: result.citation_match_proxy_score),
        "combined_support_proxy_score": _average(results, lambda result: result.combined_support_proxy_score),
        "nonempty_format_proxy_score": _average(results, lambda result: result.nonempty_format_proxy_score),
        "weighted_proxy_score": _average(results, lambda result: result.weighted_proxy_score),
        "failure_counts": _failure_counts(results),
        "category_metrics": _category_metrics(results),
        "worst_failed_cases": _worst_failed_cases(results),
        "targets": TARGETS,
    }
    summary["automated_gate_pass"] = (
        summary["expected_evidence_retrieval_top5_rate"] is not None
        and summary["expected_evidence_retrieval_top5_rate"] >= TARGETS["expected_evidence_retrieval_top5_rate"]
        and summary["refusal_behavior_match_rate"] is not None
        and summary["refusal_behavior_match_rate"] >= TARGETS["refusal_behavior_match_rate"]
        and summary["expected_evidence_citation_match_rate"] == TARGETS["expected_evidence_citation_match_rate"]
        and summary["extractive_latency_p50_ms"] is not None
        and summary["extractive_latency_p50_ms"] < TARGETS["extractive_latency_p50_ms"]
    )
    return summary


def write_reports(results: List[CaseResult], summary: Dict[str, Any], *, out_dir: Path) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "metrics.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2, sort_keys=True), encoding="utf-8")
    if results:
        with (out_dir / "per_case.csv").open("w", encoding="utf-8", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=list(asdict(results[0]).keys()))
            writer.writeheader()
            for result in results:
                writer.writerow(asdict(result))
    with (out_dir / "human_review.csv").open("w", encoding="utf-8", newline="") as handle:
        fieldnames = ["case_id", "answer", "citations", "is_correct", "citation_ok", "notes"]
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for result in results:
            writer.writerow(
                {
                    "case_id": result.case_id,
                    "answer": result.answer,
                    "citations": result.citations,
                    "is_correct": "",
                    "citation_ok": "",
                    "notes": result.notes,
                }
            )
    (out_dir / "metrics.md").write_text(_markdown_summary(summary), encoding="utf-8")


def _behavior_evidence_proxy_pass(
    case: EvaluationCase,
    answer_text: str,
    top5: bool,
    *,
    actual_mode: str,
    expected_evidence_citation_match: bool,
) -> bool:
    if case.expected_behavior == "conflict":
        return top5 and expected_evidence_citation_match and (actual_mode == "show_conflict" or "conflict" in answer_text.casefold())
    if case.expected_behavior != "answer":
        return False
    if not top5:
        return False
    return expected_evidence_citation_match and actual_mode in {"answer", "answer_uncertain"}


def _rate(results: List[CaseResult], predicate) -> Optional[float]:
    if not results:
        return None
    return sum(1 for result in results if predicate(result)) / len(results)


def _average(results: List[CaseResult], selector) -> Optional[float]:
    if not results:
        return None
    return sum(float(selector(result)) for result in results) / len(results)


def _percentile(values: List[Optional[int]], quantile: float) -> Optional[int]:
    clean = sorted(int(value) for value in values if value is not None)
    if not clean:
        return None
    index = min(len(clean) - 1, int(round((len(clean) - 1) * quantile)))
    return clean[index]


def _elapsed_ms(started: float) -> int:
    return int((time.perf_counter() - started) * 1000)


def _flatten_grouped_hits(grouped_hits: Dict[str, List[Dict[str, Any]]]) -> List[Dict[str, Any]]:
    flattened: List[Dict[str, Any]] = []
    seen = set()
    max_depth = max((len(hits) for hits in grouped_hits.values()), default=0)
    for depth in range(max_depth):
        for group in SCHOLARSHIP_EVIDENCE_GROUPS:
            hits = grouped_hits.get(group["key"], [])
            if depth >= len(hits):
                continue
            hit = hits[depth]
            chunk_id = str(hit.get("chunk_id") or "")
            if chunk_id in seen:
                continue
            seen.add(chunk_id)
            flattened.append(hit)
    return flattened


def _failure_reason(
    *,
    case: EvaluationCase,
    actual_mode: str,
    metric,
    behavior_evidence_proxy_pass: bool,
    rejection_correct: bool,
    clarification_correct: bool,
    citation_present: bool,
    expected_evidence_citation_match: bool,
) -> str:
    if case.expected_behavior in {"answer", "conflict"}:
        if not metric.top5:
            return "expected_evidence_missing_from_top5"
        if not citation_present:
            return "missing_citation"
        if not expected_evidence_citation_match:
            return "citation_does_not_match_expected_evidence"
        if not behavior_evidence_proxy_pass:
            return "answer_mode_or_expected_evidence_proxy_failed"
    if case.expected_behavior == "refuse" and not rejection_correct:
        return "false_answer_for_refusal_case" if actual_mode != "refuse" else ""
    if case.expected_behavior == "clarify" and not clarification_correct:
        return "missing_clarification"
    return ""


def _score_case(
    *,
    case: EvaluationCase,
    metric,
    answer_text: str,
    actual_mode: str,
    behavior_evidence_proxy_pass: bool,
    rejection_correct: bool,
    clarification_correct: bool,
    expected_evidence_citation_match: bool,
    failure_reason: str,
) -> Dict[str, float]:
    if case.expected_behavior in {"answer", "conflict"}:
        if metric.top1:
            retrieval = 1.0
        elif metric.top3:
            retrieval = 0.85
        elif metric.top5:
            retrieval = 0.70
        else:
            retrieval = 0.0
        answer = 1.0 if behavior_evidence_proxy_pass else 0.0
        citation = 1.0 if expected_evidence_citation_match else 0.0
        support = 1.0 if behavior_evidence_proxy_pass and expected_evidence_citation_match and not failure_reason else 0.0
    else:
        retrieval = 1.0
        correct_behavior = rejection_correct if case.expected_behavior == "refuse" else clarification_correct
        answer = 1.0 if correct_behavior else 0.0
        citation = 1.0
        support = 1.0 if correct_behavior else 0.0
    format_score = 1.0 if str(answer_text).strip() else 0.0
    total = (
        SCORE_WEIGHTS["retrieval_evidence_proxy"] * retrieval
        + SCORE_WEIGHTS["behavior_evidence_proxy"] * answer
        + SCORE_WEIGHTS["citation_match_proxy"] * citation
        + SCORE_WEIGHTS["combined_support_proxy"] * support
        + SCORE_WEIGHTS["nonempty_format_proxy"] * format_score
    )
    return {
        "retrieval_evidence_proxy": retrieval,
        "behavior_evidence_proxy": answer,
        "citation_match_proxy": citation,
        "combined_support_proxy": support,
        "nonempty_format_proxy": format_score,
        "weighted_proxy": total,
    }


def _failure_counts(results: List[CaseResult]) -> Dict[str, int]:
    counts = {
        "failed_cases": 0,
        "expected_evidence_missing_from_top5": 0,
        "missing_citation": 0,
        "false_refusal": 0,
        "false_answer": 0,
        "missing_clarification": 0,
        "citation_does_not_match_expected_evidence": 0,
        "answer_mode_or_expected_evidence_proxy_failed": 0,
    }
    for result in results:
        failed = bool(result.failure_reason)
        if failed:
            counts["failed_cases"] += 1
            counts[result.failure_reason] = counts.get(result.failure_reason, 0) + 1
        if result.expected_behavior in {"answer", "conflict"} and result.actual_mode == "refuse":
            counts["false_refusal"] += 1
        if result.expected_behavior == "refuse" and result.actual_mode != "refuse":
            counts["false_answer"] += 1
    return counts


def _category_metrics(results: List[CaseResult]) -> Dict[str, Dict[str, Any]]:
    categories = sorted({result.category for result in results})
    out: Dict[str, Dict[str, Any]] = {}
    for category in categories:
        category_results = [result for result in results if result.category == category]
        answerable = [result for result in category_results if result.expected_behavior in {"answer", "conflict"}]
        out[category] = {
            "cases": len(category_results),
            "expected_evidence_retrieval_top5_rate": _rate(answerable, lambda result: result.retrieval_top5),
            "answer_mode_and_evidence_proxy_rate": _rate(answerable, lambda result: result.behavior_evidence_proxy_pass),
            "failed_cases": sum(1 for result in category_results if result.failure_reason),
        }
    return out


def _worst_failed_cases(results: List[CaseResult], *, limit: int = 12) -> List[Dict[str, Any]]:
    failures = [result for result in results if result.failure_reason]
    failures.sort(key=lambda result: (result.retrieval_rank is None, result.retrieval_rank or 999, result.case_id), reverse=True)
    return [
        {
            "case_id": result.case_id,
            "category": result.category,
            "expected_behavior": result.expected_behavior,
            "actual_mode": result.actual_mode,
            "retrieval_rank": result.retrieval_rank,
            "failure_reason": result.failure_reason,
        }
        for result in failures[:limit]
    ]


def _markdown_summary(summary: Dict[str, Any]) -> str:
    mode = summary.get("mode", "balanced")
    lines = [
        "# EMU Advisor Automated Regression Proxies",
        "",
        "These measurements are automated behavior/evidence proxies, not semantic answer-quality or human-review evidence.",
        "",
        f"Mode: `{mode}`",
        f"Automated gate pass: `{summary['automated_gate_pass']}`",
        "",
    ]
    for key in [
        "cases",
        "weighted_proxy_score",
        "retrieval_evidence_proxy_score",
        "behavior_evidence_proxy_score",
        "citation_match_proxy_score",
        "combined_support_proxy_score",
        "nonempty_format_proxy_score",
        "expected_evidence_retrieval_top5_rate",
        "answer_mode_and_evidence_proxy_rate",
        "refusal_behavior_match_rate",
        "clarification_behavior_match_rate",
        "citation_presence_rate",
        "expected_evidence_citation_match_rate",
        "extractive_latency_p50_ms",
        "extractive_latency_p95_ms",
        "generated_latency_p50_ms",
        "generated_first_token_p50_ms",
        "generated_cases_attempted",
        "generated_cases_completed",
        "generated_error_cases",
        "generated_available",
        "generated_model",
        "generated_unavailable_reason",
    ]:
        lines.append(f"- `{key}`: {summary.get(key)}")
    lines.append("")
    lines.append("Targets:")
    for key, value in TARGETS.items():
        lines.append(f"- `{key}`: {value}")
    lines.append("")
    lines.append("Failure analysis:")
    for key, value in summary.get("failure_counts", {}).items():
        lines.append(f"- `{key}`: {value}")
    lines.append("")
    lines.append("Worst failed cases:")
    for case in summary.get("worst_failed_cases", []):
        lines.append(
            f"- `{case['case_id']}`: {case['failure_reason']} "
            f"(mode `{case['actual_mode']}`, rank `{case['retrieval_rank']}`)"
        )
    return "\n".join(lines) + "\n"


def _rank_modes(results: Dict[str, Any]) -> List[Dict[str, Any]]:
    ranked = [
        {
            "mode": mode,
            "weighted_proxy_score": summary.get("weighted_proxy_score"),
            "expected_evidence_retrieval_top5_rate": summary.get("expected_evidence_retrieval_top5_rate"),
            "extractive_latency_p50_ms": summary.get("extractive_latency_p50_ms"),
            "failed_cases": summary.get("failure_counts", {}).get("failed_cases"),
        }
        for mode, summary in results.items()
    ]
    ranked.sort(
        key=lambda item: (
            item["weighted_proxy_score"] if item["weighted_proxy_score"] is not None else -1,
            -(item["extractive_latency_p50_ms"] or 999999),
        ),
        reverse=True,
    )
    return ranked


def _mode_comparison_markdown(comparison: Dict[str, Any]) -> str:
    lines = ["# EMU Advisor Mode Comparison", ""]
    lines.append("| Mode | Weighted proxy | Expected-evidence top-5 | p50 extractive | Failed cases |")
    lines.append("|---|---:|---:|---:|---:|")
    for item in comparison.get("ranking", []):
        lines.append(
            "| {mode} | {total} | {top5} | {latency} | {failed} |".format(
                mode=item["mode"],
                total=_fmt_float(item.get("weighted_proxy_score")),
                top5=_fmt_percent(item.get("expected_evidence_retrieval_top5_rate")),
                latency="-" if item.get("extractive_latency_p50_ms") is None else f"{item['extractive_latency_p50_ms']} ms",
                failed="-" if item.get("failed_cases") is None else item["failed_cases"],
            )
        )
    lines.append("")
    lines.append("Generated-answer metrics remain secondary until local model latency is characterized.")
    return "\n".join(lines) + "\n"


def _fmt_float(value: Any) -> str:
    return "-" if value is None else f"{float(value):.3f}"


def _fmt_percent(value: Any) -> str:
    return "-" if value is None else f"{float(value) * 100:.1f}%"


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run EMU Advisor evaluation metrics.")
    sub = parser.add_subparsers(dest="cmd", required=True)
    run = sub.add_parser("run")
    run.add_argument("--cases", type=Path, required=True)
    run.add_argument("--chunks", type=Path, required=True)
    run.add_argument("--out", type=Path, required=True)
    run.add_argument("--mode", choices=sorted(MODE_PRESETS), default="balanced")
    run.add_argument("--all-modes", action="store_true")
    run.add_argument("--include-generation", action="store_true")
    run.add_argument("--ollama-model", default="qwen3:8b")
    run.add_argument("--ollama-base-url", default="http://localhost:11434")
    run.add_argument("--ollama-timeout-s", type=float, default=90.0)
    return parser


def main(argv: Optional[List[str]] = None) -> int:
    args = build_parser().parse_args(argv)
    if args.cmd == "run":
        def generator_factory():
            return OllamaGenerator(model=args.ollama_model, base_url=args.ollama_base_url, timeout_s=args.ollama_timeout_s)

        if args.all_modes:
            comparison = run_all_modes(
                cases_path=args.cases,
                chunks_path=args.chunks,
                out_dir=args.out,
                include_generation=args.include_generation,
                generator_factory=generator_factory if args.include_generation else None,
            )
            print(json.dumps(comparison, ensure_ascii=False, indent=2, sort_keys=True))
            return 0
        generator = generator_factory() if args.include_generation else None
        summary = run_evaluation(
            cases_path=args.cases,
            chunks_path=args.chunks,
            out_dir=args.out,
            mode=args.mode,
            include_generation=args.include_generation,
            generator=generator,
        )
        print(json.dumps(summary, ensure_ascii=False, indent=2, sort_keys=True))
        return 0
    raise ValueError(args.cmd)


if __name__ == "__main__":
    raise SystemExit(main())
