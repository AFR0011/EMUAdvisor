"""Text normalization utilities shared by retrieval components."""

from __future__ import annotations

import re
import unicodedata
from typing import List


TOKEN_RE = re.compile(r"\w+", re.UNICODE)


def normalize_text(text: str) -> str:
    normalized = unicodedata.normalize("NFKC", text)
    return normalized.casefold()


def tokenize(text: str) -> List[str]:
    return TOKEN_RE.findall(normalize_text(text))
