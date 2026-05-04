from __future__ import annotations

import json
import subprocess
import sys
import unittest
from pathlib import Path

from emu_advisor.schema import (
    SchemaValidationError,
    legacy_chunk_to_canonical,
    validate_chunk,
)


FIXTURES = Path(__file__).resolve().parent / "fixtures"


class CanonicalSchemaTests(unittest.TestCase):
    def test_valid_chunk_fixture_records_validate(self) -> None:
        path = FIXTURES / "canonical_chunks.valid.jsonl"
        records = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]

        chunks = [validate_chunk(record) for record in records]

        self.assertEqual(chunks[0].source.language, "en")
        self.assertEqual(chunks[1].source.source_type, "pdf")
        self.assertEqual(chunks[1].page_number, 7)

    def test_invalid_chunk_fixture_reports_expected_issues(self) -> None:
        path = FIXTURES / "canonical_chunks.invalid.jsonl"
        record = json.loads(path.read_text(encoding="utf-8"))

        with self.assertRaises(SchemaValidationError) as raised:
            validate_chunk(record)

        fields = {issue.field for issue in raised.exception.issues}
        self.assertIn("document_id", fields)
        self.assertIn("source_type", fields)
        self.assertIn("language", fields)
        self.assertIn("chunk_text", fields)

    def test_legacy_chunk_mapping_creates_canonical_record(self) -> None:
        record = legacy_chunk_to_canonical(
            {
                "doc_id": "5-1-0-Regulation",
                "chunk_id": "legacy-1",
                "title": "Legacy Regulation",
                "url": "https://mevzuat.emu.edu.tr/content/en/legacy.htm",
                "lang": "en",
                "section_path": ["Chapter 1", "Article 2"],
                "text": "Legacy chunk text with enough source context.",
            },
            last_crawled_at="2026-05-04T08:00:00Z",
        )

        chunk = validate_chunk(record)
        self.assertEqual(chunk.document_id, "5-1-0-Regulation")
        self.assertEqual(chunk.section_path, "Chapter 1 > Article 2")
        self.assertTrue(chunk.metadata["legacy_source"])
        self.assertTrue(chunk.metadata["legacy_missing_source_hash"])

    def test_jsonl_validator_cli_accepts_valid_fixture(self) -> None:
        path = FIXTURES / "canonical_chunks.valid.jsonl"

        result = subprocess.run(
            [sys.executable, "-m", "emu_advisor.validate_jsonl", str(path), "--kind", "chunk"],
            cwd=Path(__file__).resolve().parents[1],
            text=True,
            capture_output=True,
            check=False,
        )

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("valid chunk JSONL", result.stdout)

    def test_jsonl_validator_cli_rejects_invalid_fixture(self) -> None:
        path = FIXTURES / "canonical_chunks.invalid.jsonl"

        result = subprocess.run(
            [sys.executable, "-m", "emu_advisor.validate_jsonl", str(path), "--kind", "chunk"],
            cwd=Path(__file__).resolve().parents[1],
            text=True,
            capture_output=True,
            check=False,
        )

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("source_type", result.stderr)


if __name__ == "__main__":
    unittest.main()
