"""Casual message detection and follow-up query expansion."""

from __future__ import annotations

import re


# English casual patterns
EN_GREETINGS = (
    "hi",
    "hello",
    "hey",
    "good morning",
    "good afternoon",
    "good evening",
    "how are you",
    "how're you",
    "what's up",
    "whats up",
    "greetings",
)

EN_THANKS = (
    "thank you",
    "thanks",
    "appreciate it",
    "much appreciated",
)

EN_FAREWELLS = (
    "goodbye",
    "bye",
    "see you",
    "take care",
    "have a good one",
    "see you later",
)

EN_GENERIC = (
    "who are you",
    "what are you",
    "introduce yourself",
    "help",
    "help me",
    "start over",
    "reset",
)

# Turkish equivalents
TR_GREETINGS = (
    "merhaba",
    "selam",
    "iyi gunler",
    "gunaydin",
    "iyi aksamlar",
    "naber",
    "nasilsin",
    "nasil gidiyor",
)

TR_THANKS = (
    "tesekkurler",
    "tesekkur ederim",
    "tekkur ederim",
    "cok tesekkurler",
    "cok tesekkur ederim",
    "tesekkur",
    "teşekkürler",
    "teşekkür ederim",
    "çok teşekkürler",
    "çok teşekkür ederim",
)

TR_FAREWELLS = (
    "gorusuruz",
    "görüşürüz",
    "hosca kal",
    "gidiyorum",
    "hoşca kal",
    "iyi gunler",
    "iyi aksamlar",
    "iyi calismalar",
)

TR_GENERIC = (
    "kimsin",
    "ne issin",
    "tanitim yap",
    "yardim",
    "yardim et",
    "baslat",
    "sifirla",
)

CASUAL_FILLER_WORDS = {
    "there",
    "friend",
    "assistant",
    "bot",
    "emu",
    "please",
    "pls",
    "again",
    "now",
    "today",
    "sir",
    "madam",
    "hocam",
}

FOLLOW_UP_REFERENCE_TERMS = {
    "it",
    "this",
    "that",
    "these",
    "those",
    "they",
    "them",
    "there",
    "same",
    "one",
    "ones",
    "above",
    "previous",
    "mentioned",
    "bunu",
    "buna",
    "bunun",
    "bu",
    "şu",
    "o",
    "bunlar",
    "onlar",
    "aynı",
    "önceki",
}

FOLLOW_UP_GENERIC_TERMS = {
    "apply",
    "application",
    "deadline",
    "deadlines",
    "documents",
    "documentation",
    "penalty",
    "penalties",
    "requirement",
    "requirements",
    "eligibility",
    "amount",
    "rate",
    "limit",
    "limits",
    "duration",
    "appeal",
    "başvuru",
    "belge",
    "belgeler",
    "ceza",
    "şart",
    "şartlar",
    "süre",
    "oran",
    "limit",
}


def _normalize(query: str) -> str:
    """Normalize query for matching."""
    query = query.lower().strip()
    # Remove punctuation but keep spaces
    query = re.sub(r"[^\w\sçğıöşüÇĞİÖŞÜ]", " ", query)
    # Collapse multiple spaces
    query = re.sub(r"\s+", " ", query)
    return query


def _matches_standalone_casual(
    normalized: str,
    phrases: tuple[str, ...],
    *,
    max_extra_words: int = 3,
) -> bool:
    """Match only standalone casual messages, not substrings inside real questions."""
    if not normalized:
        return False

    normalized_phrases = sorted((_normalize(item) for item in phrases), key=len, reverse=True)
    for phrase in normalized_phrases:
        if normalized == phrase:
            return True
        if normalized.startswith(f"{phrase} "):
            remaining = normalized[len(phrase):].strip().split()
            if (
                remaining
                and len(remaining) <= max_extra_words
                and all(word in CASUAL_FILLER_WORDS for word in remaining)
            ):
                return True
    return False


def is_casual_message(query: str) -> tuple[bool, str, str]:
    """
    Detect if query is a casual message (greeting, thanks, farewell, or generic).

    Returns:
        Tuple of (is_casual, category, response_text)
        - is_casual: True if the query is only a casual message
        - category: One of "greeting", "thanks", "farewell", "generic", or ""
        - response_text: Friendly response to return
    """
    normalized = _normalize(query)

    # Check English greetings
    if _matches_standalone_casual(normalized, EN_GREETINGS):
        return (
            True,
            "greeting",
            "Hello! I'm EMU Assistant, here to help you with Eastern Mediterranean University regulations. "
            "How can I assist you today?",
        )

    # Check Turkish greetings
    if _matches_standalone_casual(normalized, TR_GREETINGS):
        return (
            True,
            "greeting",
            "Merhaba! EMU Asistanıyım, Doğu Akdeniz Üniversitesi düzenlemeleri konusunda size yardımcı olmak için buradayım. "
            "Sana nasıl yardımcı olabilirim?",
        )

    # Check English thanks
    if _matches_standalone_casual(normalized, EN_THANKS):
        return (
            True,
            "thanks",
            "You're welcome! If you have any more questions about EMU regulations, feel free to ask.",
        )

    # Check Turkish thanks
    if _matches_standalone_casual(normalized, TR_THANKS):
        return (
            True,
            "thanks",
            "Rica ederim! EMU düzenlemeleri ile ilgili başka sorularınız varsa, lütfen sorun.",
        )

    # Check English farewells
    if _matches_standalone_casual(normalized, EN_FAREWELLS):
        return (
            True,
            "farewell",
            "Goodbye! Have a great day and feel free to return if you have more questions.",
        )

    # Check Turkish farewells
    if _matches_standalone_casual(normalized, TR_FAREWELLS):
        return (
            True,
            "farewell",
            "Görüşürüz! İyi günler dilerim; başka sorularınız olursa lütfen geri dönün.",
        )

    # Check English generics
    if _matches_standalone_casual(normalized, EN_GENERIC):
        return (
            True,
            "generic",
            "I'm EMU Assistant, a local-only RAG assistant for Eastern Mediterranean University regulations. "
            "I can answer questions from the official regulations database. What would you like to know?",
        )

    # Check Turkish generics
    if _matches_standalone_casual(normalized, TR_GENERIC):
        return (
            True,
            "generic",
            "Ben EMU Asistanıyım, Doğu Akdeniz Üniversitesi düzenlemeleri için yerel bir RAG asistanıyım. "
            "Resmi düzenleme veritabanından sorularınıza cevap verebilirim. Ne öğrenmek istiyorsunuz?",
        )

    return (False, "", "")


def is_follow_up(query: str) -> bool:
    """
    Detect if query is likely a follow-up to a previous conversation.

    This is intentionally conservative: it only marks questions as follow-ups when
    they contain reference words such as "this/that/it" or are short, contextless
    questions like "how do I apply?" after a previous topic exists.
    """
    normalized = _normalize(query)
    words = normalized.split()
    if not words:
        return False

    word_set = set(words)

    # Explicit references to prior context.
    if word_set & FOLLOW_UP_REFERENCE_TERMS:
        return True

    # Very short questions that usually need the previous topic.
    wh_words = {"why", "where", "when", "who", "what", "how", "which", "ne", "nasıl", "nasil", "nerede", "ne zaman", "kim", "hangi"}
    if words[0] in wh_words and len(words) <= 5:
        return True

    # Short procedural questions like "How do I apply?" or "What documents are needed?"
    if words[0] in wh_words and len(words) <= 8 and (word_set & FOLLOW_UP_GENERIC_TERMS):
        return True

    # Pattern-based detection
    follow_up_patterns = [
        r"^what about",
        r"^how about",
        r"^and what",
        r"^but what",
        r"^so what",
        r"^if what",
        r"^and how",
        r"^but how",
        r"^what if",
        r"^and if",
        r"^does that",
        r"^is that",
        r"^can that",
        r"^can i still",
        r"^what happens if",
        r"^te ne",
        r"^ve ne",
        r"^pe ne",
        r"^ama ne",
        r"^eğer ne",
        r"^ve ne",
    ]

    for pattern in follow_up_patterns:
        if re.match(pattern, normalized):
            return True

    return False


def expand_follow_up_query(query: str, last_topic: str) -> str:
    """
    Expand a follow-up query by appending the last topic's key terms.

    Example:
        query: "what about the penalty"
        last_topic: "attendance requirement"
        result: "what about the penalty attendance requirement"
    """
    normalized = _normalize(query)
    last_topic_norm = _normalize(last_topic)

    if not last_topic_norm:
        return query

    # If the query is very short, append the last topic.
    words = normalized.split()
    if len(words) <= 8:
        if normalized not in last_topic_norm and last_topic_norm not in normalized:
            return f"{query} Context from previous question: {last_topic}"

    # For longer follow-ups, append compact key terms from the previous topic.
    topic_words = last_topic.split()
    key_terms = " ".join(topic_words[:8])

    if key_terms and _normalize(key_terms) not in normalized:
        return f"{query} Context from previous question: {key_terms}"

    return query
