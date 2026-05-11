"""Local benchmark helpers for embeddings and generated-answer mode."""

from __future__ import annotations

import argparse
import json
import time
from pathlib import Path
from statistics import median
from typing import Any, Dict, List, Optional

from .answer import build_extractive_answer
from .corpus import load_chunks_jsonl
from .embeddings import create_embedding_model
from .evaluation import evaluate_hits, load_cases, summarize_metrics
from .generation import DEFAULT_OLLAMA_LLM, OllamaGenerator
from .retrieval import HybridRetriever
from .routing import route_query


def benchmark_embedding(*, cases_path: Path, chunks_path: Path, embedding: str, limit: Optional[int] = None) -> Dict[str, Any]:
    started = time.perf_counter()
    chunks = load_chunks_jsonl(chunks_path)
    embedder = create_embedding_model(embedding)
    build_ms = _elapsed_ms(started)
    retriever = HybridRetriever(chunks, embedder=embedder)
    cases = load_cases(cases_path)
    if limit:
        cases = cases[:limit]
    query_latencies = []
    metrics = []
    for case in cases:
        query_started = time.perf_counter()
        hits = retriever.retrieve(case.question, route=route_query(case.question), mode="balanced", top_k=8)
        query_latencies.append(_elapsed_ms(query_started))
        metrics.append(evaluate_hits(case, hits))
    summary = summarize_metrics(metrics)
    return {
        "kind": "embedding",
        "embedding": embedder.metadata.model_name,
        "dimensions": embedder.dimensions,
        "cases": len(cases),
        "chunks": len(chunks),
        "build_ms": build_ms,
        "retrieval": summary,
        "query_latency_p50_ms": _percentile(query_latencies, 0.50),
        "query_latency_p95_ms": _percentile(query_latencies, 0.95),
    }


def benchmark_generation(
    *,
    cases_path: Path,
    chunks_path: Path,
    model: str = DEFAULT_OLLAMA_LLM,
    timeout_s: float = 30,
    limit: int = 5,
) -> Dict[str, Any]:
    chunks = load_chunks_jsonl(chunks_path)
    retriever = HybridRetriever(chunks, embedder=create_embedding_model("hash"))
    generator = OllamaGenerator(model=model, timeout_s=timeout_s)
    status = generator.status(timeout_s=min(timeout_s, 10), smoke=False)
    cases = [case for case in load_cases(cases_path) if case.expected_behavior == "answer"][:limit]
    results = []
    for case in cases:
        hits = retriever.retrieve(case.question, route=route_query(case.question), mode="balanced", top_k=8)
        extractive = build_extractive_answer(case.question, hits)
        if not status.get("model_available"):
            results.append(
                {
                    "case_id": case.case_id,
                    "generated": False,
                    "error": status.get("error") or f"model not available: {model}",
                    "extractive_latency_only": True,
                }
            )
            continue
        generated = generator.generate(case.question, extractive.decision.supported_hits)
        results.append(
            {
                "case_id": case.case_id,
                "generated": bool(generated.text),
                "latency_ms": generated.latency_ms,
                "first_token_ms": generated.first_token_ms,
                "error": generated.error,
            }
        )
    successful = [result for result in results if result.get("generated")]
    return {
        "kind": "generation",
        "model": model,
        "model_status": status,
        "cases": len(cases),
        "successful_generations": len(successful),
        "latency_p50_ms": _percentile([int(result["latency_ms"]) for result in successful if result.get("latency_ms") is not None], 0.50),
        "first_token_p50_ms": _percentile([int(result["first_token_ms"]) for result in successful if result.get("first_token_ms") is not None], 0.50),
        "default_recommendation": "extractive_first" if len(successful) < len(cases) else "generated_opt_in_pending_human_review",
        "results": results,
    }


def _elapsed_ms(started: float) -> int:
    return int((time.perf_counter() - started) * 1000)


def _percentile(values: List[int], ratio: float) -> Optional[int]:
    if not values:
        return None
    ordered = sorted(values)
    if ratio == 0.50:
        return int(median(ordered))
    index = min(len(ordered) - 1, max(0, int(round((len(ordered) - 1) * ratio))))
    return int(ordered[index])


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run local EMU Advisor benchmark probes.")
    sub = parser.add_subparsers(dest="cmd", required=True)

    embedding = sub.add_parser("embedding")
    embedding.add_argument("--cases", type=Path, required=True)
    embedding.add_argument("--chunks", type=Path, required=True)
    embedding.add_argument("--embedding", default="hash")
    embedding.add_argument("--limit", type=int, default=None)

    generation = sub.add_parser("generation")
    generation.add_argument("--cases", type=Path, required=True)
    generation.add_argument("--chunks", type=Path, required=True)
    generation.add_argument("--model", default=DEFAULT_OLLAMA_LLM)
    generation.add_argument("--timeout-s", type=float, default=30)
    generation.add_argument("--limit", type=int, default=5)
    return parser


def main(argv: Optional[List[str]] = None) -> int:
    args = build_parser().parse_args(argv)
    if args.cmd == "embedding":
        result = benchmark_embedding(cases_path=args.cases, chunks_path=args.chunks, embedding=args.embedding, limit=args.limit)
    elif args.cmd == "generation":
        result = benchmark_generation(
            cases_path=args.cases,
            chunks_path=args.chunks,
            model=args.model,
            timeout_s=args.timeout_s,
            limit=args.limit,
        )
    else:
        raise ValueError(args.cmd)
    print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
