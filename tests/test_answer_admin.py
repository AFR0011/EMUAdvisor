from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from emu_advisor.admin import activate_snapshot, copy_active_chunks, diff_snapshots, write_snapshot
from emu_advisor.answer import build_extractive_answer, progressive_answer_events
from emu_advisor.citations import citation_from_chunk
from emu_advisor.schema import validate_chunk


def chunk(chunk_id: str, text: str, *, source_type: str = "html", page_number: int | None = None, metadata: dict | None = None) -> dict:
    record = {
        "document_id": chunk_id.split(":")[0],
        "chunk_id": chunk_id,
        "parent_document_id": None,
        "source_type": source_type,
        "source_url": "https://mevzuat.emu.edu.tr/content/en/fixture.pdf" if source_type == "pdf" else "https://mevzuat.emu.edu.tr/content/en/fixture.htm",
        "source_title": "Fixture Regulation",
        "language": "en",
        "corpus": "regulations_en",
        "access_tier": "public",
        "effective_date": None,
        "last_crawled_at": "2026-05-04T08:00:00Z",
        "version_hash": "hash-" + chunk_id,
        "section_path": "Article 4",
        "article_number": "4",
        "page_number": page_number,
        "chunk_text": text,
        "metadata": metadata or {},
        "score": 0.9,
    }
    validate_chunk(record)
    return record


class AnswerTests(unittest.TestCase):
    def test_strong_evidence_builds_extractive_answer_with_citation(self) -> None:
        hit = chunk("doc:c1", "Article 4 Attendance requirement is stated here for students.")

        answer = build_extractive_answer("attendance requirement", [hit])

        self.assertEqual(answer.mode, "answer")
        self.assertEqual(answer.decision.level, "strong")
        self.assertEqual(len(answer.citations), 1)
        self.assertIn("Attendance requirement", answer.text)

    def test_weak_evidence_refuses_without_generation(self) -> None:
        answer = build_extractive_answer("attendance requirement", [chunk("doc:c1", "Unrelated text only.")])

        self.assertEqual(answer.mode, "refuse")
        self.assertEqual(answer.citations, [])

    def test_conflict_is_shown_not_resolved(self) -> None:
        hits = [
            chunk("doc-a:c1", "Deadline is ten days.", metadata={"conflict_key": "deadline", "conflict_value": "10"}),
            chunk("doc-b:c1", "Deadline is fifteen days.", metadata={"conflict_key": "deadline", "conflict_value": "15"}),
        ]

        answer = build_extractive_answer("deadline", hits)

        self.assertEqual(answer.mode, "show_conflict")
        self.assertIn("appears to conflict", answer.text)
        self.assertIn("verify", answer.text.lower())

    def test_conflict_intent_is_not_answered_as_final_advice(self) -> None:
        hit = chunk("doc:c1", "Article 4 says deadlines are announced by the academic unit.")

        answer = build_extractive_answer("What if two rules give different deadlines?", [hit])

        self.assertEqual(answer.mode, "show_conflict")
        self.assertIn("conflict", answer.text.lower())

    def test_official_clarification_intent_asks_for_scope(self) -> None:
        hit = chunk("doc:c1", "Regulation evidence mentions the relevant academic unit.")

        answer = build_extractive_answer("Which office should verify ambiguous regulation conflicts?", [hit])

        self.assertEqual(answer.mode, "clarify")

    def test_progressive_answer_keeps_fallback_when_generation_fails(self) -> None:
        hit = chunk("doc:c1", "Article 4 Attendance requirement is stated here for students.")

        def failing_generator(_query, _hits):
            raise RuntimeError("local model unavailable")
            yield ""

        events = list(progressive_answer_events("attendance requirement", [hit], generator=failing_generator))

        self.assertEqual(events[0]["type"], "extractive_answer")
        self.assertIn("generation_error", {event["type"] for event in events})
        self.assertEqual(events[-1], {"type": "done", "generated": False})

    def test_pdf_citation_includes_page_number(self) -> None:
        citation = citation_from_chunk(chunk("doc:c1", "PDF evidence", source_type="pdf", page_number=7))

        self.assertIn("p. 7", citation.label())
        self.assertEqual(citation.page_number, 7)


class AdminWorkflowTests(unittest.TestCase):
    def test_snapshot_diff_and_activation(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            first = write_snapshot([chunk("doc:c1", "Attendance requirement text.")], root / "snapshots", label="first")
            changed = chunk("doc:c1", "Attendance requirement text changed.")
            changed["version_hash"] = "new-hash"
            second = write_snapshot([changed, chunk("doc2:c1", "Additional rule.")], root / "snapshots", label="second")

            diff = diff_snapshots(first, second)
            pointer = root / "active_snapshot.txt"
            active_chunks = root / "active" / "chunks.jsonl"
            activate_snapshot(second, pointer)
            copy_active_chunks(pointer, active_chunks)

            self.assertEqual(diff.added, ["doc2"])
            self.assertEqual(diff.changed, ["doc"])
            self.assertTrue(active_chunks.exists())


if __name__ == "__main__":
    unittest.main()
