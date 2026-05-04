from __future__ import annotations

import unittest

from emu_advisor.embeddings import DEFAULT_EMBEDDING_MODEL, HashEmbeddingModel
from emu_advisor.evaluation import evaluate_hits
from emu_advisor.modes import MODE_PRESETS, validate_modes
from emu_advisor.retrieval import HybridRetriever
from emu_advisor.routing import route_query
from emu_advisor.schema import validate_chunk
from emu_advisor.store import LocalVectorStore


def chunk(
    chunk_id: str,
    text: str,
    *,
    language: str = "en",
    corpus: str = "regulations_en",
    document_id: str | None = None,
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
        "metadata": {"fixture": True},
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
            expected_document_id = "en:html:attendance"

        metric = evaluate_hits(Case, hits)  # type: ignore[arg-type]

        self.assertTrue(metric.top5)
        self.assertEqual(metric.hit_rank, 1)


if __name__ == "__main__":
    unittest.main()
