"""Language, corpus, and V1 scope routing."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, List, Optional
from urllib.parse import urlparse

from .text import normalize_text, tokenize


TURKISH_MARKERS = set("\u00e7\u011f\u0131\u00f6\u015f\u00fc\u00c7\u011e\u0130\u00d6\u015e\u00dc")
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
    "bolum program",
)

TURKISH_SIGNAL_TERMS = {
    "akademik",
    "arastirma",
    "asgari",
    "basari",
    "basvuru",
    "belge",
    "belgeler",
    "burs",
    "ceza",
    "celiskili",
    "dau",
    "devam",
    "devamsizlik",
    "dilekce",
    "gorev",
    "gorevli",
    "gorevlisi",
    "gorevlileri",
    "harc",
    "hangi",
    "itiraz",
    "itirazi",
    "kac",
    "kampus",
    "karsilastir",
    "kural",
    "kurallar",
    "kurallari",
    "lisansustu",
    "maas",
    "madde",
    "maddesi",
    "mali",
    "mevzuat",
    "muafiyet",
    "nasil",
    "ne",
    "neden",
    "neler",
    "nelerdir",
    "nerede",
    "nedir",
    "ogrenci",
    "ogretim",
    "oran",
    "oranlar",
    "oranlari",
    "personel",
    "sinav",
    "sorulmali",
    "seref",
    "sure",
    "turkce",
    "ucret",
    "uygulama",
    "yandal",
    "yararlanabilir",
    "yardim",
    "yapilir",
    "yollar",
    "yonetmelik",
    "yuksek",
    "yuzde",
}

ENGLISH_SIGNAL_TERMS = {
    "about",
    "allowed",
    "answer",
    "appeal",
    "apply",
    "attendance",
    "campus",
    "course",
    "deadline",
    "documents",
    "eligibility",
    "english",
    "exam",
    "grade",
    "high",
    "honour",
    "how",
    "maximum",
    "penalty",
    "regulation",
    "requirement",
    "rule",
    "rules",
    "scholarship",
    "student",
    "turkish",
    "what",
    "when",
    "where",
    "which",
    "who",
    "why",
}

TURKISH_SIGNAL_PHRASES = (
    "anlama gelir",
    "ne zaman",
    "nasil yapilir",
    "nasil basvur",
    "hangi ofis",
    "buna nasil",
    "bunun icin",
)


@dataclass(frozen=True)
class RouteDecision:
    query_language: str
    corpora: List[str]
    in_scope: bool
    reason: str


def detect_query_language(query: str, *, language_hint: Optional[str] = None) -> str:
    if language_hint in {"en", "tr"}:
        return language_hint

    if any(char in TURKISH_MARKERS for char in query):
        return "tr"
    lowered = normalize_text(query)
    tokens = tokenize(query)
    token_set = set(tokens)

    turkish_score = 0
    english_score = 0
    turkish_score += sum(1 for token in token_set if token in TURKISH_SIGNAL_TERMS)
    english_score += sum(1 for token in token_set if token in ENGLISH_SIGNAL_TERMS)
    turkish_score += sum(2 for phrase in TURKISH_SIGNAL_PHRASES if phrase in lowered)

    # Turkish legal/regulatory questions commonly contain one or more Turkish
    # suffixes after ASCII transliteration; keep this conservative to avoid
    # classifying English phrases such as "not allowed" as Turkish.
    if any(token.endswith(("lari", "leri", "dir", "mali", "meli")) and len(token) > 5 for token in token_set):
        turkish_score += 1

    if turkish_score >= 2 and turkish_score >= english_score:
        return "tr"
    return "en"


def route_query(query: str, *, language_hint: Optional[str] = None) -> RouteDecision:
    lowered = normalize_text(query)
    language = detect_query_language(query, language_hint=language_hint)
    if any(term in lowered for term in OUT_OF_SCOPE_TERMS):
        return RouteDecision(
            query_language=language,
            corpora=[],
            in_scope=False,
            reason="query appears outside V1 regulations scope",
        )

    corpus = "regulations_tr" if language == "tr" else "regulations_en"
    return RouteDecision(
        query_language=language,
        corpora=[corpus],
        in_scope=True,
        reason="matched query language corpus",
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
