from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas

from emu_advisor.evaluation import load_cases
from emu_advisor.html_ingest import HtmlDocumentInput, HtmlScopeError, ingest_html_document
from emu_advisor.pdf_ingest import PdfDocumentInput, ingest_pdf_document
from emu_advisor.routing import filter_chunks_for_route, route_query, source_in_v1_scope
from emu_advisor.schema import validate_chunk


class HtmlIngestionTests(unittest.TestCase):
    def test_html_ingestion_emits_traceable_canonical_chunks(self) -> None:
        html = """
        <html>
          <head><title>Attendance Regulation</title></head>
          <body>
            <h1>Article 1 Attendance</h1>
            <p>Students must attend courses according to the official regulation.</p>
            <p>Absence limits are enforced by the academic unit.</p>
          </body>
        </html>
        """

        chunks = ingest_html_document(
            HtmlDocumentInput(
                html=html,
                source_url="https://mevzuat.emu.edu.tr/content/en/attendance.htm",
                last_crawled_at="2026-05-04T08:00:00Z",
            )
        )

        self.assertEqual(len(chunks), 1)
        chunk = validate_chunk(chunks[0])
        self.assertEqual(chunk.source.source_type, "html")
        self.assertEqual(chunk.source.language, "en")
        self.assertEqual(chunk.source.corpus, "regulations_en")
        self.assertEqual(chunk.article_number, "1")
        self.assertEqual(chunk.section_path, "Article 1 Attendance")
        self.assertTrue(chunk.source.version_hash)

    def test_html_ingestion_rejects_out_of_scope_source(self) -> None:
        with self.assertRaises(HtmlScopeError):
            ingest_html_document(
                HtmlDocumentInput(
                    html="<p>Course catalog content</p>",
                    source_url="https://catalog.emu.edu.tr/course.htm",
                )
            )

    def test_html_ingestion_preserves_table_rows_and_salary_derived_facts(self) -> None:
        html = """
        <html>
          <head><title>Academic Staff Salary</title></head>
          <body>
            <h2>II. COLUMN</h2>
            <table>
              <tr><th>POSITION</th><th>SCALE</th><th>1</th><th>14</th></tr>
              <tr><td><span>ASSIST. PROFESSOR</span></td><td>5</td><td>107,900.00</td><td>145,600.00</td></tr>
              <tr><td>PROFESSOR</td><td>7</td><td>159,600.00</td><td>188,200.00</td></tr>
            </table>
          </body>
        </html>
        """

        chunks = ingest_html_document(
            HtmlDocumentInput(
                html=html,
                source_url="https://mevzuat.emu.edu.tr/6-1_StaffingEmploymentAcademicStaff.htm",
                language="en",
                last_crawled_at="2026-05-05T08:00:00Z",
            )
        )

        table_rows = [chunk for chunk in chunks if chunk["metadata"].get("evidence_kind") == "table_row"]
        derived = [chunk for chunk in chunks if chunk["metadata"].get("evidence_kind") == "derived_fact"]

        self.assertTrue(any("ASSIST. PROFESSOR" in chunk["chunk_text"] for chunk in table_rows))
        self.assertTrue(any("Professor uses scale 7" in chunk["chunk_text"] for chunk in derived))
        self.assertTrue(any("Assistant Professor uses scale 5" in chunk["chunk_text"] for chunk in derived))
        self.assertTrue(any("107,900.00" in chunk["chunk_text"] and "188,200.00" in chunk["chunk_text"] for chunk in derived))
        self.assertTrue(all("table_id" in chunk["metadata"] for chunk in table_rows))


class PdfIngestionTests(unittest.TestCase):
    def test_pdf_ingestion_preserves_page_number_and_article(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            pdf_path = Path(tmp) / "fixture.pdf"
            c = canvas.Canvas(str(pdf_path), pagesize=letter)
            c.drawString(72, 720, "Article 4 PDF Attendance Rule")
            c.drawString(72, 700, "This page preserves citation metadata for testing.")
            c.showPage()
            c.drawString(72, 720, "Article 5 Table Rule")
            c.drawString(72, 700, "Grade 90 100 | Grade 80 89 | Grade 70 79")
            c.save()

            chunks = ingest_pdf_document(
                PdfDocumentInput(
                    pdf_path=pdf_path,
                    source_url="https://mevzuat.emu.edu.tr/content/en/fixture.pdf",
                    source_title="Fixture PDF Regulation",
                    language="en",
                    last_crawled_at="2026-05-04T08:00:00Z",
                )
            )

        self.assertEqual({chunk["page_number"] for chunk in chunks}, {1, 2})
        self.assertIn("4", {chunk["article_number"] for chunk in chunks})
        self.assertTrue(any(chunk["metadata"]["table_text_detected"] for chunk in chunks))
        for chunk in chunks:
            validate_chunk(chunk)


class RoutingTests(unittest.TestCase):
    def test_default_routing_keeps_english_and_turkish_separate(self) -> None:
        en_route = route_query("What is high honour?")
        tr_route = route_query("Yüksek şeref nedir?")

        self.assertEqual(en_route.corpora, ["regulations_en"])
        self.assertEqual(tr_route.corpora, ["regulations_tr"])
        self.assertFalse(en_route.cross_corpus)
        self.assertFalse(tr_route.cross_corpus)

    def test_explicit_cross_corpus_routing_searches_both(self) -> None:
        route = route_query("Compare English and Turkish leave rules", explicit_cross_corpus=True)

        self.assertTrue(route.cross_corpus)
        self.assertEqual(route.corpora, ["regulations_en", "regulations_tr"])

    def test_cross_corpus_and_regulation_course_questions_are_in_scope(self) -> None:
        self.assertTrue(route_query("İngilizce ve Türkçe izin kurallarını karşılaştır.").cross_corpus)
        self.assertTrue(route_query("What is the maximum course load?").in_scope)

    def test_out_of_scope_query_and_source_are_rejected(self) -> None:
        route = route_query("Tell me about today's campus events")
        tr_route = route_query("Bugünkü etkinlikler nelerdir?")

        self.assertFalse(route.in_scope)
        self.assertFalse(tr_route.in_scope)
        self.assertEqual(filter_chunks_for_route([{"corpus": "regulations_en"}], route), [])
        self.assertFalse(source_in_v1_scope("https://events.emu.edu.tr/today", source_type="html"))


class EvaluationTests(unittest.TestCase):
    def test_seed_evaluation_set_is_machine_readable(self) -> None:
        cases = load_cases(Path("eval_sets/v1_gold.jsonl"))

        self.assertEqual(len(cases), 60)
        self.assertEqual(sum(1 for case in cases if case.language == "en"), 30)
        self.assertEqual(sum(1 for case in cases if case.language == "tr"), 30)
        self.assertEqual(sum(1 for case in cases if case.expected_behavior == "answer"), 48)
        self.assertEqual(sum(1 for case in cases if case.expected_behavior == "refuse"), 4)
        self.assertEqual(sum(1 for case in cases if case.expected_behavior == "clarify"), 4)
        self.assertEqual(sum(1 for case in cases if case.expected_behavior == "conflict"), 4)
        self.assertEqual({case.review_status for case in cases}, {"assistant_curated_pending_human_review"})
        for case in cases:
            if case.expected_behavior in {"answer", "conflict"}:
                self.assertTrue(case.expected_chunk_ids or case.expected_source_urls)

    def test_hard_regression_set_is_machine_readable(self) -> None:
        cases = load_cases(Path("eval_sets/v1_hard.jsonl"))

        self.assertEqual(len(cases), 50)
        self.assertEqual(sum(1 for case in cases if case.language == "en"), 25)
        self.assertEqual(sum(1 for case in cases if case.language == "tr"), 25)
        self.assertGreaterEqual(sum(1 for case in cases if case.category == "salary_table"), 20)
        self.assertGreaterEqual(sum(1 for case in cases if case.category == "scholarship_bundle"), 20)
        self.assertEqual({case.review_status for case in cases}, {"assistant_curated_hard_regression"})


if __name__ == "__main__":
    unittest.main()
