from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from emu_advisor.benchmark import benchmark_embedding
from emu_advisor.corpus import write_chunks_jsonl
from emu_advisor.eval_review import bind_seed_cases, export_review_csv, summarize_review_status
from emu_advisor.readiness import build_readiness_report, write_markdown_report
from emu_advisor.schema import validate_chunk


class BoardReadinessToolTests(unittest.TestCase):
    def test_eval_review_exports_csv_and_status(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            cases = tmp_path / "cases.jsonl"
            out = tmp_path / "review.csv"
            cases.write_text(json.dumps(_case_payload(), ensure_ascii=False) + "\n", encoding="utf-8")

            status = summarize_review_status([cases])
            result = export_review_csv(cases, out)

        self.assertEqual(status["total_cases"], 1)
        self.assertEqual(status["pending_cases"], 1)
        self.assertEqual(result["cases"], 1)

    def test_bind_seed_cases_adds_chunk_labels_when_source_matches(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            cases = tmp_path / "cases.jsonl"
            chunks = tmp_path / "chunks.jsonl"
            out = tmp_path / "bound.jsonl"
            cases.write_text(json.dumps(_case_payload(), ensure_ascii=False) + "\n", encoding="utf-8")
            write_chunks_jsonl([_chunk()], chunks)

            result = bind_seed_cases(cases, chunks, out)
            payload = json.loads(out.read_text(encoding="utf-8").splitlines()[0])

        self.assertEqual(result["bound_cases"], 1)
        self.assertEqual(payload["expected_chunk_id"], "doc:c1")
        self.assertIn("bound_pending_human_review", payload["review_status"])

    def test_embedding_benchmark_runs_against_small_case_set(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            cases = tmp_path / "cases.jsonl"
            chunks = tmp_path / "chunks.jsonl"
            cases.write_text(json.dumps(_case_payload(), ensure_ascii=False) + "\n", encoding="utf-8")
            write_chunks_jsonl([_chunk()], chunks)

            result = benchmark_embedding(cases_path=cases, chunks_path=chunks, embedding="hash")

        self.assertEqual(result["kind"], "embedding")
        self.assertEqual(result["cases"], 1)
        self.assertEqual(result["retrieval"]["top5"], 1.0)

    def test_readiness_report_can_write_markdown(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "docs").mkdir()
            (root / "eval_sets").mkdir()
            for path in [
                root / "EMU_RAG_Current_System_Specs.md",
                root / "docs" / "EMUAdvisor Full Analysis.md",
                root / "docs" / "DEMO_STORYBOARD.md",
                root / "docs" / "PUBLICATION_CHECKLIST.md",
            ]:
                path.write_text("ok\n", encoding="utf-8")
            for name in ["v1_gold.jsonl", "v1_hard.jsonl", "emu_gold_seed.jsonl"]:
                (root / "eval_sets" / name).write_text(json.dumps(_case_payload(), ensure_ascii=False) + "\n", encoding="utf-8")
            out = root / "docs" / "BOARD_DEMO_READINESS.md"

            report = build_readiness_report(root)
            write_markdown_report(report, out)
            exists = out.exists()

        self.assertTrue(exists)
        self.assertEqual(report["status"], "partial")


def _case_payload() -> dict:
    return {
        "case_id": "T-001",
        "question": "What is the attendance requirement?",
        "language": "en",
        "expected_behavior": "answer",
        "expected_corpus": "regulations_en",
        "expected_source_url": "https://mevzuat.emu.edu.tr/test.htm",
        "expected_source_urls": ["https://mevzuat.emu.edu.tr/test.htm"],
        "expected_answer_keywords": ["attendance"],
        "category": "functional",
        "review_status": "provisional_gold_seed_pending_source_binding",
        "is_correct": None,
        "citation_ok": None,
        "expected_answer_text": "Students must meet the attendance requirement.",
    }


def _chunk() -> dict:
    record = {
        "document_id": "doc",
        "chunk_id": "doc:c1",
        "parent_document_id": None,
        "source_type": "html",
        "source_url": "https://mevzuat.emu.edu.tr/test.htm",
        "source_title": "Test Regulation",
        "language": "en",
        "corpus": "regulations_en",
        "access_tier": "public",
        "effective_date": None,
        "last_crawled_at": "2026-05-07T08:00:00Z",
        "version_hash": "abc123" * 11,
        "section_path": "Article 1",
        "article_number": "1",
        "page_number": None,
        "chunk_text": "Students must meet the attendance requirement.",
        "metadata": {"fixture": True},
    }
    validate_chunk(record)
    return record


if __name__ == "__main__":
    unittest.main()
