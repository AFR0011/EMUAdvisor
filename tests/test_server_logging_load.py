from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from fastapi.testclient import TestClient

from emu_advisor.audit_log import AuditEvent, AuditLogger
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

    def test_stream_endpoint_returns_ndjson_events(self) -> None:
        client = TestClient(create_app())

        response = client.post("/ask/stream", json={"question": "What is high honour?"})

        self.assertEqual(response.status_code, 200)
        lines = [json.loads(line) for line in response.text.splitlines() if line.strip()]
        self.assertEqual(lines[0]["type"], "extractive_answer")
        self.assertEqual(lines[-1]["type"], "done")


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


if __name__ == "__main__":
    unittest.main()
