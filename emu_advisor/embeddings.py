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
from typing import Any, Iterable, List, Optional

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


class OllamaEmbeddingModel:
    """Local Ollama embedding client with no external API dependency."""

    def __init__(
        self,
        *,
        model_name: str = "qwen3-embedding:4b",
        base_url: str = "http://localhost:11434",
        timeout_s: float = 60.0,
        dimensions: Optional[int] = None,
    ) -> None:
        self.model_name = model_name
        self.base_url = base_url.rstrip("/")
        self.timeout_s = timeout_s
        self._dimensions = dimensions

    @property
    def dimensions(self) -> int:
        if self._dimensions is None:
            self._dimensions = len(self.encode_one("dimension probe"))
        return self._dimensions

    @property
    def metadata(self) -> EmbeddingMetadata:
        return EmbeddingMetadata(
            model_name=self.model_name,
            dimensions=self.dimensions,
            local_only=True,
            notes="Local Ollama embedding model.",
        )

    def encode_one(self, text: str) -> List[float]:
        return self.encode([text])[0]

    def encode(self, texts: Iterable[str]) -> List[List[float]]:
        import httpx

        inputs = list(texts)
        if not inputs:
            return []

        payload = {"model": self.model_name, "input": inputs}
        try:
            response = httpx.post(f"{self.base_url}/api/embed", json=payload, timeout=self.timeout_s)
            response.raise_for_status()
            data = response.json()
            vectors = data.get("embeddings")
            if isinstance(vectors, list) and vectors:
                out = [_coerce_vector(vector) for vector in vectors]
                self._dimensions = len(out[0])
                return out
        except Exception:
            if len(inputs) != 1:
                return [self.encode_one(text) for text in inputs]

        # Compatibility fallback for older Ollama embeddings endpoint.
        out: List[List[float]] = []
        for text in inputs:
            response = httpx.post(
                f"{self.base_url}/api/embeddings",
                json={"model": self.model_name, "prompt": text},
                timeout=self.timeout_s,
            )
            response.raise_for_status()
            vector = _coerce_vector(response.json().get("embedding"))
            self._dimensions = len(vector)
            out.append(vector)
        return out


def create_embedding_model(
    choice: str = "auto",
    *,
    allow_fallback: bool = True,
    hash_dimensions: int = 256,
) -> HashEmbeddingModel | OllamaEmbeddingModel:
    """Create the requested embedding model.

    `auto` prefers local Ollama `qwen3-embedding:4b` and falls back to the
    deterministic hash baseline when Ollama is unavailable.
    """

    if choice == "hash":
        return HashEmbeddingModel(dimensions=hash_dimensions)
    if choice not in {"auto", "ollama"}:
        raise ValueError(f"unknown embedding choice: {choice}")

    model = OllamaEmbeddingModel()
    try:
        _ = model.dimensions
        return model
    except Exception:
        if allow_fallback:
            return HashEmbeddingModel(dimensions=hash_dimensions)
        raise


def cosine_similarity(left: List[float], right: List[float]) -> float:
    if len(left) != len(right):
        raise ValueError("vectors must have the same dimensions")
    return sum(a * b for a, b in zip(left, right))


def _coerce_vector(value: Any) -> List[float]:
    if not isinstance(value, list) or not value:
        raise ValueError("Ollama response did not include an embedding vector")
    return [float(item) for item in value]
