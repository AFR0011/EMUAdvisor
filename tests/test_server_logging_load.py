from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from fastapi.testclient import TestClient

from emu_advisor.audit_log import AuditEvent, AuditLogger
from emu_advisor.corpus import CorpusBundle, corpus_status
from emu_advisor.demo import demo_chunks
from emu_advisor.embeddings import HashEmbeddingModel
from emu_advisor.load_test import simulate_active_sessions
from emu_advisor.retrieval import HybridRetriever
from emu_advisor.server import create_app


class ServerTests(unittest.TestCase):
    def test_fastapi_health_whoami_and_ask(self) -> None:
        client = TestClient(create_app())

        health = client.get("/health")
        whoami = client.get("/whoami")
        answer = client.post(
            "/ask",
            json={"question": "What is the attendance requirement?", "mode": "balanced", "answer_style": "extractive"},
        )
        metrics = client.get("/metrics")
        corpus_status = client.get("/corpus/status")
        llm_status = client.get("/llm/status")
        home = client.get("/")
        admin = client.get("/admin")
        mode_metrics = client.get("/metrics/modes")
        chat = client.post("/chat", json={"question": "What is the attendance requirement?"})

        self.assertEqual(health.status_code, 200)
        self.assertTrue(health.json()["ok"])
        self.assertEqual(whoami.status_code, 200)
        self.assertEqual(whoami.json()["runtime"], "local-only demo")
        self.assertEqual(answer.status_code, 200)
        self.assertIn(answer.json()["mode"], {"answer", "answer_uncertain"})
        self.assertGreaterEqual(len(answer.json()["citations"]), 1)
        self.assertIn("timings", answer.json())
        self.assertEqual(metrics.status_code, 200)
        self.assertEqual(corpus_status.status_code, 200)
        self.assertGreaterEqual(corpus_status.json()["chunk_count"], 1)
        self.assertIn("vector_backend", corpus_status.json())
        self.assertEqual(llm_status.status_code, 200)
        self.assertIn("model_available", llm_status.json())
        self.assertEqual(home.status_code, 200)
        self.assertEqual(admin.status_code, 200)
        self.assertEqual(mode_metrics.status_code, 200)
        self.assertIn("balanced", mode_metrics.json()["modes"])
        self.assertEqual(chat.status_code, 200)
        self.assertIn(chat.json()["state"], {"answer", "answer_uncertain"})
        self.assertIn("citations", chat.json())
        self.assertNotIn("hits", chat.json())
        self.assertNotIn("timings", chat.json())

    def test_generated_answer_style_uses_extractive_fallback_when_model_unavailable(self) -> None:
        client = TestClient(create_app())

        with patch(
            "emu_advisor.generation.OllamaGenerator.status",
            return_value={"model_available": False, "smoke_ok": False, "error": "missing model", "latency_ms": 1},
        ):
            answer = client.post(
                "/ask",
                json={"question": "What is the attendance requirement?", "mode": "balanced", "answer_style": "generated"},
            )

        payload = answer.json()
        self.assertEqual(answer.status_code, 200)
        self.assertIsNone(payload["generated_answer"])
        self.assertIn("local Ollama generation unavailable", payload["generated_error"])
        self.assertEqual(payload["answer"], payload["extractive_answer"])
        self.assertEqual(payload["timings"]["generation_ms"], 1)

    def test_stream_endpoint_returns_ndjson_events(self) -> None:
        client = TestClient(create_app())

        response = client.post("/ask/stream", json={"question": "What is high honour?"})

        self.assertEqual(response.status_code, 200)
        lines = [json.loads(line) for line in response.text.splitlines() if line.strip()]
        self.assertEqual(lines[0]["type"], "extractive_answer")
        self.assertEqual(lines[-1]["type"], "done")

    def test_broad_scholarship_prompt_returns_grouped_extractive_without_generation(self) -> None:
        chunks = [
            _server_chunk(
                "scholarship:entrance",
                "EMU entrance incentive scholarship first 5000 includes tuition exemption, dormitory accommodation, and monthly pocket money.",
                source_title="Student Scholarship Regulation",
            ),
            _server_chunk(
                "scholarship:international",
                "International student scholarship tuition fee discount may be granted as exemption scholarship or 25% and 50% tuition fee discount.",
                source_title="Student Scholarship Regulation",
            ),
            _server_chunk(
                "scholarship:honour",
                "High honour scholarship is granted to top 1% students and may provide 20%, 15%, or 10% tuition fee awards.",
                source_title="Student Scholarship Regulation",
            ),
            _server_chunk(
                "scholarship:sports",
                "Sports grant scholarship covers full or partial tuition fees or dormitory accommodation for successful sports involvement.",
                source_title="Student Scholarship Regulation",
            ),
            _server_chunk(
                "scholarship:ra",
                "Research assistant postgraduate scholarship category A, B, and C may include tuition exemption and monthly scholarship based on net minimum wage.",
                source_title="Research Assistant Regulation",
                source_url="https://mevzuat.emu.edu.tr/5-4-3-Rules-Research_assistant_by-law-m.htm",
            ),
            _server_chunk(
                "scholarship:disabled",
                "Student with disability scholarship may provide tuition fee support under the scholarship regulation.",
                source_title="Student Scholarship Regulation",
            ),
        ]
        bundle = CorpusBundle(chunks=chunks, source="test", path=None, status=corpus_status(chunks, path=None))

        with patch("emu_advisor.server.load_corpus", return_value=bundle), patch(
            "emu_advisor.generation.OllamaGenerator.generate", side_effect=AssertionError("generation should not run")
        ):
            client = TestClient(create_app())
            response = client.post("/ask", json={"question": "How to get a scholarship?", "answer_style": "both"})

        payload = response.json()
        self.assertEqual(response.status_code, 200)
        self.assertEqual(payload["answer_type"], "topic_bundle")
        self.assertIsNone(payload["generated_answer"])
        self.assertIn("Which scholarship type should I expand", payload["answer"])
        titles = {group["title"] for group in payload["evidence_groups"]}
        self.assertIn("Research assistant and postgraduate scholarships", titles)
        self.assertIn("Sports grant", titles)
        self.assertIn("High-honour award", titles)


class AuditLoggingTests(unittest.TestCase):
    def test_audit_log_hashes_session_id_and_keeps_debug_fields(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "audit.jsonl"
            logger = AuditLogger(path, salt="test")
            logger.log(
                AuditEvent(
                    event_type="ask",
                    query="attendance requirement",
                    session_id="user@example.com",
                    route={"corpora": ["regulations_en"]},
                    answer_mode="answer",
                    latency_ms=12,
                    citation_ids=["doc:c1"],
                )
            )
            payload = json.loads(path.read_text(encoding="utf-8"))

        self.assertNotIn("user@example.com", json.dumps(payload))
        self.assertEqual(payload["answer_mode"], "answer")
        self.assertEqual(payload["citation_ids"], ["doc:c1"])
        self.assertIsNotNone(payload["session_hash"])


class LoadSimulationTests(unittest.TestCase):
    def test_active_session_simulation_completes_all_sessions(self) -> None:
        retriever = HybridRetriever(demo_chunks(), embedder=HashEmbeddingModel(dimensions=64))

        result = simulate_active_sessions(
            retriever,
            ["What is the attendance requirement?", "Yüksek şeref nedir?"],
            active_sessions=50,
            max_workers=4,
        )

        self.assertEqual(result.active_sessions, 50)
        self.assertEqual(result.completed, 50)
        self.assertEqual(result.extractive_fallbacks, 50)

def _server_chunk(
    chunk_id: str,
    text: str,
    *,
    source_title: str,
    source_url: str = "https://mevzuat.emu.edu.tr/5-1-2-Rules-Scholarship_regulations.htm",
) -> dict:
    return {
        "document_id": chunk_id.split(":")[0],
        "chunk_id": chunk_id,
        "parent_document_id": None,
        "source_type": "html",
        "source_url": source_url,
        "source_title": source_title,
        "language": "en",
        "corpus": "regulations_en",
        "access_tier": "public",
        "effective_date": None,
        "last_crawled_at": "2026-05-05T08:00:00Z",
        "version_hash": "abc123" * 11,
        "section_path": "Scholarships",
        "article_number": "7",
        "page_number": None,
        "chunk_text": text,
        "metadata": {"fixture": True, "evidence_kind": "text"},
    }


if __name__ == "__main__":
    unittest.main()
