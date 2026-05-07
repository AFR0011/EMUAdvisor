"""Text normalization utilities shared by retrieval components."""

from __future__ import annotations

import re
import unicodedata
from typing import List


TOKEN_RE = re.compile(r"\w+", re.UNICODE)
TURKISH_TRANSLITERATION = str.maketrans(
    {
        "\u00e7": "c",
        "\u00c7": "c",
        "\u011f": "g",
        "\u011e": "g",
        "\u0131": "i",
        "I": "i",
        "\u0130": "i",
        "\u00f6": "o",
        "\u00d6": "o",
        "\u015f": "s",
        "\u015e": "s",
        "\u00fc": "u",
        "\u00dc": "u",
    }
)
STOPWORDS = {
    "a",
    "an",
    "and",
    "are",
    "can",
    "do",
    "does",
    "for",
    "from",
    "how",
    "in",
    "is",
    "may",
    "of",
    "or",
    "the",
    "to",
    "what",
    "when",
    "which",
    "who",
    "with",
    "student",
    "students",
    "bir",
    "ve",
    "veya",
    "ile",
    "icin",
    "hangi",
    "nasil",
    "kac",
    "ne",
    "mi",
    "mu",
    "ayni",
    "anda",
    "fazla",
    "ogrenci",
}


def normalize_text(text: str) -> str:
    normalized = unicodedata.normalize("NFKC", text).translate(TURKISH_TRANSLITERATION).casefold()
    decomposed = unicodedata.normalize("NFKD", normalized)
    return "".join(char for char in decomposed if not unicodedata.combining(char))


def tokenize(text: str) -> List[str]:
    return TOKEN_RE.findall(normalize_text(text))


def signal_terms(text: str) -> List[str]:
    return [token for token in tokenize(text) if len(token) >= 2 and token not in STOPWORDS]
