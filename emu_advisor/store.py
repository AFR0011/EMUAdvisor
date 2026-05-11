"""Qdrant-compatible local vector store.

This is not a replacement for Qdrant in production. It mirrors the collection,
payload, vector, and filter shape needed by the app so ingestion/retrieval tests
can run locally while `qdrant_client` is unavailable.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Iterable, List, Mapping, Optional
from uuid import NAMESPACE_URL, uuid5

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

    def health(self) -> Dict[str, Any]:
        return {
            "backend": "local",
            "collection": self.collection_name,
            "available": True,
            "points": len(self.points),
            "dimensions": self.dimensions,
        }


def _matches_filters(payload: Mapping[str, Any], filters: Mapping[str, Any]) -> bool:
    for key, expected in filters.items():
        actual = payload.get(key)
        if isinstance(expected, (list, tuple, set)):
            if actual not in expected:
                return False
        elif actual != expected:
            return False
    return True


def _looks_like_real_qdrant_client(client: Any) -> bool:
    return any(hasattr(client, name) for name in ("query_points", "search", "scroll", "create_collection"))


class QdrantVectorStore:
    """Qdrant-backed vector store for production profile."""

    def __init__(
        self,
        *,
        collection_name: str = "emu_regulations",
        dimensions: int = 256,
        url: str = "http://localhost:6333",
        path: Optional[str] = None,
        client: Optional[Any] = None,
    ) -> None:
        self.collection_name = collection_name
        self.dimensions = dimensions
        self._owns_client = client is None
        if client is not None:
            self.client = client
            if _looks_like_real_qdrant_client(client):
                try:
                    from qdrant_client import models
                except ImportError:
                    models = None  # type: ignore[assignment]
                self.models = models
            else:
                self.models = None
        else:
            try:
                from qdrant_client import QdrantClient, models
            except ImportError as exc:
                raise RuntimeError("qdrant-client is required for Qdrant backend") from exc
            if path:
                self.client = QdrantClient(path=path)
            else:
                self.client = QdrantClient(url=url)
            self.models = models

    def recreate_collection(self) -> None:
        if self.models is None or not hasattr(self.client, "create_collection"):
            self.client.recreate_collection(self.collection_name, self.dimensions)
            return
        if hasattr(self.client, "collection_exists") and self.client.collection_exists(self.collection_name):
            self.client.delete_collection(collection_name=self.collection_name)
        self.client.create_collection(
            collection_name=self.collection_name,
            vectors_config=self.models.VectorParams(size=self.dimensions, distance=self.models.Distance.COSINE),
        )

    def ensure_collection(self) -> None:
        if self.models is None or not hasattr(self.client, "create_collection"):
            return
        if hasattr(self.client, "collection_exists") and self.client.collection_exists(self.collection_name):
            return
        self.client.create_collection(
            collection_name=self.collection_name,
            vectors_config=self.models.VectorParams(size=self.dimensions, distance=self.models.Distance.COSINE),
        )

    def upsert_chunks(self, chunks: Iterable[Mapping[str, Any]], embedder: HashEmbeddingModel) -> int:
        records = []
        for record in chunks:
            validate_chunk(record)
            vector = embedder.encode_one(str(record["chunk_text"]))
            if len(vector) != self.dimensions:
                raise ValueError("embedder dimensions do not match collection dimensions")
            point_id = str(uuid5(NAMESPACE_URL, str(record["chunk_id"])))
            payload = dict(record)
            if self.models is None:
                records.append({"id": point_id, "vector": vector, "payload": payload})
            else:
                records.append(self.models.PointStruct(id=point_id, vector=vector, payload=payload))
        if records:
            self.ensure_collection()
            self.client.upsert(collection_name=self.collection_name, points=records)
        return len(records)

    def query(
        self,
        query_vector: List[float],
        *,
        limit: int,
        filters: Optional[Mapping[str, Any]] = None,
    ) -> List[Dict[str, Any]]:
        if self.models is None:
            hits = self.client.query(self.collection_name, query_vector, limit=limit, filters=filters or {})
        elif hasattr(self.client, "query_points"):
            response = self.client.query_points(
                collection_name=self.collection_name,
                query=query_vector,
                query_filter=_qdrant_filter(self.models, filters or {}),
                limit=limit,
                with_payload=True,
            )
            hits = list(getattr(response, "points", response))
        else:
            hits = self.client.search(
                collection_name=self.collection_name,
                query_vector=query_vector,
                query_filter=_qdrant_filter(self.models, filters or {}),
                limit=limit,
                with_payload=True,
            )
        results: List[Dict[str, Any]] = []
        for hit in hits:
            payload = _hit_payload(hit)
            payload["_dense_score"] = _hit_score(hit)
            results.append(payload)
        return results

    def filter(self, *, filters: Mapping[str, Any]) -> List[Dict[str, Any]]:
        if self.models is None:
            return self.client.filter(self.collection_name, filters=filters)
        points, _next_page = self.client.scroll(
            collection_name=self.collection_name,
            scroll_filter=_qdrant_filter(self.models, filters),
            with_payload=True,
            limit=10000,
        )
        return [dict(point.payload or {}) for point in points]

    def health(self) -> Dict[str, Any]:
        try:
            if self.models is None:
                if hasattr(self.client, "health"):
                    return dict(self.client.health(self.collection_name))
                return {"backend": "qdrant", "collection": self.collection_name, "available": True}
            exists = True
            points = None
            if hasattr(self.client, "collection_exists"):
                exists = bool(self.client.collection_exists(self.collection_name))
            if exists and hasattr(self.client, "get_collection"):
                info = self.client.get_collection(collection_name=self.collection_name)
                points = getattr(info, "points_count", None)
            return {
                "backend": "qdrant",
                "collection": self.collection_name,
                "available": bool(exists),
                "points": points,
                "dimensions": self.dimensions,
            }
        except Exception as exc:
            return {
                "backend": "qdrant",
                "collection": self.collection_name,
                "available": False,
                "points": None,
                "dimensions": self.dimensions,
                "error": str(exc),
            }

    def close(self) -> None:
        if self._owns_client and hasattr(self.client, "close"):
            self.client.close()


def _hit_payload(hit: Any) -> Dict[str, Any]:
    payload = getattr(hit, "payload", None)
    if payload is None and isinstance(hit, Mapping):
        payload = hit.get("payload", {})
    return dict(payload or {})


def _hit_score(hit: Any) -> float:
    score = getattr(hit, "score", None)
    if score is None and isinstance(hit, Mapping):
        score = hit.get("score", 0.0)
    return float(score or 0.0)


def _qdrant_filter(models: Any, filters: Mapping[str, Any]) -> Any:
    if not filters:
        return None
    conditions = []
    for key, expected in filters.items():
        if isinstance(expected, (list, tuple, set)):
            match = models.MatchAny(any=list(expected))
        else:
            match = models.MatchValue(value=expected)
        conditions.append(models.FieldCondition(key=key, match=match))
    return models.Filter(must=conditions)
