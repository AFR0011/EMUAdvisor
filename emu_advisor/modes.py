"""Executable operating mode presets."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict


@dataclass(frozen=True)
class ModePreset:
    name: str
    retrieval_fanout: int
    dense_weight: float
    lexical_weight: float
    rerank_enabled: bool
    rerank_candidates: int
    max_context_chunks: int
    generation_timeout_s: float
    local_llm_label: str


MODE_PRESETS: Dict[str, ModePreset] = {
    "cheap": ModePreset(
        name="cheap",
        retrieval_fanout=20,
        dense_weight=0.8,
        lexical_weight=1.2,
        rerank_enabled=False,
        rerank_candidates=0,
        max_context_chunks=4,
        generation_timeout_s=60.0,
        local_llm_label="small quantized local model or extractive fallback",
    ),
    "balanced": ModePreset(
        name="balanced",
        retrieval_fanout=50,
        dense_weight=1.0,
        lexical_weight=1.0,
        rerank_enabled=True,
        rerank_candidates=20,
        max_context_chunks=8,
        generation_timeout_s=30.0,
        local_llm_label="8B-14B local instruct model",
    ),
    "expensive": ModePreset(
        name="expensive",
        retrieval_fanout=100,
        dense_weight=1.2,
        lexical_weight=1.0,
        rerank_enabled=True,
        rerank_candidates=50,
        max_context_chunks=14,
        generation_timeout_s=15.0,
        local_llm_label="larger local model served with GPU runtime",
    ),
}


def get_mode(name: str) -> ModePreset:
    try:
        return MODE_PRESETS[name]
    except KeyError as exc:
        raise ValueError(f"unknown mode: {name}") from exc


def validate_modes() -> None:
    cheap = MODE_PRESETS["cheap"]
    balanced = MODE_PRESETS["balanced"]
    expensive = MODE_PRESETS["expensive"]
    if not (cheap.retrieval_fanout < balanced.retrieval_fanout < expensive.retrieval_fanout):
        raise ValueError("mode retrieval fanout must increase from cheap to expensive")
    if cheap.rerank_enabled:
        raise ValueError("cheap mode should not require reranking")
    if not balanced.rerank_enabled or not expensive.rerank_enabled:
        raise ValueError("balanced and expensive modes should enable reranking")
