# ============================================================
# tests/test_pipeline.py
# Comprehensive test suite covering all pipeline components.
#
# Test categories:
#   - Unit tests for individual modules
#   - Integration tests for the full RAG pipeline
#   - Evaluation sanity checks
#
# Run:
#   pytest tests/test_pipeline.py -v
#   pytest tests/test_pipeline.py -v -k "test_risk_agent"
# ============================================================

import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

# Add project root to path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))


# ============================================================
# Config Tests
# ============================================================

class TestSettings:
    """Verify that settings load correctly and directories exist."""

    def test_settings_import(self):
        """Settings module should import without errors."""
        from src.config.settings import settings
        assert settings is not None

    def test_required_fields(self):
        """Required fields should have non-None defaults."""
        from src.config.settings import settings
        assert settings.chunk_size > 0
        assert settings.chunk_overlap >= 0
        assert settings.retrieval_top_k > 0
        assert settings.rerank_top_n > 0
        assert settings.llm_model_name != ""
        assert settings.text_embedding_model != ""

    def test_supported_hazards(self):
        """Supported hazard list must contain core hazard types."""
        from src.config.settings import settings
        required = {"flood", "cyclone", "heatwave", "earthquake", "drought"}
        assert required.issubset(set(settings.supported_hazards))

    def test_chunk_size_greater_than_overlap(self):
        """Chunk size must exceed overlap to avoid infinite loops."""
        from src.config.settings import settings
        assert settings.chunk_size > settings.chunk_overlap


# ============================================================
# Ingestion Tests
# ============================================================

class TestLoader:
    """Test PDF loading utilities."""

    def test_hazard_infer_flood(self):
        """Flood-related filename should infer 'flood' hazard."""
        from src.ingestion.loader import _infer_hazard
        assert _infer_hazard("flood_preparedness_guide") == "flood"

    def test_hazard_infer_cyclone(self):
        """Hurricane filename should map to 'cyclone'."""
        from src.ingestion.loader import _infer_hazard
        assert _infer_hazard("hurricane_response_manual") == "cyclone"

    def test_hazard_infer_heatwave(self):
        """Heatwave filename should infer correctly."""
        from src.ingestion.loader import _infer_hazard
        assert _infer_hazard("extreme_heat_advisory") == "heatwave"

    def test_hazard_infer_general_fallback(self):
        """Unknown filename should fall back to 'general'."""
        from src.ingestion.loader import _infer_hazard
        assert _infer_hazard("unknown_document_v2") == "general"

    def test_page_record_repr(self):
        """PageRecord repr should include source and page info."""
        from src.ingestion.loader import PageRecord
        record = PageRecord("test_doc", 3, "Sample text content here.", {})
        repr_str = repr(record)
        assert "test_doc" in repr_str
        assert "3" in repr_str

    def test_image_record_repr(self):
        """ImageRecord repr should include source info."""
        from src.ingestion.loader import ImageRecord
        from PIL import Image
        img = Image.new("RGB", (100, 100), color=(0, 0, 255))
        record = ImageRecord("flood_guide", 2, 0, img, "A caption.", {})
        assert "flood_guide" in repr(record)

    def test_load_all_pdfs_empty_dir(self, tmp_path):
        """load_all_pdfs on an empty directory returns empty lists."""
        from src.ingestion.loader import load_all_pdfs
        pages, images = load_all_pdfs(raw_dir=tmp_path)
        assert pages == []
        assert images == []


class TestChunker:
    """Test text chunking logic."""

    def test_chunk_text_string_basic(self):
        """Basic chunking of a text string should return documents."""
        from src.ingestion.chunker import chunk_text_string
        text = "Climate change poses risks. " * 50   # ~1400 chars
        docs = chunk_text_string(
            text,
            base_metadata={"hazard": "general"},
            chunk_size=256,
            chunk_overlap=32,
        )
        assert len(docs) > 1, "Long text should produce multiple chunks."

    def test_chunk_preserves_metadata(self):
        """Metadata should be present in all produced chunks."""
        from src.ingestion.chunker import chunk_text_string
        docs = chunk_text_string(
            "Flood preparedness requires early action and planning. " * 20,
            base_metadata={"hazard": "flood", "source": "test"},
        )
        for doc in docs:
            assert "hazard" in doc.metadata
            assert doc.metadata["hazard"] == "flood"

    def test_chunk_index_increments(self):
        """chunk_index in metadata should be sequential."""
        from src.ingestion.chunker import chunk_text_string
        docs = chunk_text_string(
            "Sentence about floods. " * 60,
            chunk_size=128,
            chunk_overlap=16,
        )
        indices = [doc.metadata["chunk_index"] for doc in docs]
        assert indices == list(range(len(docs)))

    def test_empty_text_returns_empty(self):
        """Chunking empty/whitespace text should return no documents."""
        from src.ingestion.chunker import chunk_text_string
        docs = chunk_text_string("   ")
        assert docs == []

    def test_chunk_page_records_empty(self):
        """Chunking an empty list should return empty list."""
        from src.ingestion.chunker import chunk_page_records
        result = chunk_page_records([])
        assert result == []

    def test_chunk_page_records_skips_short_pages(self):
        """Pages with fewer than 50 chars should be skipped."""
        from src.ingestion.loader import PageRecord
        from src.ingestion.chunker import chunk_page_records
        short_record = PageRecord("test", 1, "Too short.", {"hazard": "flood"})
        result = chunk_page_records([short_record])
        assert result == []


# ============================================================
# Risk Agent Tests
# ============================================================

class TestRiskAgent:
    """Test rule-based and LLM-based hazard classification."""

    def test_flood_keyword_detection(self):
        """Direct flood keyword should be classified correctly."""
        from src.agents.risk_agent import risk_agent, HazardType
        ctx = risk_agent.analyze("What should I do during a flood?")
        assert ctx.hazard == HazardType.FLOOD

    def test_cyclone_keyword_detection(self):
        """Cyclone keyword should classify correctly."""
        from src.agents.risk_agent import risk_agent, HazardType
        ctx = risk_agent.analyze("How do I prepare for a cyclone season?")
        assert ctx.hazard == HazardType.CYCLONE

    def test_hurricane_maps_to_cyclone(self):
        """'Hurricane' should map to cyclone hazard type."""
        from src.agents.risk_agent import risk_agent, HazardType
        ctx = risk_agent.analyze("hurricane evacuation procedures")
        assert ctx.hazard == HazardType.CYCLONE

    def test_heatwave_detection(self):
        """Heatwave keywords should be classified."""
        from src.agents.risk_agent import risk_agent, HazardType
        ctx = risk_agent.analyze("extreme heat wave safety tips")
        assert ctx.hazard == HazardType.HEATWAVE

    def test_earthquake_detection(self):
        """Earthquake keywords should be classified."""
        from src.agents.risk_agent import risk_agent, HazardType
        ctx = risk_agent.analyze("seismic safety during an earthquake")
        assert ctx.hazard == HazardType.EARTHQUAKE

    def test_preparedness_intent(self):
        """Preparedness-related query should set correct intent."""
        from src.agents.risk_agent import risk_agent, QueryIntent
        ctx = risk_agent.analyze("How do I prepare for a flood emergency?")
        assert ctx.intent == QueryIntent.PREPAREDNESS
        assert ctx.needs_structured_output is True

    def test_information_intent(self):
        """Generic informational query should not trigger structured output."""
        from src.agents.risk_agent import risk_agent, QueryIntent
        ctx = risk_agent.analyze("What causes floods?")
        # Rule-based: no preparedness keyword
        assert ctx.intent == QueryIntent.INFORMATION

    def test_risk_context_to_dict(self):
        """RiskContext.to_dict() should contain all expected keys."""
        from src.agents.risk_agent import risk_agent
        ctx = risk_agent.analyze("flood preparation steps")
        d = ctx.to_dict()
        required_keys = {
            "hazard", "confidence", "intent",
            "needs_structured_output", "raw_query",
            "detected_keywords", "classification_method",
        }
        assert required_keys.issubset(d.keys())

    def test_confidence_range(self):
        """Confidence should always be in [0.0, 1.0]."""
        from src.agents.risk_agent import risk_agent
        for query in [
            "flood safety",
            "cyclone preparedness",
            "what is climate change",
            "heatwave survival guide",
        ]:
            ctx = risk_agent.analyze(query)
            assert 0.0 <= ctx.confidence <= 1.0


# ============================================================
# Retriever Tests
# ============================================================

class TestRetriever:
    """Test ChromaDB retrieval functions."""

    def test_get_vectorstore_stats_structure(self):
        """Stats dict should contain expected keys."""
        from src.retrieval.retriever import get_vectorstore_stats
        stats = get_vectorstore_stats()
        assert "text_document_count" in stats
        assert "image_document_count" in stats
        assert "vectorstore_path" in stats
        assert isinstance(stats["text_document_count"], int)

    def test_retrieve_text_chunks_empty_store(self):
        """Retrieval on empty store should return empty list, not raise."""
        from src.retrieval.retriever import retrieve_text_chunks
        # This will query an empty store — should return [] gracefully
        docs = retrieve_text_chunks("flood preparedness", top_k=5)
        assert isinstance(docs, list)

    def test_retrieve_with_hazard_filter(self):
        """Retrieval with hazard filter should not raise exceptions."""
        from src.retrieval.retriever import retrieve_text_chunks
        docs = retrieve_text_chunks(
            "what to do during a cyclone",
            hazard_filter="cyclone",
            top_k=3,
        )
        assert isinstance(docs, list)

    def test_retrieve_images_empty_store(self):
        """Image retrieval on empty store should return empty list."""
        from src.retrieval.retriever import retrieve_similar_images
        results = retrieve_similar_images("flood map", top_k=2)
        assert isinstance(results, list)


# ============================================================
# Reranker Tests
# ============================================================

class TestReranker:
    """Test document reranking logic."""

    def test_rerank_empty_list(self):
        """Reranking empty list should return empty list."""
        from src.retrieval.reranker import rerank_documents
        result = rerank_documents("flood safety", [], top_n=3)
        assert result == []

    def test_rerank_fewer_docs_than_top_n(self):
        """When docs < top_n, all docs are returned without reranking."""
        from langchain_core.documents import Document
        from src.retrieval.reranker import rerank_documents
        docs = [
            Document(page_content="Flood safety tips.", metadata={}),
            Document(page_content="Prepare emergency kit.", metadata={}),
        ]
        result = rerank_documents("flood safety", docs, top_n=5)
        assert len(result) == 2

    def test_rerank_returns_top_n(self):
        """Reranker should return exactly top_n documents."""
        from langchain_core.documents import Document
        from src.retrieval.reranker import rerank_documents
        docs = [
            Document(
                page_content=f"Document about climate risk number {i}.",
                metadata={"source": f"doc_{i}"},
            )
            for i in range(8)
        ]
        result = rerank_documents("climate risk preparedness", docs, top_n=3)
        assert len(result) == 3

    def test_rerank_scores_in_metadata(self):
        """Reranked documents should have rerank_score in metadata."""
        from langchain_core.documents import Document
        from src.retrieval.reranker import rerank_documents
        docs = [
            Document(
                page_content=f"Flood preparedness tip number {i}. "
                             "Store water and emergency supplies.",
                metadata={"source": f"doc_{i}"},
            )
            for i in range(5)
        ]
        result = rerank_documents("flood preparedness tips", docs, top_n=3)
        for doc in result:
            assert "rerank_score" in doc.metadata
            assert isinstance(doc.metadata["rerank_score"], float)


# ============================================================
# Utility Tests
# ============================================================

class TestHelpers:
    """Test shared utility functions."""

    def test_truncate_text_short(self):
        """Short text should not be modified."""
        from src.utils.helpers import truncate_text
        assert truncate_text("Hello world.", max_chars=100) == "Hello world."

    def test_truncate_text_long(self):
        """Long text should be truncated and end with ellipsis."""
        from src.utils.helpers import truncate_text
        text = "A" * 1000
        result = truncate_text(text, max_chars=200)
        assert len(result) <= 204   # 200 + len("…")
        assert result.endswith("…")

    def test_sanitize_query_strips_whitespace(self):
        """sanitize_query should normalize spaces."""
        from src.utils.helpers import sanitize_query
        assert sanitize_query("  flood   tips  ") == "flood tips"

    def test_sanitize_query_caps_length(self):
        """sanitize_query should cap at 1000 chars."""
        from src.utils.helpers import sanitize_query
        long_query = "flood " * 300  # > 1000 chars
        assert len(sanitize_query(long_query)) <= 1000

    def test_hazard_emoji_known(self):
        """Known hazards should return a non-empty emoji."""
        from src.utils.helpers import hazard_emoji
        for h in ["flood", "cyclone", "heatwave", "earthquake", "drought"]:
            emoji = hazard_emoji(h)
            assert emoji and len(emoji) > 0

    def test_hazard_emoji_unknown_fallback(self):
        """Unknown hazard type falls back to the globe emoji."""
        from src.utils.helpers import hazard_emoji
        assert hazard_emoji("volcano") == "🌍"

    def test_compute_file_hash_deterministic(self, tmp_path):
        """Same file content should always produce the same hash."""
        from src.utils.helpers import compute_file_hash
        test_file = tmp_path / "test.txt"
        test_file.write_bytes(b"climate risk content")
        h1 = compute_file_hash(test_file)
        h2 = compute_file_hash(test_file)
        assert h1 == h2
        assert len(h1) == 64  # SHA-256 hex digest

    def test_hash_registry_round_trip(self, tmp_path):
        """Hash registry should persist and reload correctly."""
        from src.utils.helpers import save_processed_hashes, load_processed_hashes
        registry_path = tmp_path / "hashes.json"
        data = {"flood_guide.pdf": "abc123", "heat_advisory.pdf": "def456"}
        save_processed_hashes(registry_path, data)
        loaded = load_processed_hashes(registry_path)
        assert loaded == data

    def test_load_hashes_missing_file(self, tmp_path):
        """Loading a non-existent hash file should return empty dict."""
        from src.utils.helpers import load_processed_hashes
        result = load_processed_hashes(tmp_path / "nonexistent.json")
        assert result == {}

    def test_elapsed_time_str_format(self):
        """Elapsed time string should end with 's'."""
        import time
        from src.utils.helpers import elapsed_time_str
        t0 = time.time() - 2.5
        result = elapsed_time_str(t0)
        assert result.endswith("s")
        assert float(result[:-1]) >= 2.0


# ============================================================
# Evaluation Tests
# ============================================================

class TestEvaluation:
    """Test RAGAS evaluation utilities."""

    def test_prepare_eval_dataset_structure(self):
        """Prepared dataset should have correct schema."""
        from langchain_core.documents import Document
        from src.evaluation.ragas_eval import prepare_eval_dataset

        pipeline_outputs = [
            {
                "query": "What to do during a flood?",
                "answer": "Move to higher ground immediately.",
                "retrieved_docs": [
                    Document(
                        page_content="During a flood, move to elevated areas.",
                        metadata={"source": "flood_guide", "page": 1},
                    )
                ],
            }
        ]

        dataset = prepare_eval_dataset(pipeline_outputs, ["Move to higher ground."])
        assert "question" in dataset.column_names
        assert "answer" in dataset.column_names
        assert "contexts" in dataset.column_names
        assert "ground_truth" in dataset.column_names
        assert len(dataset) == 1

    def test_format_scores_no_data(self):
        """Empty scores dict should return a warning message."""
        from src.evaluation.ragas_eval import format_scores_for_display
        result = format_scores_for_display({})
        assert "No evaluation scores available" in result

    def test_format_scores_with_data(self):
        """Score dict should render as a markdown table."""
        from src.evaluation.ragas_eval import format_scores_for_display
        scores = {
            "faithfulness": 0.85,
            "answer_relevancy": 0.91,
            "context_precision": 0.78,
        }
        result = format_scores_for_display(scores)
        assert "faithfulness" in result.lower() or "Faithfulness" in result
        assert "0.850" in result
        assert "|" in result   # Markdown table formatting

    def test_score_rating_excellent(self):
        """Score >= 0.85 should be rated Excellent."""
        from src.evaluation.ragas_eval import _score_rating
        assert "Excellent" in _score_rating(0.90)
        assert "Excellent" in _score_rating(0.85)

    def test_score_rating_needs_improvement(self):
        """Score < 0.55 should be rated Needs Improvement."""
        from src.evaluation.ragas_eval import _score_rating
        assert "Needs Improvement" in _score_rating(0.40)
        assert "Needs Improvement" in _score_rating(0.54)


# ============================================================
# Integration Test (mocked LLM)
# ============================================================

class TestRAGPipelineIntegration:
    """
    Integration tests for the full RAG pipeline.
    LLM calls are mocked to avoid API costs in CI.
    """

    @patch("src.rag.pipeline._get_llm")
    @patch("src.retrieval.retriever.retrieve_text_chunks")
    @patch("src.retrieval.retriever.retrieve_similar_images")
    @patch("src.retrieval.reranker.rerank_documents")
    def test_pipeline_run_returns_expected_keys(
        self,
        mock_rerank,
        mock_images,
        mock_text,
        mock_llm,
    ):
        """
        Full pipeline.run() should return a dict with all required keys.
        """
        from langchain_core.documents import Document
        from src.rag.pipeline import RAGPipeline

        # Set up mocks
        mock_doc = Document(
            page_content="During a flood, evacuate immediately to higher ground.",
            metadata={"source": "flood_guide", "page": 1, "hazard": "flood"},
        )
        mock_text.return_value = [mock_doc]
        mock_rerank.return_value = [mock_doc]
        mock_images.return_value = []

        # Mock LLM chain invocation
        mock_chain = MagicMock()
        mock_chain.invoke.return_value = (
            "## 🔴 BEFORE\n- Store water supplies.\n\n"
            "## 🟡 DURING\n- Evacuate to higher ground.\n\n"
            "## 🟢 AFTER\n- Check for structural damage.\n\n"
            "## 🏥 HEALTH & SAFETY\n- Avoid floodwater contact.\n\n"
            "## 📚 Sources\n- flood_guide, page 1"
        )
        mock_llm.return_value = MagicMock()

        pipeline = RAGPipeline()
        # Directly mock the chain building
        with patch.object(pipeline, "_build_chain", return_value=mock_chain):
            result = pipeline.run("How do I prepare for a flood?")

        # Validate output structure
        expected_keys = {
            "answer", "sources", "risk_context",
            "retrieved_docs", "image_results", "query",
        }
        assert expected_keys.issubset(result.keys())
        assert isinstance(result["answer"], str)
        assert isinstance(result["sources"], list)
        assert isinstance(result["risk_context"], dict)

    @patch("src.rag.pipeline._get_llm")
    @patch("src.retrieval.retriever.retrieve_text_chunks")
    @patch("src.retrieval.retriever.retrieve_similar_images")
    @patch("src.retrieval.reranker.rerank_documents")
    def test_pipeline_risk_context_populated(
        self,
        mock_rerank,
        mock_images,
        mock_text,
        mock_llm,
    ):
        """risk_context in output should identify the correct hazard."""
        from langchain_core.documents import Document
        from src.rag.pipeline import RAGPipeline

        mock_doc = Document(
            page_content="Cyclone safety guide.",
            metadata={"source": "cyclone_guide", "page": 2, "hazard": "cyclone"},
        )
        mock_text.return_value = [mock_doc]
        mock_rerank.return_value = [mock_doc]
        mock_images.return_value = []

        mock_chain = MagicMock()
        mock_chain.invoke.return_value = "Cyclone preparedness response."

        pipeline = RAGPipeline()
        with patch.object(pipeline, "_build_chain", return_value=mock_chain):
            result = pipeline.run("How to prepare for a cyclone?")

        assert result["risk_context"]["hazard"] == "cyclone"
