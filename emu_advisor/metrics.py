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

from .answer import build_extractive_answer
from .corpus import load_chunks_jsonl
from .evaluation import EvaluationCase, evaluate_hits, load_cases
from .generation import OllamaGenerator
from .retrieval import HybridRetriever
from .routing import asks_cross_corpus, route_query


TARGETS = {
    "retrieval_top5": 0.85,
    "rejection_accuracy": 0.90,
    "citation_coverage": 1.0,
    "extractive_latency_p50_ms": 1000,
}


@dataclass(frozen=True)
class CaseResult:
    case_id: str
    category: str
    expected_behavior: str
    actual_mode: str
    retrieval_rank: Optional[int]
    retrieval_top1: bool
    retrieval_top3: bool
    retrieval_top5: bool
    response_correct: bool
    rejection_correct: bool
    clarification_correct: bool
    citation_covered: bool
    route_ms: int
    retrieve_ms: int
    extractive_ms: int
    generation_ms: Optional[int]
    first_token_ms: Optional[int]
    generated_error: Optional[str]
    answer: str
    citations: str
    notes: str


def run_evaluation(
    *,
    cases_path: Path,
    chunks_path: Path,
    out_dir: Path,
    include_generation: bool = False,
    generator: Optional[OllamaGenerator] = None,
) -> Dict[str, Any]:
    cases = load_cases(cases_path)
    _validate_case_mix(cases)
    chunks = load_chunks_jsonl(chunks_path)
    retriever = HybridRetriever(chunks)
    generator = generator or OllamaGenerator()
    results: List[CaseResult] = []

    for case in cases:
        route_start = time.perf_counter()
        route = route_query(case.question, explicit_cross_corpus=asks_cross_corpus(case.question))
        route_ms = _elapsed_ms(route_start)

        retrieve_start = time.perf_counter()
        hits = retriever.retrieve(case.question, route=route, top_k=8)
        retrieve_ms = _elapsed_ms(retrieve_start)

        extractive_start = time.perf_counter()
        answer = build_extractive_answer(case.question, hits)
        extractive_ms = _elapsed_ms(extractive_start)

        metric = evaluate_hits(case, hits)
        citations = [citation.as_dict() for citation in answer.citations]
        generated_ms: Optional[int] = None
        first_token_ms: Optional[int] = None
        generated_error: Optional[str] = None
        if include_generation and answer.mode in {"answer", "answer_uncertain"}:
            generated = generator.generate(case.question, answer.decision.supported_hits)
            generated_ms = generated.latency_ms
            first_token_ms = generated.first_token_ms
            generated_error = generated.error

        response_correct = _response_correct(case, answer.text, metric.top5)
        rejection_correct = case.expected_behavior == "refuse" and answer.mode == "refuse"
        clarification_correct = case.expected_behavior == "clarify" and answer.mode == "clarify"
        citation_covered = bool(citations) if case.expected_behavior in {"answer", "conflict"} else True
        results.append(
            CaseResult(
                case_id=case.case_id,
                category=case.category,
                expected_behavior=case.expected_behavior,
                actual_mode=answer.mode,
                retrieval_rank=metric.hit_rank,
                retrieval_top1=metric.top1,
                retrieval_top3=metric.top3,
                retrieval_top5=metric.top5,
                response_correct=response_correct,
                rejection_correct=rejection_correct,
                clarification_correct=clarification_correct,
                citation_covered=citation_covered,
                route_ms=route_ms,
                retrieve_ms=retrieve_ms,
                extractive_ms=extractive_ms,
                generation_ms=generated_ms,
                first_token_ms=first_token_ms,
                generated_error=generated_error,
                answer=answer.text,
                citations=json.dumps(citations, ensure_ascii=False),
                notes=case.notes,
            )
        )

    summary = summarize_case_results(results)
    summary["generated_model"] = getattr(generator, "model", None) if include_generation else None
    write_reports(results, summary, out_dir=out_dir)
    return summary


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
        "available": True,
        "cases": len(results),
        "answerable_cases": len(answerable),
        "rejection_cases": len(refusals),
        "clarification_cases": len(clarifications),
        "retrieval_top1": _rate(answerable, lambda result: result.retrieval_top1),
        "retrieval_top3": _rate(answerable, lambda result: result.retrieval_top3),
        "retrieval_top5": _rate(answerable, lambda result: result.retrieval_top5),
        "response_accuracy": _rate(answerable, lambda result: result.response_correct),
        "rejection_accuracy": _rate(refusals, lambda result: result.rejection_correct),
        "clarification_accuracy": _rate(clarifications, lambda result: result.clarification_correct),
        "citation_coverage": _rate(answerable, lambda result: result.citation_covered),
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
        "targets": TARGETS,
    }
    summary["presentable"] = (
        summary["retrieval_top5"] is not None
        and summary["retrieval_top5"] >= TARGETS["retrieval_top5"]
        and summary["rejection_accuracy"] is not None
        and summary["rejection_accuracy"] >= TARGETS["rejection_accuracy"]
        and summary["citation_coverage"] == TARGETS["citation_coverage"]
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


def _response_correct(case: EvaluationCase, answer_text: str, top5: bool) -> bool:
    if case.expected_behavior == "conflict":
        return "conflict" in answer_text.casefold() or top5
    if case.expected_behavior != "answer":
        return False
    if not top5:
        return False
    if case.expected_answer_keywords:
        lowered = answer_text.casefold()
        return any(keyword.casefold() in lowered for keyword in case.expected_answer_keywords)
    return True


def _validate_case_mix(cases: List[EvaluationCase]) -> None:
    if not any(case.expected_behavior == "answer" for case in cases):
        raise ValueError("evaluation set must include at least one answerable case")
    if not any(case.expected_behavior == "refuse" for case in cases):
        raise ValueError("evaluation set must include at least one refusal case")


def _rate(results: List[CaseResult], predicate) -> Optional[float]:
    if not results:
        return None
    return sum(1 for result in results if predicate(result)) / len(results)


def _percentile(values: List[Optional[int]], quantile: float) -> Optional[int]:
    clean = sorted(int(value) for value in values if value is not None)
    if not clean:
        return None
    index = min(len(clean) - 1, int(round((len(clean) - 1) * quantile)))
    return clean[index]


def _elapsed_ms(started: float) -> int:
    return int((time.perf_counter() - started) * 1000)


def _markdown_summary(summary: Dict[str, Any]) -> str:
    lines = ["# EMU Advisor Metrics", "", f"Presentable: `{summary['presentable']}`", ""]
    for key in [
        "cases",
        "retrieval_top5",
        "response_accuracy",
        "rejection_accuracy",
        "clarification_accuracy",
        "citation_coverage",
        "extractive_latency_p50_ms",
        "extractive_latency_p95_ms",
        "generated_latency_p50_ms",
        "generated_first_token_p50_ms",
        "generated_cases_attempted",
        "generated_cases_completed",
        "generated_error_cases",
        "generated_available",
        "generated_model",
    ]:
        lines.append(f"- `{key}`: {summary.get(key)}")
    lines.append("")
    lines.append("Targets:")
    for key, value in TARGETS.items():
        lines.append(f"- `{key}`: {value}")
    return "\n".join(lines) + "\n"


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run EMU Advisor evaluation metrics.")
    sub = parser.add_subparsers(dest="cmd", required=True)
    run = sub.add_parser("run")
    run.add_argument("--cases", type=Path, required=True)
    run.add_argument("--chunks", type=Path, required=True)
    run.add_argument("--out", type=Path, required=True)
    run.add_argument("--include-generation", action="store_true")
    run.add_argument("--ollama-model", default="qwen3:8b")
    run.add_argument("--ollama-base-url", default="http://localhost:11434")
    run.add_argument("--ollama-timeout-s", type=float, default=90.0)
    return parser


def main(argv: Optional[List[str]] = None) -> int:
    args = build_parser().parse_args(argv)
    if args.cmd == "run":
        generator = (
            OllamaGenerator(model=args.ollama_model, base_url=args.ollama_base_url, timeout_s=args.ollama_timeout_s)
            if args.include_generation
            else None
        )
        summary = run_evaluation(
            cases_path=args.cases,
            chunks_path=args.chunks,
            out_dir=args.out,
            include_generation=args.include_generation,
            generator=generator,
        )
        print(json.dumps(summary, ensure_ascii=False, indent=2, sort_keys=True))
        return 0
    raise ValueError(args.cmd)


if __name__ == "__main__":
    raise SystemExit(main())
