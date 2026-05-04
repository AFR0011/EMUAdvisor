"""Qdrant-compatible local vector store.

This is not a replacement for Qdrant in production. It mirrors the collection,
payload, vector, and filter shape needed by the app so ingestion/retrieval tests
can run locally while `qdrant_client` is unavailable.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Iterable, List, Mapping, Optional

from .embeddings import HashEmbeddingModel, cosine_similarity
from .schema import validate_chunk


@dataclass(frozen=True)
class StoredPoint:
    point_id: str
    vector: List[float]
    payload: Dict[str, Any]


class LocalVectorStore:
    def __init__(self, *, collection_name: str = "emu_regulations", dimensions: int = 256) -> None:
        self.collection_name = collection_name
        self.dimensions = dimensions
        self.points: Dict[str, StoredPoint] = {}
        self.payload_indexes = {
            "language",
            "corpus",
            "access_tier",
            "source_type",
            "source_url",
            "version_hash",
            "last_crawled_at",
            "section_path",
            "article_number",
            "page_number",
        }

    def recreate_collection(self) -> None:
        self.points.clear()

    def upsert_chunks(self, chunks: Iterable[Mapping[str, Any]], embedder: HashEmbeddingModel) -> int:
        count = 0
        for record in chunks:
            validate_chunk(record)
            vector = embedder.encode_one(str(record["chunk_text"]))
            if len(vector) != self.dimensions:
                raise ValueError("embedder dimensions do not match collection dimensions")
            payload = dict(record)
            point_id = str(record["chunk_id"])
            self.points[point_id] = StoredPoint(point_id=point_id, vector=vector, payload=payload)
            count += 1
        return count

    def query(
        self,
        query_vector: List[float],
        *,
        limit: int,
        filters: Optional[Mapping[str, Any]] = None,
    ) -> List[Dict[str, Any]]:
        filters = filters or {}
        results: List[Dict[str, Any]] = []
        for point in self.points.values():
            if not _matches_filters(point.payload, filters):
                continue
            score = cosine_similarity(query_vector, point.vector)
            hit = dict(point.payload)
            hit["_dense_score"] = score
            results.append(hit)
        results.sort(key=lambda item: item["_dense_score"], reverse=True)
        return results[:limit]

    def filter(self, *, filters: Mapping[str, Any]) -> List[Dict[str, Any]]:
        return [dict(point.payload) for point in self.points.values() if _matches_filters(point.payload, filters)]


def _matches_filters(payload: Mapping[str, Any], filters: Mapping[str, Any]) -> bool:
    for key, expected in filters.items():
        actual = payload.get(key)
        if isinstance(expected, (list, tuple, set)):
            if actual not in expected:
                return False
        elif actual != expected:
            return False
    return True
