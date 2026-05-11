"""Hybrid lexical+dense retrieval over canonical chunks."""

from __future__ import annotations

import math
from collections import Counter, defaultdict
from dataclasses import dataclass
from typing import Any, Dict, Iterable, List, Mapping, Optional
from urllib.parse import urlparse

from .embeddings import HashEmbeddingModel
from .modes import ModePreset, get_mode
from .routing import RouteDecision, filter_chunks_for_route, route_query
from .store import LocalVectorStore, QdrantVectorStore
from .text import normalize_text, signal_terms, tokenize


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
    def __init__(
        self,
        chunks: Iterable[Mapping[str, Any]],
        *,
        embedder: Optional[HashEmbeddingModel] = None,
        vector_backend: str = "local",
        qdrant_url: str = "http://localhost:6333",
        qdrant_path: Optional[str] = None,
        qdrant_collection: str = "emu_regulations",
        require_qdrant: bool = False,
    ) -> None:
        self.embedder = embedder or HashEmbeddingModel()
        self.chunks = [dict(chunk) for chunk in chunks]
        self.vector_backend = vector_backend
        self.backend_warning: Optional[str] = None
        if vector_backend == "qdrant":
            try:
                self.store = QdrantVectorStore(
                    collection_name=qdrant_collection,
                    dimensions=self.embedder.dimensions,
                    url=qdrant_url,
                    path=qdrant_path,
                )
                self.store.upsert_chunks(self.chunks, self.embedder)
            except Exception as exc:
                if require_qdrant:
                    raise RuntimeError(
                        f"Qdrant backend is required but unavailable for collection {qdrant_collection}: {exc}"
                    ) from exc
                self.store = LocalVectorStore(dimensions=self.embedder.dimensions)
                self.vector_backend = "local"
                self.backend_warning = f"Qdrant unavailable, using local fallback: {exc}"
                self.store.upsert_chunks(self.chunks, self.embedder)
        elif vector_backend == "local":
            self.store = LocalVectorStore(dimensions=self.embedder.dimensions)
            self.store.upsert_chunks(self.chunks, self.embedder)
        else:
            raise ValueError(f"unknown vector backend: {vector_backend}")

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
        if route.cross_corpus and len(route.corpora) > 1:
            fused = _diversify_cross_corpus(fused, route.corpora, top_k=top_k)
        return [result.as_hit() for result in fused[:top_k]]


def _lexical_rank(query: str, chunks: List[Dict[str, Any]], *, limit: int) -> List[Dict[str, Any]]:
    query_terms = _expanded_query_terms(query)
    query_counts = Counter(query_terms)
    doc_freq: Counter[str] = Counter()
    chunk_tokens: Dict[str, List[str]] = {}
    for chunk in chunks:
        tokens = tokenize(_searchable_text(chunk))
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
        score *= _quality_multiplier(chunk)
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
    query_terms = set(_expanded_query_terms(query))
    reranked = []
    for result in results:
        text_terms = set(tokenize(_searchable_text(result.chunk)))
        overlap = len(query_terms & text_terms)
        boosted_score = (
            result.score
            + overlap * 0.01
            + _topic_boost(query, result.chunk)
            + _structured_evidence_boost(query, result.chunk)
        ) * _quality_multiplier(result.chunk)
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


def _diversify_cross_corpus(results: List[RetrievalResult], corpora: List[str], *, top_k: int) -> List[RetrievalResult]:
    selected: List[RetrievalResult] = []
    selected_ids = set()
    for corpus in corpora:
        for result in results:
            if result.chunk.get("corpus") != corpus:
                continue
            chunk_id = str(result.chunk.get("chunk_id", ""))
            selected.append(result)
            selected_ids.add(chunk_id)
            break
    for result in results:
        chunk_id = str(result.chunk.get("chunk_id", ""))
        if chunk_id in selected_ids:
            continue
        selected.append(result)
        selected_ids.add(chunk_id)
        if len(selected) >= top_k:
            break
    return selected[:top_k] + [result for result in results if str(result.chunk.get("chunk_id", "")) not in selected_ids]


def _is_index_or_toc_chunk(chunk: Mapping[str, Any]) -> bool:
    path = urlparse(str(chunk.get("source_url", ""))).path.strip("/").casefold()
    leaf = path.rsplit("/", 1)[-1]
    title = str(chunk.get("source_title", "")).strip().casefold()
    return leaf in {"content.htm", "content-en.htm"} or title in {"content", "content en"}


def _searchable_text(chunk: Mapping[str, Any]) -> str:
    return " ".join(
        str(chunk.get(field, ""))
        for field in ("chunk_text", "source_title", "section_path", "article_number", "source_url")
    )


def _is_form_or_attachment_chunk(chunk: Mapping[str, Any]) -> bool:
    parsed = urlparse(str(chunk.get("source_url", "")))
    path = parsed.path.casefold()
    title = normalize_text(str(chunk.get("source_title", "")).strip())
    return "/forms/" in path or title.endswith(" formu") or title.endswith(" form") or " formu " in title


def _quality_multiplier(chunk: Mapping[str, Any]) -> float:
    multiplier = 1.0
    if _is_index_or_toc_chunk(chunk):
        multiplier *= 0.25
    if _is_form_or_attachment_chunk(chunk):
        multiplier *= 0.2
    if _looks_like_placeholder_form_row(chunk):
        multiplier *= 0.35
    return multiplier


def _topic_boost(query: str, chunk: Mapping[str, Any]) -> float:
    query_terms = set(_expanded_query_terms(query))
    source_url = normalize_text(str(chunk.get("source_url", "")))
    searchable = normalize_text(_searchable_text(chunk))
    query_text = normalize_text(query)
    boost = 0.0

    academic_staff_terms = {"academic", "staff"} <= query_terms or {"akademik", "personel"} <= query_terms
    pay_or_scale_terms = query_terms & {"salary", "salaries", "scale", "scales", "position", "positions", "maaş", "maas", "barem", "kadro"}
    if academic_staff_terms and pay_or_scale_terms and (
        "6-1_staffingemploymentacademicstaff" in source_url or "tuzukler/6-1_akdperskadrocal" in source_url
    ):
        boost += 0.08

    if "ng" in query_terms and (
        "5-1-0-regulation-education_examination_success" in source_url or "tuzukler/5-1_ogrtsnvbasari" in source_url
    ):
        boost += 0.06

    research_assistant_terms = (
        {"research", "assistant"} <= query_terms
        or {"arastirma", "gorevlisi"} <= query_terms
        or {"arastirma", "gorevli"} <= query_terms
    )
    appointment_or_rules_terms = query_terms & {
        "appointment",
        "appointing",
        "rules",
        "rule",
        "kural",
        "kurallar",
        "kurallarini",
        "gorev",
        "gorevlendirme",
    }
    if research_assistant_terms and (
        appointment_or_rules_terms or "research_assistant_by-law" in source_url or "arastirmagorevlisigorevburs" in source_url
    ):
        if "5-4-3-rules-research_assistant_by-law" in source_url or "5-4-3-yonetmelik-arastirmagorevlisigorevburs" in source_url:
            boost += 0.20

    if query_terms & {"scholarship", "scholarships", "burs", "indirim", "indirimden"} and (
        "scholarship" in searchable or "burs" in searchable or "indirim" in searchable
    ):
        boost += 0.05

    if query_terms & {"burs", "scholarship", "scholarships"} and (
        "5-1-2-yonetmelik-burs-indirim-uygulama" in source_url
        or "5-1-2-rules-scholarship" in source_url
        or "burs indirim" in searchable
    ):
        boost += 0.08

    if query_terms & {"oran", "oranlar", "oranlarda", "yuzde", "percent", "percentage", "rate", "rates"} and (
        "5-1-2-yonetmelik-burs-indirim-uygulama" in source_url
        or "5-1-2-rules-scholarship" in source_url
    ):
        boost += 0.08

    if query_terms & {"withdraw", "withdrawal", "withdrawn", "withdrawing", "withdraws"}:
        if "5-1-5-rules-course_registration" in source_url or "5-1-5-rules-course-registration" in source_url:
            boost += 0.10
        if "course withdrawal" in searchable or "withdraw from two registered courses" in searchable:
            boost += 0.12

    if {"maximum", "number", "registered", "course"} <= query_terms and "course withdrawal" in searchable:
        boost += 0.06

    if "burs" in query_text and "burs" in searchable and "basarili sporcu bursu" in searchable:
        boost += 0.05

    return boost


def _structured_evidence_boost(query: str, chunk: Mapping[str, Any]) -> float:
    metadata = chunk.get("metadata") if isinstance(chunk.get("metadata"), Mapping) else {}
    evidence_kind = str(metadata.get("evidence_kind") or "")
    if evidence_kind not in {"table_row", "table_summary", "derived_fact"}:
        return 0.0
    query_terms = set(_expanded_query_terms(query))
    numeric_or_table_terms = {
        "salary",
        "salaries",
        "range",
        "ranges",
        "scale",
        "scales",
        "step",
        "steps",
        "professor",
        "assistant",
        "maaş",
        "maas",
        "barem",
        "basamak",
    }
    if not (query_terms & numeric_or_table_terms):
        return 0.0
    if evidence_kind == "derived_fact":
        return 0.18
    if evidence_kind == "table_row":
        return 0.12
    return 0.04


def _expanded_query_terms(query: str) -> List[str]:
    terms = signal_terms(query) or tokenize(query)
    expanded: List[str] = []
    for term in terms:
        expanded.append(term)
        expanded.extend(_term_variants(term))
    return expanded


def _term_variants(term: str) -> List[str]:
    variants: List[str] = []
    suffix_variants = (
        ("larda", 5),
        ("lerde", 5),
        ("lari", 4),
        ("leri", 4),
        ("lar", 3),
        ("ler", 3),
        ("s", 1),
    )
    for suffix, length in suffix_variants:
        if term.endswith(suffix) and len(term) > length + 2:
            variants.append(term[:-length])
    variants.extend(
        {
            "withdraw": ["withdrawal", "withdrawn", "withdrawing", "withdraws"],
            "withdrawal": ["withdraw", "withdrawn", "withdrawing"],
            "withdrawn": ["withdraw", "withdrawal"],
            "registered": ["registration", "register", "registering"],
            "registration": ["registered", "register", "registering"],
            "course": ["courses"],
            "courses": ["course"],
            "burs": ["burslar", "bursu", "bursun"],
            "burslar": ["burs"],
            "oran": ["oranlar", "oranlarda", "yuzde"],
            "oranlarda": ["oran", "oranlar", "yuzde"],
            "yuzde": ["percent", "percentage", "oran"],
            "lisansustu": ["yuksek", "doktora"],
            "gorevliligi": ["gorevlisi", "gorevli"],
            "gorevlisi": ["gorevliligi", "gorevli"],
        }.get(term, [])
    )
    return variants


def _looks_like_placeholder_form_row(chunk: Mapping[str, Any]) -> bool:
    text = str(chunk.get("chunk_text", ""))
    normalized = normalize_text(text)
    if "yukumluluk belgesi" in normalized:
        return True
    return text.count(".") >= 20 and ("adi-soyadi" in normalized or "imza" in normalized)
