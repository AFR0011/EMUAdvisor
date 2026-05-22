from __future__ import annotations

import unittest
from unittest.mock import patch

from emu_advisor.query_understanding import parse_query_understanding, understand_query
from emu_advisor.routing import route_query


class _FakeResponse:
    def __init__(self, text: str) -> None:
        self._text = text

    def raise_for_status(self) -> None:
        return None

    def json(self) -> dict[str, str]:
        return {"response": self._text}


class QueryUnderstandingTests(unittest.TestCase):
    def test_valid_llm_json_rewrite_is_used(self) -> None:
        response = _FakeResponse(
            '{"input_language":"tr","retrieval_language":"tr",'
            '"standalone_query":"Burs basvurusu nasil yapilir?",'
            '"is_follow_up":true,"confidence":"high"}'
        )

        with patch("httpx.post", return_value=response):
            result = understand_query(
                "buna nasil basvururum",
                [{"role": "user", "text": "What scholarships are available?"}],
                mode="llm",
                model="qwen3:8b",
                timeout_s=0.1,
            )

        self.assertEqual(result.method, "llm")
        self.assertEqual(result.retrieval_language, "tr")
        self.assertTrue(result.is_follow_up)
        self.assertEqual(result.standalone_query, "Burs basvurusu nasil yapilir?")

    def test_invalid_llm_json_falls_back_deterministically(self) -> None:
        with patch("httpx.post", return_value=_FakeResponse("not json")):
            result = understand_query("not itirazi nasil yapilir", mode="llm", timeout_s=0.1)

        self.assertEqual(result.method, "deterministic_fallback")
        self.assertEqual(result.retrieval_language, "tr")
        self.assertEqual(result.standalone_query, "not itirazi nasil yapilir")
        self.assertIsNotNone(result.error)

    def test_llm_timeout_falls_back_deterministically(self) -> None:
        with patch("httpx.post", side_effect=TimeoutError("timed out")):
            result = understand_query("basvuru belgeleri nelerdir", mode="llm", timeout_s=0.1)

        self.assertEqual(result.method, "deterministic_fallback")
        self.assertEqual(result.retrieval_language, "tr")
        self.assertEqual(route_query(result.standalone_query, language_hint=result.retrieval_language).corpora, ["regulations_tr"])

    def test_low_confidence_valid_output_still_routes_safely(self) -> None:
        result = parse_query_understanding(
            '{"input_language":"tr","retrieval_language":"tr",'
            '"standalone_query":"Basvuru belgeleri nelerdir?",'
            '"is_follow_up":false,"confidence":"low"}',
            original_query="basvuru belgeleri nelerdir",
        )

        self.assertEqual(result.confidence, "low")
        self.assertEqual(route_query(result.standalone_query, language_hint=result.retrieval_language).corpora, ["regulations_tr"])


if __name__ == "__main__":
    unittest.main()
