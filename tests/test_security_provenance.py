from __future__ import annotations

import json
import os
import tempfile
import unittest
import re
from pathlib import Path
from unittest.mock import patch

import httpx
from fastapi.testclient import TestClient

os.environ.setdefault("EMU_ADVISOR_PROFILE", "test")
os.environ.setdefault("EMU_ADVISOR_CORPUS_MODE", "fixture")
os.environ.setdefault("EMU_ADVISOR_QUERY_REWRITE", "deterministic")

from emu_advisor.conversation_store import ConversationStore
from emu_advisor.corpus import load_corpus
from emu_advisor.evaluation import EvaluationCase, citation_matches_expected_evidence
from emu_advisor.pipeline import _fetch, is_allowed_crawl_url
from emu_advisor.server import create_app
from tools.publication_guard import verify_human_review_contract


def _case(*, behavior: str = "answer", chunks: list[str] | None = None, sources: list[str] | None = None) -> EvaluationCase:
    chunks = chunks or []
    sources = sources or []
    return EvaluationCase(
        case_id="synthetic",
        question="synthetic question",
        language="en",
        expected_behavior=behavior,
        expected_corpus="regulations_en",
        expected_document_id=None,
        expected_chunk_id=chunks[0] if chunks else None,
        expected_source_url=sources[0] if sources else None,
        expected_corpora=["regulations_en"],
        expected_chunk_ids=chunks,
        expected_source_urls=sources,
        expected_answer_keywords=["keyword"],
        category="synthetic",
        is_correct=None,
        citation_ok=None,
        review_status="assistant_curated_pending_independent_review",
        notes="synthetic",
    )


class SessionCapabilityTests(unittest.TestCase):
    def test_cross_session_read_export_and_clear_are_uniformly_denied(self) -> None:
        with patch.dict(
            os.environ,
            {
                "EMU_ADVISOR_PROFILE": "test",
                "EMU_ADVISOR_CORPUS_MODE": "fixture",
                "EMU_ADVISOR_QUERY_REWRITE": "deterministic",
                "EMU_ADVISOR_ENABLE_CHAT_PERSISTENCE": "0",
                "EMU_ADVISOR_ENABLE_AUDIT_LOGGING": "0",
            },
            clear=False,
        ):
            client = TestClient(create_app())
        first = client.post("/chat", json={"question": "Hi"}).json()
        second = client.post("/chat", json={"question": "Hello"}).json()
        own = {"X-EMU-Session-Capability": first["session_capability"]}
        other = {"X-EMU-Session-Capability": second["session_capability"]}

        self.assertEqual(client.get(f"/chat/session/{first['session_id']}", headers=own).status_code, 200)
        denied = [
            client.get(f"/chat/session/{first['session_id']}", headers=other),
            client.post("/chat/export", headers=other, json={"session_id": first["session_id"], "format": "markdown"}),
            client.post("/chat/clear", headers=other, json={"session_id": first["session_id"]}),
            client.post("/chat", headers=other, json={"session_id": first["session_id"], "question": "continue"}),
        ]
        self.assertEqual({response.status_code for response in denied}, {404})
        self.assertEqual({response.json()["detail"] for response in denied}, {"session unavailable"})

    def test_persistence_is_opt_in_and_stores_only_capability_hash(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "sessions.json"
            disabled = ConversationStore(path, persistence_enabled=False)
            disabled.create_session()
            self.assertFalse(path.exists())

            enabled = ConversationStore(path, persistence_enabled=True)
            access = enabled.create_session()
            payload = path.read_text(encoding="utf-8")
            self.assertNotIn(access.capability, payload)
            self.assertIn("capability_hash", payload)

    def test_legacy_persistence_file_is_not_loaded_or_rewritten(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "legacy.json"
            original = '{"version":1,"sessions":[{"session_id":"legacy","messages":[]}]}'
            path.write_text(original, encoding="utf-8")
            store = ConversationStore(path, persistence_enabled=True)
            store.create_session()
            self.assertEqual(path.read_text(encoding="utf-8"), original)
            self.assertEqual(store.list_sessions()[0].message_count, 0)


class CorpusModeAndSourceTests(unittest.TestCase):
    def test_corpus_mode_fails_closed_and_fixture_is_explicit(self) -> None:
        with self.assertRaises(RuntimeError):
            load_corpus(mode="", profile="test")
        with self.assertRaises(RuntimeError):
            load_corpus(mode="fixture", profile="production")
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaises(FileNotFoundError):
                load_corpus(Path(tmp) / "missing.jsonl", mode="artifact", profile="test")
        fixture = load_corpus(mode="fixture", profile="test")
        self.assertTrue(fixture.fixture)
        self.assertTrue(all(str(chunk["source_url"]).startswith("fixture://") for chunk in fixture.chunks))

    def test_real_source_scope_is_https_exact_host_without_credentials_or_bad_port(self) -> None:
        self.assertTrue(is_allowed_crawl_url("https://mevzuat.emu.edu.tr/rules.htm"))
        self.assertFalse(is_allowed_crawl_url("http://mevzuat.emu.edu.tr/rules.htm"))
        self.assertFalse(is_allowed_crawl_url("https://user@mevzuat.emu.edu.tr/rules.htm"))
        self.assertFalse(is_allowed_crawl_url("https://mevzuat.emu.edu.tr:8443/rules.htm"))
        self.assertFalse(is_allowed_crawl_url("https://evil.example/rules.htm"))

    def test_cross_host_redirect_is_rejected_before_target_request(self) -> None:
        requested: list[str] = []

        def handler(request: httpx.Request) -> httpx.Response:
            requested.append(str(request.url))
            return httpx.Response(302, headers={"Location": "https://evil.example/stolen"}, request=request)

        with httpx.Client(transport=httpx.MockTransport(handler), follow_redirects=False) as client:
            with self.assertRaisesRegex(ValueError, "out-of-scope redirect"):
                _fetch("https://mevzuat.emu.edu.tr/start", client)
        self.assertEqual(requested, ["https://mevzuat.emu.edu.tr/start"])


class EvidenceProxyTests(unittest.TestCase):
    def test_citation_requires_expected_chunk_and_conflict_requires_both(self) -> None:
        single = _case(chunks=["expected:c1"])
        self.assertEqual(citation_matches_expected_evidence(single, [{"chunk_id": "wrong:c1"}]), (False, "expected_chunk"))
        self.assertEqual(citation_matches_expected_evidence(single, [{"chunk_id": "expected:c1"}]), (True, "expected_chunk"))

        conflict = _case(behavior="conflict", chunks=["left:c1", "right:c1"])
        self.assertFalse(citation_matches_expected_evidence(conflict, [{"chunk_id": "left:c1"}])[0])
        self.assertTrue(citation_matches_expected_evidence(conflict, [{"chunk_id": "left:c1"}, {"chunk_id": "right:c1"}])[0])

    def test_source_fallback_is_used_only_without_expected_chunks(self) -> None:
        source = "https://mevzuat.emu.edu.tr/rule.htm"
        source_only = _case(sources=[source])
        self.assertEqual(citation_matches_expected_evidence(source_only, [{"source_url": source + "/"}]), (True, "expected_source"))
        chunk_primary = _case(chunks=["expected:c1"], sources=[source])
        self.assertFalse(citation_matches_expected_evidence(chunk_primary, [{"source_url": source}])[0])

    def test_human_review_status_cannot_self_certify(self) -> None:
        with self.assertRaises(ValueError):
            verify_human_review_contract(
                {"review_status": "human_reviewed_verified", "is_correct": True, "citation_ok": True}
            )


class PortabilityContractTests(unittest.TestCase):
    def test_ci_has_cross_platform_core_and_immutable_official_action_refs(self) -> None:
        workflow = Path(".github/workflows/ci.yml").read_text(encoding="utf-8")
        self.assertIn("ubuntu-latest", workflow)
        self.assertIn("windows-latest", workflow)
        self.assertIn("EMU_ADVISOR_CORPUS_MODE: fixture", workflow)
        refs = re.findall(r"uses:\s+(actions/(?:checkout|setup-python))@([0-9a-f]+)", workflow)
        self.assertGreaterEqual(len(refs), 4)
        self.assertTrue(all(len(sha) == 40 for _action, sha in refs))

    def test_uvloop_lock_is_excluded_on_windows(self) -> None:
        lock = Path("requirements-lock.txt").read_text(encoding="utf-8")
        self.assertIn('uvloop==0.22.1; sys_platform != "win32"', lock)


if __name__ == "__main__":
    unittest.main()
