# tests/conftest.py
# ============================================================
# Shared pytest fixtures available across all test modules.
# ============================================================

import sys
from pathlib import Path

import pytest

# Ensure project root is on sys.path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))


@pytest.fixture(scope="session")
def sample_pdf_text():
    """Return a sample multi-page text corpus for testing."""
    return [
        "Floods are among the most destructive natural disasters. "
        "Preparation includes building emergency kits and evacuation plans. "
        "Store at least three days of water per person. " * 10,

        "During a flood event, avoid walking through moving water. "
        "If evacuating, disconnect utilities at main switches. "
        "Follow official instructions from emergency services. " * 10,

        "After a flood, document damage for insurance purposes. "
        "Boil water before drinking. Watch for gas leaks. "
        "Do not return home until authorities declare it safe. " * 10,
    ]


@pytest.fixture(scope="session")
def sample_hazard_queries():
    """Return a list of test queries covering different hazard types."""
    return [
        ("How do I prepare for a flood?", "flood"),
        ("What should I do during a cyclone?", "cyclone"),
        ("Heatwave safety tips for the elderly", "heatwave"),
        ("Earthquake survival guide", "earthquake"),
        ("Drought water conservation strategies", "drought"),
        ("General climate risk information", "general"),
    ]


@pytest.fixture
def mock_langchain_document():
    """Return a single mock LangChain Document for testing."""
    from langchain_core.documents import Document
    return Document(
        page_content=(
            "During a flood, immediately move to higher ground. "
            "Do not walk through moving water. "
            "Follow evacuation orders from local authorities."
        ),
        metadata={
            "source": "flood_preparedness_guide",
            "page": 5,
            "hazard": "flood",
            "chunk_index": 0,
        },
    )


@pytest.fixture
def mock_pipeline_output(mock_langchain_document):
    """Return a mock RAG pipeline output dict."""
    return {
        "query": "What should I do during a flood?",
        "answer": (
            "## 🔴 BEFORE\n- Store emergency supplies.\n\n"
            "## 🟡 DURING\n- Move to higher ground immediately.\n\n"
            "## 🟢 AFTER\n- Check for structural damage.\n\n"
            "## 🏥 HEALTH & SAFETY\n- Avoid contact with floodwater."
        ),
        "sources": [
            {"source": "flood_preparedness_guide", "page": 5, "hazard": "flood"}
        ],
        "risk_context": {
            "hazard": "flood",
            "confidence": 0.70,
            "intent": "preparedness",
            "needs_structured_output": True,
            "raw_query": "What should I do during a flood?",
            "detected_keywords": ["flood"],
            "classification_method": "rule-based",
        },
        "retrieved_docs": [mock_langchain_document],
        "image_results": [],
    }
