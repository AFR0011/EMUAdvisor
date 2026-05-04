"""Language, corpus, and V1 scope routing."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, List, Optional
from urllib.parse import urlparse


TURKISH_MARKERS = set("çğıöşüÇĞİÖŞÜ")
OUT_OF_SCOPE_TERMS = (
    "event",
    "events",
    "campus events",
    "activity center",
    "student advising",
    "staff advising",
    "email",
    "schedule a meeting",
    "send email",
    "etkinlik",
    "etkinlikler",
    "e-posta",
    "eposta",
    "bölüm program",
)


@dataclass(frozen=True)
class RouteDecision:
    query_language: str
    corpora: List[str]
    cross_corpus: bool
    in_scope: bool
    reason: str


def detect_query_language(query: str) -> str:
    if any(char in TURKISH_MARKERS for char in query):
        return "tr"
    lowered = query.lower()
    if any(token in lowered for token in (" nedir", " yonetmelik", "yönetmelik", " madde", " öğrenci", "ogrenci", "öğretim", "ogretim")):
        return "tr"
    return "en"


def route_query(query: str, *, explicit_cross_corpus: bool = False) -> RouteDecision:
    lowered = query.lower()
    if any(term in lowered for term in OUT_OF_SCOPE_TERMS):
        return RouteDecision(
            query_language=detect_query_language(query),
            corpora=[],
            cross_corpus=False,
            in_scope=False,
            reason="query appears outside V1 regulations scope",
        )

    language = detect_query_language(query)
    if explicit_cross_corpus or asks_cross_corpus(query):
        return RouteDecision(
            query_language=language,
            corpora=["regulations_en", "regulations_tr"],
            cross_corpus=True,
            in_scope=True,
            reason="explicit cross-corpus search requested",
        )

    corpus = "regulations_tr" if language == "tr" else "regulations_en"
    return RouteDecision(
        query_language=language,
        corpora=[corpus],
        cross_corpus=False,
        in_scope=True,
        reason="matched query language corpus",
    )


def asks_cross_corpus(query: str) -> bool:
    lowered = query.lower()
    return any(
        marker in lowered
        for marker in (
            "compare",
            "both english and turkish",
            "english and turkish",
            "turkish and english",
            "karşılaştır",
            "ingilizce ve türkçe",
            "türkçe ve ingilizce",
        )
    )


def source_in_v1_scope(source_url: str, *, source_type: str = "html") -> bool:
    parsed = urlparse(source_url)
    if parsed.hostname != "mevzuat.emu.edu.tr":
        return False
    if source_type == "pdf":
        return parsed.path.lower().endswith(".pdf")
    return source_type == "html"


def filter_chunks_for_route(chunks: Iterable[dict], route: RouteDecision) -> List[dict]:
    if not route.in_scope:
        return []
    allowed = set(route.corpora)
    return [chunk for chunk in chunks if chunk.get("corpus") in allowed]
