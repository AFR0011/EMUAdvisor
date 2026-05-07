from __future__ import annotations

import unittest
from unittest.mock import patch

from emu_advisor.answer import build_extractive_answer
from emu_advisor.embeddings import DEFAULT_EMBEDDING_MODEL, HashEmbeddingModel
from emu_advisor.evaluation import evaluate_hits
from emu_advisor.modes import MODE_PRESETS, validate_modes
from emu_advisor.retrieval import HybridRetriever
from emu_advisor.routing import route_query
from emu_advisor.schema import validate_chunk
from emu_advisor.store import LocalVectorStore, QdrantVectorStore


def chunk(
    chunk_id: str,
    text: str,
    *,
    language: str = "en",
    corpus: str = "regulations_en",
    document_id: str | None = None,
    metadata: dict | None = None,
) -> dict:
    record = {
        "document_id": document_id or chunk_id.split(":")[0],
        "chunk_id": chunk_id,
        "parent_document_id": None,
        "source_type": "html",
        "source_url": f"https://mevzuat.emu.edu.tr/content/{language}/{chunk_id}.htm",
        "source_title": f"Fixture {chunk_id}",
        "language": language,
        "corpus": corpus,
        "access_tier": "public",
        "effective_date": None,
        "last_crawled_at": "2026-05-04T08:00:00Z",
        "version_hash": "abc123" * 11,
        "section_path": "Article 1",
        "article_number": "1",
        "page_number": None,
        "chunk_text": text,
        "metadata": {"fixture": True, **(metadata or {})},
    }
    validate_chunk(record)
    return record


class EmbeddingModeStoreTests(unittest.TestCase):
    def test_default_embedding_is_local_multilingual_not_english_e5(self) -> None:
        embedder = HashEmbeddingModel(dimensions=64)

        self.assertEqual(DEFAULT_EMBEDDING_MODEL, "local-hash-multilingual-v1")
        self.assertNotIn("e5-base-v2", embedder.metadata.model_name)
        self.assertEqual(len(embedder.encode_one("Yüksek şeref high honour")), 64)
        self.assertEqual(embedder.encode_one("attendance"), embedder.encode_one("attendance"))

    def test_modes_are_executable_and_change_more_than_llm_label(self) -> None:
        validate_modes()

        self.assertLess(MODE_PRESETS["cheap"].retrieval_fanout, MODE_PRESETS["balanced"].retrieval_fanout)
        self.assertFalse(MODE_PRESETS["cheap"].rerank_enabled)
        self.assertTrue(MODE_PRESETS["balanced"].rerank_enabled)
        self.assertGreater(MODE_PRESETS["expensive"].max_context_chunks, MODE_PRESETS["cheap"].max_context_chunks)

    def test_local_vector_store_filters_payloads(self) -> None:
        embedder = HashEmbeddingModel(dimensions=32)
        store = LocalVectorStore(dimensions=32)
        store.upsert_chunks(
            [
                chunk("en-doc:c1", "attendance rule", language="en", corpus="regulations_en"),
                chunk("tr-doc:c1", "devam kuralı", language="tr", corpus="regulations_tr"),
            ],
            embedder,
        )

        filtered = store.filter(filters={"corpus": "regulations_tr"})

        self.assertEqual(len(filtered), 1)
        self.assertEqual(filtered[0]["language"], "tr")
        self.assertIn("corpus", store.payload_indexes)

    def test_qdrant_vector_store_uses_client_payloads_without_real_service(self) -> None:
        class FakeClient:
            def __init__(self) -> None:
                self.recreated = False
                self.points = []

            def recreate_collection(self, collection_name, dimensions) -> None:
                self.recreated = (collection_name, dimensions)

            def upsert(self, *, collection_name, points) -> None:
                self.points.extend(points)

            def query(self, collection_name, query_vector, *, limit, filters):
                return [{"payload": point["payload"], "score": 0.75} for point in self.points[:limit]]

            def filter(self, collection_name, *, filters):
                return [point["payload"] for point in self.points if point["payload"].get("corpus") == filters.get("corpus")]

        embedder = HashEmbeddingModel(dimensions=32)
        client = FakeClient()
        store = QdrantVectorStore(client=client, collection_name="emu_regulations", dimensions=32)
        record = chunk("en-doc:c1", "attendance rule", language="en", corpus="regulations_en")

        store.recreate_collection()
        count = store.upsert_chunks([record], embedder)
        hits = store.query(embedder.encode_one("attendance"), limit=1, filters={"corpus": "regulations_en"})

        self.assertEqual(count, 1)
        self.assertEqual(client.recreated, ("emu_regulations", 32))
        self.assertEqual(hits[0]["chunk_id"], "en-doc:c1")
        self.assertEqual(hits[0]["_dense_score"], 0.75)


class RetrievalTests(unittest.TestCase):
    def test_hybrid_retrieval_keeps_language_filters_and_finds_expected_chunk(self) -> None:
        chunks = [
            chunk("attendance:c1", "Article 1 Students must meet the attendance requirement.", document_id="en:html:attendance"),
            chunk("honour:c1", "High honour requires the stated CGPA threshold.", document_id="en:html:honour"),
            chunk(
                "devam:c1",
                "Madde 1 Öğrenciler devam zorunluluğuna uymalıdır.",
                language="tr",
                corpus="regulations_tr",
                document_id="tr:html:devam",
            ),
        ]
        retriever = HybridRetriever(chunks, embedder=HashEmbeddingModel(dimensions=64))

        en_hits = retriever.retrieve("attendance requirement", top_k=2)
        tr_hits = retriever.retrieve("devam zorunluluğu", top_k=2)

        self.assertEqual(en_hits[0]["document_id"], "en:html:attendance")
        self.assertTrue(all(hit["corpus"] == "regulations_en" for hit in en_hits))
        self.assertEqual(tr_hits[0]["document_id"], "tr:html:devam")
        self.assertTrue(all(hit["corpus"] == "regulations_tr" for hit in tr_hits))

    def test_retrieval_metrics_report_top5_supporting_evidence(self) -> None:
        chunks = [
            chunk("attendance:c1", "Students must meet the attendance requirement.", document_id="en:html:attendance"),
            chunk("other:c1", "Unrelated regulation text.", document_id="en:html:other"),
        ]
        retriever = HybridRetriever(chunks, embedder=HashEmbeddingModel(dimensions=64))
        hits = retriever.retrieve("attendance requirement", route=route_query("attendance requirement"), top_k=5)

        class Case:
            case_id = "EN-001"
            expected_behavior = "answer"
            expected_chunk_id = None
            expected_chunk_ids = []
            expected_document_id = "en:html:attendance"
            expected_source_url = None
            expected_source_urls = []
            expected_answer_keywords = []

        metric = evaluate_hits(Case, hits)  # type: ignore[arg-type]

        self.assertTrue(metric.top5)
        self.assertEqual(metric.hit_rank, 1)

    def test_qdrant_backend_falls_back_to_local_unless_required(self) -> None:
        chunks = [chunk("attendance:c1", "Students must meet the attendance requirement.", document_id="en:html:attendance")]

        with patch("emu_advisor.retrieval.QdrantVectorStore", side_effect=RuntimeError("qdrant down")):
            retriever = HybridRetriever(chunks, embedder=HashEmbeddingModel(dimensions=64), vector_backend="qdrant")

        self.assertEqual(retriever.vector_backend, "local")
        self.assertIn("Qdrant unavailable", retriever.backend_warning or "")

        with patch("emu_advisor.retrieval.QdrantVectorStore", side_effect=RuntimeError("qdrant down")):
            with self.assertRaises(RuntimeError):
                HybridRetriever(
                    chunks,
                    embedder=HashEmbeddingModel(dimensions=64),
                    vector_backend="qdrant",
                    require_qdrant=True,
                )

    def test_salary_query_prefers_derived_table_evidence_and_preserves_ranges(self) -> None:
        chunks = [
            chunk(
                "salary:c1",
                "Academic salary comparison derived from the salary scales table: Professor uses scale 7 with steps 1-14 from 159,600.00 to 188,200.00. Assistant Professor uses scale 5 with steps 1-14 from 107,900.00 to 145,600.00.",
                document_id="en:html:6-1-staffing",
                metadata={"evidence_kind": "derived_fact", "derived_type": "salary_comparison"},
            ),
            chunk(
                "salary:c2",
                "General academic staff appointment rules mention professor and assistant professor titles.",
                document_id="en:html:6-1-staffing",
            ),
        ]
        retriever = HybridRetriever(chunks, embedder=HashEmbeddingModel(dimensions=64))

        hits = retriever.retrieve("what is the salary range of a professor compared to assistant professor?", top_k=2)
        answer = build_extractive_answer("what is the salary range of a professor compared to assistant professor?", hits)

        self.assertEqual(hits[0]["metadata"]["evidence_kind"], "derived_fact")
        self.assertEqual(answer.answer_type, "table")
        self.assertIn("159,600.00", answer.text)
        self.assertIn("145,600.00", answer.text)


if __name__ == "__main__":
    unittest.main()
