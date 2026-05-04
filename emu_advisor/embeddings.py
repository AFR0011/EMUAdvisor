"""Local embedding baselines for EMU Advisor.

The production target may use BGE-M3, multilingual-E5, gte-multilingual, or a
Qwen embedding model. This module provides a deterministic local multilingual
hashing baseline so tests and offline development do not depend on external
model downloads or APIs.
"""

from __future__ import annotations

import hashlib
import math
from dataclasses import dataclass
from typing import Iterable, List

from .text import tokenize


DEFAULT_EMBEDDING_MODEL = "local-hash-multilingual-v1"
PRODUCTION_CANDIDATES = (
    "BAAI/bge-m3",
    "intfloat/multilingual-e5-base",
    "Alibaba-NLP/gte-multilingual-base",
    "Qwen/Qwen3-Embedding-0.6B",
)


@dataclass(frozen=True)
class EmbeddingMetadata:
    model_name: str
    dimensions: int
    local_only: bool
    notes: str


class HashEmbeddingModel:
    """Deterministic multilingual bag-of-token hashing embedder."""

    def __init__(self, *, dimensions: int = 256, model_name: str = DEFAULT_EMBEDDING_MODEL) -> None:
        if dimensions <= 0:
            raise ValueError("dimensions must be positive")
        self.dimensions = dimensions
        self.model_name = model_name

    @property
    def metadata(self) -> EmbeddingMetadata:
        return EmbeddingMetadata(
            model_name=self.model_name,
            dimensions=self.dimensions,
            local_only=True,
            notes="Deterministic local baseline; replace with configured multilingual model for quality runs.",
        )

    def encode_one(self, text: str) -> List[float]:
        vector = [0.0] * self.dimensions
        for token in tokenize(text):
            digest = hashlib.sha256(token.encode("utf-8")).digest()
            bucket = int.from_bytes(digest[:4], "big") % self.dimensions
            sign = 1.0 if digest[4] % 2 == 0 else -1.0
            vector[bucket] += sign
        norm = math.sqrt(sum(value * value for value in vector))
        if norm == 0:
            return vector
        return [value / norm for value in vector]

    def encode(self, texts: Iterable[str]) -> List[List[float]]:
        return [self.encode_one(text) for text in texts]


def cosine_similarity(left: List[float], right: List[float]) -> float:
    if len(left) != len(right):
        raise ValueError("vectors must have the same dimensions")
    return sum(a * b for a, b in zip(left, right))
