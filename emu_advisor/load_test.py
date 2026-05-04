"""Lightweight active-session load simulation."""

from __future__ import annotations

import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from statistics import mean
from typing import Iterable, List

from .answer import build_extractive_answer
from .retrieval import HybridRetriever


@dataclass(frozen=True)
class LoadResult:
    active_sessions: int
    completed: int
    max_latency_ms: int
    avg_latency_ms: float
    extractive_fallbacks: int


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
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = [executor.submit(run, question) for question in expanded]
        for future in as_completed(futures):
            latencies.append(future.result())

    return LoadResult(
        active_sessions=active_sessions,
        completed=len(latencies),
        max_latency_ms=max(latencies),
        avg_latency_ms=mean(latencies),
        extractive_fallbacks=len(latencies),
    )
