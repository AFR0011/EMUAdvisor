"""Lightweight active-session load simulation."""

from __future__ import annotations

import argparse
import json
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from pathlib import Path
from statistics import mean, median
from typing import Iterable, List, Optional

from .answer import build_extractive_answer
from .corpus import load_chunks_jsonl
from .embeddings import create_embedding_model
from .retrieval import HybridRetriever


@dataclass(frozen=True)
class LoadResult:
    active_sessions: int
    completed: int
    max_latency_ms: int
    avg_latency_ms: float
    p50_latency_ms: int
    p95_latency_ms: int
    errors: int
    extractive_fallbacks: int

    def as_dict(self) -> dict:
        return {
            "active_sessions": self.active_sessions,
            "completed": self.completed,
            "errors": self.errors,
            "max_latency_ms": self.max_latency_ms,
            "avg_latency_ms": self.avg_latency_ms,
            "p50_latency_ms": self.p50_latency_ms,
            "p95_latency_ms": self.p95_latency_ms,
            "extractive_fallbacks": self.extractive_fallbacks,
            "error_rate": self.errors / max(self.active_sessions, 1),
        }


def simulate_active_sessions(
    retriever: HybridRetriever,
    questions: Iterable[str],
    *,
    active_sessions: int = 50,
    max_workers: int = 4,
) -> LoadResult:
    question_list = list(questions)
    if not question_list:
        raise ValueError("questions cannot be empty")
    expanded = [question_list[idx % len(question_list)] for idx in range(active_sessions)]

    def run(question: str) -> int:
        started = time.perf_counter()
        hits = retriever.retrieve(question, top_k=5)
        build_extractive_answer(question, hits)
        return int((time.perf_counter() - started) * 1000)

    latencies: List[int] = []
    errors = 0
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = [executor.submit(run, question) for question in expanded]
        for future in as_completed(futures):
            try:
                latencies.append(future.result())
            except Exception:
                errors += 1

    return LoadResult(
        active_sessions=active_sessions,
        completed=len(latencies),
        max_latency_ms=max(latencies) if latencies else 0,
        avg_latency_ms=mean(latencies) if latencies else 0.0,
        p50_latency_ms=_percentile(latencies, 0.50) or 0,
        p95_latency_ms=_percentile(latencies, 0.95) or 0,
        errors=errors,
        extractive_fallbacks=len(latencies),
    )


def _percentile(values: List[int], ratio: float) -> Optional[int]:
    if not values:
        return None
    ordered = sorted(values)
    if ratio == 0.50:
        return int(median(ordered))
    index = min(len(ordered) - 1, max(0, int(round((len(ordered) - 1) * ratio))))
    return int(ordered[index])


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Simulate active EMU Advisor extractive sessions.")
    parser.add_argument("--chunks", type=Path, required=True)
    parser.add_argument("--question", action="append", default=[])
    parser.add_argument("--active-sessions", type=int, default=50)
    parser.add_argument("--max-workers", type=int, default=4)
    parser.add_argument("--embedding", default="hash")
    return parser


def main(argv: Optional[List[str]] = None) -> int:
    args = build_parser().parse_args(argv)
    chunks = load_chunks_jsonl(args.chunks)
    retriever = HybridRetriever(chunks, embedder=create_embedding_model(args.embedding))
    questions = args.question or ["What is the attendance requirement?", "Yuksek seref nedir?"]
    result = simulate_active_sessions(
        retriever,
        questions,
        active_sessions=args.active_sessions,
        max_workers=args.max_workers,
    )
    print(json.dumps(result.as_dict(), ensure_ascii=False, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
