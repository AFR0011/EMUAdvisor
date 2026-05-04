"""Hybrid lexical+dense retrieval over canonical chunks."""

from __future__ import annotations

import math
from collections import Counter, defaultdict
from dataclasses import dataclass
from typing import Any, Dict, Iterable, List, Mapping, Optional

from .embeddings import HashEmbeddingModel
from .modes import ModePreset, get_mode
from .routing import RouteDecision, filter_chunks_for_route, route_query
from .store import LocalVectorStore
from .text import tokenize


@dataclass(frozen=True)
class RetrievalResult:
    chunk: Dict[str, Any]
    score: float
    dense_score: float
    lexical_score: float
    rank_dense: Optional[int]
    rank_lexical: Optional[int]

    def as_hit(self) -> Dict[str, Any]:
        hit = dict(self.chunk)
        hit["score"] = self.score
        hit["dense_score"] = self.dense_score
        hit["lexical_score"] = self.lexical_score
        hit["rank_dense"] = self.rank_dense
        hit["rank_lexical"] = self.rank_lexical
        return hit


class HybridRetriever:
    def __init__(self, chunks: Iterable[Mapping[str, Any]], *, embedder: Optional[HashEmbeddingModel] = None) -> None:
        self.embedder = embedder or HashEmbeddingModel()
        self.chunks = [dict(chunk) for chunk in chunks]
        self.store = LocalVectorStore(dimensions=self.embedder.dimensions)
        self.store.upsert_chunks(self.chunks, self.embedder)

    def retrieve(
        self,
        query: str,
        *,
        mode: str | ModePreset = "balanced",
        route: Optional[RouteDecision] = None,
        top_k: int = 8,
        explicit_cross_corpus: bool = False,
    ) -> List[Dict[str, Any]]:
        preset = get_mode(mode) if isinstance(mode, str) else mode
        route = route or route_query(query, explicit_cross_corpus=explicit_cross_corpus)
        if not route.in_scope:
            return []

        filters = {"corpus": route.corpora}
        query_vector = self.embedder.encode_one(query)
        dense_hits = self.store.query(query_vector, limit=preset.retrieval_fanout, filters=filters)
        routed_chunks = filter_chunks_for_route(self.chunks, route)
        lexical_hits = _lexical_rank(query, routed_chunks, limit=preset.retrieval_fanout)

        fused = _fuse(dense_hits, lexical_hits, preset=preset)
        if preset.rerank_enabled:
            fused = _rerank(query, fused, limit=preset.rerank_candidates or len(fused))
        return [result.as_hit() for result in fused[:top_k]]


def _lexical_rank(query: str, chunks: List[Dict[str, Any]], *, limit: int) -> List[Dict[str, Any]]:
    query_terms = tokenize(query)
    query_counts = Counter(query_terms)
    doc_freq: Counter[str] = Counter()
    chunk_tokens: Dict[str, List[str]] = {}
    for chunk in chunks:
        tokens = tokenize(str(chunk.get("chunk_text", "")))
        chunk_tokens[str(chunk["chunk_id"])] = tokens
        doc_freq.update(set(tokens))

    total_docs = max(len(chunks), 1)
    results: List[Dict[str, Any]] = []
    for chunk in chunks:
        tokens = chunk_tokens[str(chunk["chunk_id"])]
        counts = Counter(tokens)
        score = 0.0
        for term, query_count in query_counts.items():
            tf = counts.get(term, 0)
            if not tf:
                continue
            idf = math.log((1 + total_docs) / (1 + doc_freq[term])) + 1.0
            score += query_count * (1 + math.log(tf)) * idf
        if score > 0:
            hit = dict(chunk)
            hit["_lexical_score"] = score
            results.append(hit)
    results.sort(key=lambda item: item["_lexical_score"], reverse=True)
    return results[:limit]


def _fuse(
    dense_hits: List[Dict[str, Any]],
    lexical_hits: List[Dict[str, Any]],
    *,
    preset: ModePreset,
    rrf_k: int = 60,
) -> List[RetrievalResult]:
    by_id: Dict[str, Dict[str, Any]] = {}
    dense_ranks: Dict[str, int] = {}
    lexical_ranks: Dict[str, int] = {}
    dense_scores: Dict[str, float] = defaultdict(float)
    lexical_scores: Dict[str, float] = defaultdict(float)

    for rank, hit in enumerate(dense_hits, start=1):
        chunk_id = str(hit["chunk_id"])
        by_id[chunk_id] = hit
        dense_ranks[chunk_id] = rank
        dense_scores[chunk_id] = float(hit.get("_dense_score", 0.0))
    for rank, hit in enumerate(lexical_hits, start=1):
        chunk_id = str(hit["chunk_id"])
        by_id.setdefault(chunk_id, hit)
        lexical_ranks[chunk_id] = rank
        lexical_scores[chunk_id] = float(hit.get("_lexical_score", 0.0))

    results: List[RetrievalResult] = []
    for chunk_id, chunk in by_id.items():
        score = 0.0
        if chunk_id in dense_ranks:
            score += preset.dense_weight / (rrf_k + dense_ranks[chunk_id])
        if chunk_id in lexical_ranks:
            score += preset.lexical_weight / (rrf_k + lexical_ranks[chunk_id])
        results.append(
            RetrievalResult(
                chunk=chunk,
                score=score,
                dense_score=dense_scores[chunk_id],
                lexical_score=lexical_scores[chunk_id],
                rank_dense=dense_ranks.get(chunk_id),
                rank_lexical=lexical_ranks.get(chunk_id),
            )
        )
    results.sort(key=lambda item: item.score, reverse=True)
    return results


def _rerank(query: str, results: List[RetrievalResult], *, limit: int) -> List[RetrievalResult]:
    query_terms = set(tokenize(query))
    reranked = []
    for result in results:
        text_terms = set(tokenize(str(result.chunk.get("chunk_text", ""))))
        overlap = len(query_terms & text_terms)
        boosted_score = result.score + overlap * 0.01
        reranked.append(
            RetrievalResult(
                chunk=result.chunk,
                score=boosted_score,
                dense_score=result.dense_score,
                lexical_score=result.lexical_score,
                rank_dense=result.rank_dense,
                rank_lexical=result.rank_lexical,
            )
        )
    reranked.sort(key=lambda item: item.score, reverse=True)
    return reranked[:limit] + reranked[limit:]
