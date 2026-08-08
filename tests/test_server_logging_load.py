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
from emu_advisor.query_understanding import QueryUnderstandingResult
from emu_advisor.retrieval import HybridRetriever
from emu_advisor.server import create_app


class ServerTests(unittest.TestCase):
    def setUp(self) -> None:
        self._env = patch.dict(
            "os.environ",
            {
                "EMU_ADVISOR_QUERY_REWRITE": "deterministic",
                "EMU_ADVISOR_DISABLE_CHAT_PERSISTENCE": "1",
            },
            clear=False,
        )
        self._env.start()

    def tearDown(self) -> None:
        self._env.stop()

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
        analytics = client.get("/analytics")

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
        self.assertIn("Open regulation assistant", home.text)
        self.assertNotIn('id="chat-form"', home.text)
        self.assertEqual(admin.status_code, 200)
        self.assertIn('id="user-panel"', admin.text)
        self.assertIn('id="diagnostics-panel"', admin.text)
        self.assertIn('data-view-tab="user"', admin.text)
        self.assertEqual(mode_metrics.status_code, 200)
        self.assertIn("balanced", mode_metrics.json()["modes"])
        self.assertEqual(chat.status_code, 200)
        self.assertIn(chat.json()["state"], {"answer", "answer_uncertain"})
        self.assertIn("citations", chat.json())
        self.assertNotIn("hits", chat.json())
        self.assertNotIn("timings", chat.json())
        self.assertEqual(analytics.status_code, 200)
        self.assertIn("events", analytics.json())

    def test_security_headers_are_present(self) -> None:
        client = TestClient(create_app())

        response = client.get("/")

        self.assertEqual(response.status_code, 200)
        self.assertIn("default-src 'self'", response.headers["content-security-policy"])
        self.assertEqual(response.headers["x-content-type-options"], "nosniff")
        self.assertEqual(response.headers["x-frame-options"], "DENY")

    def test_request_validation_is_sanitized_and_restrictive(self) -> None:
        client = TestClient(create_app())

        blank = client.post("/chat", json={"question": "   "})
        long_question = client.post("/chat", json={"question": "x" * 2001})
        invalid_mode = client.post("/ask", json={"question": "attendance", "mode": "fastest"})
        stale_cross_corpus = client.post("/chat", json={"question": "attendance", "cross_corpus": True})
        script_like = client.post("/chat", json={"question": "<script>alert(1)</script>"})

        self.assertEqual(blank.status_code, 422)
        self.assertEqual(long_question.status_code, 422)
        self.assertEqual(invalid_mode.status_code, 422)
        self.assertEqual(stale_cross_corpus.status_code, 422)
        self.assertNotIn("input", json.dumps(blank.json()))
        self.assertNotIn("x" * 100, json.dumps(long_question.json()))
        self.assertEqual(script_like.status_code, 200)
        self.assertNotIn("Traceback", json.dumps(script_like.json()))

    def test_admin_token_protects_debug_surfaces_but_not_public_chat(self) -> None:
        with patch.dict("os.environ", {"EMU_ADVISOR_ADMIN_TOKEN": "secret"}, clear=False):
            client = TestClient(create_app())

        public_chat = client.post("/chat", json={"question": "What is the attendance requirement?"})
        denied_ask = client.post("/ask", json={"question": "What is the attendance requirement?"})
        allowed_ask = client.post(
            "/ask",
            headers={"Authorization": "Bearer secret"},
            json={"question": "What is the attendance requirement?", "answer_style": "extractive"},
        )
        denied_metrics = client.get("/metrics")
        allowed_metrics = client.get("/metrics", headers={"X-EMU-Admin-Token": "secret"})
        query_token_ask = client.post(
            "/ask",
            params={"admin_token": "secret"},
            json={"question": "What is the attendance requirement?", "answer_style": "extractive"},
        )
        allowed_admin = client.get("/admin")

        self.assertEqual(public_chat.status_code, 200)
        self.assertEqual(denied_ask.status_code, 401)
        self.assertEqual(allowed_ask.status_code, 200)
        self.assertEqual(denied_metrics.status_code, 401)
        self.assertEqual(allowed_metrics.status_code, 200)
        self.assertEqual(query_token_ask.status_code, 401)
        self.assertEqual(allowed_admin.status_code, 200)

    def test_production_profile_requires_admin_token(self) -> None:
        with patch.dict("os.environ", {"EMU_ADVISOR_PROFILE": "production", "EMU_ADVISOR_ADMIN_TOKEN": ""}, clear=False):
            with self.assertRaises(RuntimeError):
                create_app()

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

    def test_chat_stream_returns_ndjson_session_and_answer(self) -> None:
        client = TestClient(create_app())

        with patch(
            "emu_advisor.generation.OllamaGenerator.status",
            return_value={"model_available": False, "smoke_ok": False, "error": "missing model", "latency_ms": 1},
        ):
            response = client.post(
                "/chat/stream",
                json={"question": "What is the attendance requirement?", "session_id": "test-stream"},
            )

        self.assertEqual(response.status_code, 200)
        self.assertIn("application/x-ndjson", response.headers.get("content-type", ""))
        lines = [json.loads(line) for line in response.text.splitlines() if line.strip()]
        types = [line["type"] for line in lines]
        self.assertEqual(types[0], "session")
        self.assertIn("extractive_answer", types)
        self.assertLess(types.index("generated_delta"), types.index("extractive_answer"))
        self.assertEqual(types[-1], "done")

    def test_user_chat_retrieval_uses_balanced_mode(self) -> None:
        observed_modes: list[str] = []
        original_retrieve = HybridRetriever.retrieve

        def capture_retrieve(self, query, *args, **kwargs):
            observed_modes.append(kwargs.get("mode"))
            return original_retrieve(self, query, *args, **kwargs)

        with patch.object(HybridRetriever, "retrieve", new=capture_retrieve), patch(
            "emu_advisor.generation.OllamaGenerator.status",
            return_value={"model_available": False, "smoke_ok": False, "error": "missing model", "latency_ms": 1},
        ):
            client = TestClient(create_app())
            chat = client.post("/chat", json={"question": "What is the attendance requirement?"})
            stream = client.post(
                "/chat/stream",
                json={"question": "What is the attendance requirement?", "session_id": "balanced-stream"},
            )

        self.assertEqual(chat.status_code, 200)
        self.assertEqual(stream.status_code, 200)
        self.assertGreaterEqual(len(observed_modes), 2)
        self.assertEqual(set(observed_modes), {"balanced"})

    def test_chat_sessions_list_does_not_error(self) -> None:
        client = TestClient(create_app())
        response = client.get("/chat/sessions")
        self.assertEqual(response.status_code, 200)
        self.assertIsInstance(response.json(), list)

    def test_casual_chat_returns_friendly_response(self) -> None:
        client = TestClient(create_app())
        response = client.post("/chat", json={"question": "Hi"})
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["state"], "casual")
        self.assertNotIn("could not find reliable support", payload["answer"].lower())

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

    def test_language_switch_uses_resolved_turkish_query_without_cross_corpus(self) -> None:
        observed_routes: list[tuple[str, tuple[str, ...]]] = []
        original_retrieve = HybridRetriever.retrieve

        def fake_understand(question, history=None, **_kwargs):
            if question == "buna nasil basvururum":
                self.assertTrue(any(msg.get("role") == "user" for msg in history or []))
                return QueryUnderstandingResult(
                    input_language="tr",
                    retrieval_language="tr",
                    standalone_query="Devam şartı için başvuru nasıl yapılır?",
                    is_follow_up=True,
                    confidence="high",
                    method="llm",
                )
            return QueryUnderstandingResult(
                input_language="en",
                retrieval_language="en",
                standalone_query=question,
                is_follow_up=False,
                confidence="high",
                method="llm",
            )

        def capture_retrieve(self, query, *args, **kwargs):
            route = kwargs.get("route")
            corpora = tuple(route.corpora) if route is not None else ()
            observed_routes.append((query, corpora))
            return original_retrieve(self, query, *args, **kwargs)

        with patch("emu_advisor.server.understand_query", side_effect=fake_understand), patch.object(
            HybridRetriever, "retrieve", new=capture_retrieve
        ), patch(
            "emu_advisor.generation.OllamaGenerator.status",
            return_value={"model_available": False, "smoke_ok": False, "error": "missing model", "latency_ms": 1},
        ):
            client = TestClient(create_app())
            first = client.post(
                "/chat",
                json={"question": "What is the attendance requirement?", "session_id": "language-switch-chat"},
            )
            second = client.post(
                "/chat",
                json={"question": "buna nasil basvururum", "session_id": "language-switch-chat"},
            )
            stream = client.post(
                "/chat/stream",
                json={"question": "buna nasil basvururum", "session_id": "language-switch-chat"},
            )

        self.assertEqual(first.status_code, 200)
        self.assertEqual(second.status_code, 200)
        self.assertEqual(second.json()["language"], "tr")
        self.assertEqual(stream.status_code, 200)
        stream_events = [json.loads(line) for line in stream.text.splitlines() if line.strip()]
        extractive_events = [event for event in stream_events if event.get("type") == "extractive_answer"]
        self.assertEqual(extractive_events[-1]["language"], "tr")
        self.assertIn(("Devam şartı için başvuru nasıl yapılır?", ("regulations_tr",)), observed_routes)
        self.assertTrue(all(corpora in {("regulations_en",), ("regulations_tr",)} for _, corpora in observed_routes))


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
        self.assertEqual(result.errors, 0)
        self.assertGreaterEqual(result.p95_latency_ms, result.p50_latency_ms)
        self.assertEqual(result.as_dict()["error_rate"], 0)

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
