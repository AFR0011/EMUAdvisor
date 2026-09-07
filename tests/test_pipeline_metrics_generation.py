from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

from emu_advisor.corpus import load_chunks_jsonl
from emu_advisor.evaluation import load_cases, validate_case_set
from emu_advisor.generation import GenerationResult, OllamaGenerator
from emu_advisor.metrics import run_all_modes, run_evaluation
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
            self.assertEqual(chunks[0]["source_url"], "fixture:///fixture.htm")
            self.assertTrue(chunks[0]["metadata"]["fixture"])
            self.assertFalse(chunks[0]["metadata"]["official_source"])
            self.assertNotIn(str(root), json.dumps(chunks[0]))
            self.assertEqual(chunks[0]["language"], "en")
            self.assertTrue((out / "manifest.json").exists())
            self.assertTrue((out.parent / "active_snapshot.txt").exists())
            self.assertNotIn(str(root), (out / "manifest.json").read_text(encoding="utf-8"))
            self.assertNotIn(str(root), (out / "crawl_pages.jsonl").read_text(encoding="utf-8"))
            self.assertNotIn(str(root), (out.parent / "active_snapshot.txt").read_text(encoding="utf-8"))

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
    def test_metrics_runner_writes_dashboard_review_and_failure_analysis_artifacts(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            chunks, cases = _write_metrics_fixture(root)
            out = root / "metrics"

            summary = run_evaluation(cases_path=cases, chunks_path=chunks, out_dir=out)

            self.assertEqual(summary["cases"], 60)
            self.assertEqual(summary["expected_evidence_retrieval_top5_rate"], 1.0)
            self.assertEqual(summary["mode"], "balanced")
            self.assertIn("mode_preset", summary)
            self.assertEqual(summary["schema_version"], "emu-advisor-automated-proxy/v2")
            self.assertIn("weighted_proxy_score", summary)
            self.assertNotIn("response_accuracy", summary)
            self.assertNotIn("groundedness", summary)
            self.assertIn("failure_counts", summary)
            self.assertIn("category_metrics", summary)
            self.assertIn("worst_failed_cases", summary)
            self.assertTrue((out / "metrics.json").exists())
            self.assertTrue((out / "per_case.csv").exists())
            self.assertTrue((out / "human_review.csv").exists())
            self.assertTrue((out / "metrics.md").exists())

    def test_metrics_runner_writes_all_mode_comparison(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            chunks, cases = _write_metrics_fixture(root)
            out = root / "mode_comparison"

            comparison = run_all_modes(cases_path=cases, chunks_path=chunks, out_dir=out)

            self.assertEqual(set(comparison["results"]), {"cheap", "balanced", "expensive"})
            self.assertTrue((out / "comparison.json").exists())
            self.assertTrue((out / "comparison.md").exists())
            self.assertTrue((out / "cheap" / "metrics.json").exists())
            self.assertIn("ranking", comparison)

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
            chunks, cases = _write_metrics_fixture(root)

            summary = run_evaluation(
                cases_path=cases,
                chunks_path=chunks,
                out_dir=root / "metrics",
                include_generation=True,
                generator=FailingGenerator(),
            )

            self.assertEqual(summary["generated_cases_attempted"], 48)
            self.assertEqual(summary["generated_cases_completed"], 0)
            self.assertEqual(summary["generated_error_cases"], 48)
            self.assertFalse(summary["generated_available"])
            self.assertIsNone(summary["generated_latency_p50_ms"])

    def test_generated_metrics_skip_generation_when_status_probe_fails(self) -> None:
        class UnavailableGenerator:
            model = "qwen3:8b"
            timeout_s = 2.0

            def status(self, *, timeout_s, smoke):
                return {"model_available": False, "smoke_ok": False, "error": "missing model"}

            def generate(self, _question, _hits):
                raise AssertionError("generation should be skipped when smoke probe fails")

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            chunks, cases = _write_metrics_fixture(root)

            summary = run_evaluation(
                cases_path=cases,
                chunks_path=chunks,
                out_dir=root / "metrics",
                include_generation=True,
                generator=UnavailableGenerator(),
            )

            self.assertEqual(summary["generated_cases_attempted"], 0)
            self.assertFalse(summary["generated_available"])
            self.assertIn("local Ollama model unavailable", summary["generated_unavailable_reason"])

    def test_case_set_validation_rejects_small_or_unlabeled_sets(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _chunks, cases = _write_metrics_fixture(root)
            loaded = load_cases(cases)
            validate_case_set(loaded)

            with self.assertRaisesRegex(ValueError, "at least 50"):
                validate_case_set(loaded[:49])

            missing_label = [case for case in loaded]
            payload = missing_label[0].__dict__.copy()
            payload["expected_chunk_ids"] = []
            payload["expected_source_urls"] = []
            payload["expected_chunk_id"] = None
            payload["expected_source_url"] = None
            bad_cases = [type(missing_label[0])(**payload), *missing_label[1:]]
            with self.assertRaisesRegex(ValueError, "source or chunk labels"):
                validate_case_set(bad_cases)

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

    def test_ollama_status_reports_unavailable_service(self) -> None:
        status = OllamaGenerator(base_url="http://127.0.0.1:9", timeout_s=0.1).status(timeout_s=0.1)

        self.assertFalse(status["service_available"])
        self.assertFalse(status["model_available"])
        self.assertIsNotNone(status["error"])

    def test_ollama_status_reports_available_model_and_smoke(self) -> None:
        tags_response = Mock()
        tags_response.json.return_value = {"models": [{"name": "qwen3:8b"}]}
        tags_response.raise_for_status.return_value = None
        generate_response = Mock()
        generate_response.json.return_value = {"response": "OK"}
        generate_response.raise_for_status.return_value = None

        with patch("httpx.get", return_value=tags_response), patch("httpx.post", return_value=generate_response):
            status = OllamaGenerator(model="qwen3:8b").status(timeout_s=0.1, smoke=True)

        self.assertTrue(status["service_available"])
        self.assertTrue(status["model_available"])
        self.assertTrue(status["smoke_ok"])


def _write_metrics_fixture(root: Path) -> tuple[Path, Path]:
    chunks = root / "chunks.jsonl"
    en_chunk = _chunk(
        document_id="en:html:attendance",
        chunk_id="en-attendance:c1",
        source_url="https://mevzuat.emu.edu.tr/content/en/attendance.htm",
        source_title="Attendance",
        language="en",
        corpus="regulations_en",
        text="Students must meet the attendance requirement. Academic staff salaries and scales are cited here.",
    )
    tr_chunk = _chunk(
        document_id="tr:html:devam",
        chunk_id="tr-devam:c1",
        source_url="https://mevzuat.emu.edu.tr/content/tr/devam.htm",
        source_title="Devam",
        language="tr",
        corpus="regulations_tr",
        text="Öğrenciler devam zorunluluğuna uyar. Akademik personel maaş ve barem kuralları burada belirtilir.",
    )
    chunks.write_text(
        json.dumps(en_chunk, ensure_ascii=False) + "\n" + json.dumps(tr_chunk, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )

    records = []
    records.extend(
        _case(
            f"EN-A{i:02d}",
            "attendance requirement",
            "en",
            "answer",
            expected_corpus="regulations_en",
            chunk=en_chunk,
        )
        for i in range(1, 25)
    )
    records.extend(
        _case(
            f"TR-A{i:02d}",
            "devam zorunluluğu",
            "tr",
            "answer",
            expected_corpus="regulations_tr",
            chunk=tr_chunk,
        )
        for i in range(1, 25)
    )
    records.extend(_case(f"EN-R{i}", "Tell me about campus events", "en", "refuse") for i in range(1, 3))
    records.extend(_case(f"TR-R{i}", "Bugünkü etkinlikler nelerdir?", "tr", "refuse") for i in range(1, 3))
    records.extend(_case(f"EN-C{i}", "Which office should verify ambiguous attendance evidence?", "en", "clarify") for i in range(1, 3))
    records.extend(_case(f"TR-C{i}", "Hangi ofise sorulmalı: devam mı burs mu?", "tr", "clarify") for i in range(1, 3))
    records.extend(
        _case(
            f"EN-X{i}",
            "Are the attendance evidence excerpts conflicting?",
            "en",
            "conflict",
            expected_corpora=["regulations_en"],
            chunks=[en_chunk],
        )
        for i in range(1, 3)
    )
    records.extend(
        _case(
            f"TR-X{i}",
            "ogrenci devam celiskili mi?",
            "tr",
            "conflict",
            expected_corpora=["regulations_tr"],
            chunks=[tr_chunk],
        )
        for i in range(1, 3)
    )

    cases = root / "cases.jsonl"
    cases.write_text("\n".join(json.dumps(record, ensure_ascii=False) for record in records) + "\n", encoding="utf-8")
    return chunks, cases


def _chunk(
    *,
    document_id: str,
    chunk_id: str,
    source_url: str,
    source_title: str,
    language: str,
    corpus: str,
    text: str,
) -> dict:
    return {
        "document_id": document_id,
        "chunk_id": chunk_id,
        "parent_document_id": None,
        "source_type": "html",
        "source_url": source_url,
        "source_title": source_title,
        "language": language,
        "corpus": corpus,
        "access_tier": "public",
        "effective_date": None,
        "last_crawled_at": "2026-05-04T08:00:00Z",
        "version_hash": "hash",
        "section_path": "Article 1",
        "article_number": "1",
        "page_number": None,
        "chunk_text": text,
        "metadata": {},
    }


def _case(
    case_id: str,
    question: str,
    language: str,
    behavior: str,
    *,
    expected_corpus: str | None = None,
    expected_corpora: list[str] | None = None,
    chunk: dict | None = None,
    chunks: list[dict] | None = None,
) -> dict:
    chunks = chunks or ([chunk] if chunk else [])
    first = chunks[0] if chunks else None
    return {
        "case_id": case_id,
        "question": question,
        "language": language,
        "expected_behavior": behavior,
        "expected_corpus": expected_corpus,
        "expected_corpora": expected_corpora or ([expected_corpus] if expected_corpus else []),
        "expected_document_id": first["document_id"] if first else None,
        "expected_chunk_id": first["chunk_id"] if first else None,
        "expected_chunk_ids": [item["chunk_id"] for item in chunks],
        "expected_source_url": first["source_url"] if first else None,
        "expected_source_urls": [item["source_url"] for item in chunks],
        "expected_answer_keywords": ["attendance"] if language == "en" and behavior == "answer" else ["devam"] if behavior == "answer" else [],
        "category": "fixture",
        "review_status": "assistant_curated_pending_human_review",
        "is_correct": None,
        "citation_ok": None,
        "notes": "",
    }


if __name__ == "__main__":
    unittest.main()
