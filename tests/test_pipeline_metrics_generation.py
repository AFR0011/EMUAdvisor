from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from emu_advisor.corpus import load_chunks_jsonl
from emu_advisor.generation import GenerationResult, OllamaGenerator
from emu_advisor.metrics import run_evaluation
from emu_advisor.pipeline import _decode_html, build_corpus, discover_links, is_allowed_crawl_url, normalize_url


class PipelineTests(unittest.TestCase):
    def test_url_policy_and_pdf_discovery(self) -> None:
        html = """
        <a href="https://mevzuat.emu.edu.tr/content/en/rule.htm?utm_source=x#frag">Rule</a>
        <a href="https://mevzuat.emu.edu.tr/content/en/rule.pdf">PDF</a>
        <a href="https://events.emu.edu.tr/event.htm">Event</a>
        """

        links = discover_links(html, "https://mevzuat.emu.edu.tr/content.htm", include_pdfs=True)

        self.assertIn("https://mevzuat.emu.edu.tr/content/en/rule.htm", links)
        self.assertIn("https://mevzuat.emu.edu.tr/content/en/rule.pdf", links)
        self.assertFalse(any("events.emu.edu.tr" in link for link in links))
        self.assertTrue(is_allowed_crawl_url("https://mevzuat.emu.edu.tr/content.htm"))
        self.assertFalse(is_allowed_crawl_url("https://catalog.emu.edu.tr/course.htm"))
        self.assertEqual(
            normalize_url("https://mevzuat.emu.edu.tr/a.htm?utm_source=x&x=1#top"),
            "https://mevzuat.emu.edu.tr/a.htm?x=1",
        )

    def test_html_decode_handles_turkish_legacy_charset(self) -> None:
        payload = "Öğrenci Disiplin Yönetmeliği".encode("windows-1254")

        decoded = _decode_html(payload, "text/html; charset=windows-1254")

        self.assertIn("Öğrenci", decoded)
        self.assertIn("Yönetmeliği", decoded)

    def test_fixture_pipeline_builds_canonical_chunks_without_network(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            fixture = root / "fixture.htm"
            fixture.write_text(
                """
                <html><head><title>Fixture Regulation</title></head>
                <body><h1>Article 1 Attendance</h1>
                <p>Students must meet the attendance requirement.</p></body></html>
                """,
                encoding="utf-8",
            )
            out = root / "out"

            result = build_corpus(
                seeds=[fixture.as_uri()],
                out_dir=out,
                max_pages=3,
                include_pdfs=False,
                delay_s=0,
                allow_file=True,
            )
            chunks = load_chunks_jsonl(out / "chunks.jsonl")

            self.assertEqual(result.errors, 0)
            self.assertGreaterEqual(result.chunk_count, 1)
            self.assertEqual(chunks[0]["source_url"], "https://mevzuat.emu.edu.tr/content/fixture/fixture.htm")
            self.assertEqual(chunks[0]["language"], "en")
            self.assertTrue((out / "manifest.json").exists())
            self.assertTrue((out.parent / "active_snapshot.txt").exists())

    def test_fixture_pipeline_uses_content_language_when_url_is_ambiguous(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            fixture = root / "ambiguous.htm"
            fixture.write_text(
                """
                <html><head><title>Öğrenci Yönetmeliği</title></head>
                <body><h1>Madde 1 Amaç</h1>
                <p>Bu yönetmelik öğrenci kayıt kurallarını açıklar.</p></body></html>
                """,
                encoding="utf-8",
            )
            out = root / "out"

            build_corpus(
                seeds=[fixture.as_uri()],
                out_dir=out,
                max_pages=3,
                include_pdfs=False,
                delay_s=0,
                allow_file=True,
            )
            chunks = load_chunks_jsonl(out / "chunks.jsonl")

            self.assertEqual(chunks[0]["language"], "tr")
            self.assertEqual(chunks[0]["corpus"], "regulations_tr")


class MetricsTests(unittest.TestCase):
    def test_metrics_runner_writes_dashboard_and_review_artifacts(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            chunks = root / "chunks.jsonl"
            chunks.write_text(
                json.dumps(
                    {
                        "document_id": "en:html:attendance",
                        "chunk_id": "en-attendance:c1",
                        "parent_document_id": None,
                        "source_type": "html",
                        "source_url": "https://mevzuat.emu.edu.tr/content/en/attendance.htm",
                        "source_title": "Attendance",
                        "language": "en",
                        "corpus": "regulations_en",
                        "access_tier": "public",
                        "effective_date": None,
                        "last_crawled_at": "2026-05-04T08:00:00Z",
                        "version_hash": "hash",
                        "section_path": "Article 1",
                        "article_number": "1",
                        "page_number": None,
                        "chunk_text": "Students must meet the attendance requirement.",
                        "metadata": {},
                    }
                )
                + "\n",
                encoding="utf-8",
            )
            cases = root / "cases.jsonl"
            cases.write_text(
                "\n".join(
                    [
                        json.dumps(
                            {
                                "case_id": "A1",
                                "question": "attendance requirement",
                                "language": "en",
                                "expected_behavior": "answer",
                                "expected_corpus": "regulations_en",
                                "expected_document_id": "en:html:attendance",
                                "expected_chunk_id": None,
                                "expected_source_url": None,
                                "expected_answer_keywords": ["attendance"],
                                "category": "direct_rule_lookup",
                                "is_correct": None,
                                "citation_ok": None,
                                "notes": "",
                            }
                        ),
                        json.dumps(
                            {
                                "case_id": "R1",
                                "question": "Tell me about campus events",
                                "language": "en",
                                "expected_behavior": "refuse",
                                "expected_corpus": None,
                                "expected_document_id": None,
                                "expected_chunk_id": None,
                                "expected_source_url": None,
                                "expected_answer_keywords": [],
                                "category": "out_of_scope",
                                "is_correct": None,
                                "citation_ok": None,
                                "notes": "",
                            }
                        ),
                    ]
                )
                + "\n",
                encoding="utf-8",
            )
            out = root / "metrics"

            summary = run_evaluation(cases_path=cases, chunks_path=chunks, out_dir=out)

            self.assertEqual(summary["cases"], 2)
            self.assertEqual(summary["retrieval_top5"], 1.0)
            self.assertTrue((out / "metrics.json").exists())
            self.assertTrue((out / "per_case.csv").exists())
            self.assertTrue((out / "human_review.csv").exists())
            self.assertTrue((out / "metrics.md").exists())

    def test_generated_metrics_mark_failed_local_model_unavailable(self) -> None:
        class FailingGenerator:
            def generate(self, _question, _hits):
                return GenerationResult(
                    text="",
                    model="qwen3:8b",
                    latency_ms=3,
                    first_token_ms=None,
                    error="model unavailable",
                )

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            chunks = root / "chunks.jsonl"
            chunks.write_text(
                json.dumps(
                    {
                        "document_id": "en:html:attendance",
                        "chunk_id": "en-attendance:c1",
                        "parent_document_id": None,
                        "source_type": "html",
                        "source_url": "https://mevzuat.emu.edu.tr/content/en/attendance.htm",
                        "source_title": "Attendance",
                        "language": "en",
                        "corpus": "regulations_en",
                        "access_tier": "public",
                        "effective_date": None,
                        "last_crawled_at": "2026-05-04T08:00:00Z",
                        "version_hash": "hash",
                        "section_path": "Article 1",
                        "article_number": "1",
                        "page_number": None,
                        "chunk_text": "Students must meet the attendance requirement.",
                        "metadata": {},
                    }
                )
                + "\n",
                encoding="utf-8",
            )
            cases = root / "cases.jsonl"
            cases.write_text(
                "\n".join(
                    [
                        json.dumps(
                            {
                                "case_id": "A1",
                                "question": "attendance requirement",
                                "language": "en",
                                "expected_behavior": "answer",
                                "expected_corpus": "regulations_en",
                                "expected_document_id": "en:html:attendance",
                                "expected_chunk_id": None,
                                "expected_source_url": None,
                                "expected_answer_keywords": ["attendance"],
                                "category": "direct_rule_lookup",
                                "is_correct": None,
                                "citation_ok": None,
                                "notes": "",
                            }
                        ),
                        json.dumps(
                            {
                                "case_id": "R1",
                                "question": "Tell me about campus events",
                                "language": "en",
                                "expected_behavior": "refuse",
                                "expected_corpus": None,
                                "expected_document_id": None,
                                "expected_chunk_id": None,
                                "expected_source_url": None,
                                "expected_answer_keywords": [],
                                "category": "out_of_scope",
                                "is_correct": None,
                                "citation_ok": None,
                                "notes": "",
                            }
                        ),
                    ]
                )
                + "\n",
                encoding="utf-8",
            )

            summary = run_evaluation(
                cases_path=cases,
                chunks_path=chunks,
                out_dir=root / "metrics",
                include_generation=True,
                generator=FailingGenerator(),
            )

            self.assertEqual(summary["generated_cases_attempted"], 1)
            self.assertEqual(summary["generated_cases_completed"], 0)
            self.assertEqual(summary["generated_error_cases"], 1)
            self.assertFalse(summary["generated_available"])
            self.assertIsNone(summary["generated_latency_p50_ms"])

    def test_metrics_rejects_mojibake_cases(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "bad.jsonl"
            path.write_text('{"case_id":"bad","question":"YÃ¼ksek","language":"tr","expected_behavior":"answer","category":"x"}\n', encoding="utf-8")
            with self.assertRaises(ValueError):
                run_evaluation(cases_path=path, chunks_path=path, out_dir=Path(tmp) / "out")


class GenerationTests(unittest.TestCase):
    def test_ollama_generation_failure_is_reported(self) -> None:
        result = OllamaGenerator(base_url="http://127.0.0.1:9", timeout_s=0.1).generate("question", [])

        self.assertEqual(result.text, "")
        self.assertIsNotNone(result.error)


if __name__ == "__main__":
    unittest.main()
