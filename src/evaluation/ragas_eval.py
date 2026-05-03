# ============================================================
# src/evaluation/ragas_eval.py
# RAG evaluation using the RAGAS framework.
#
# Metrics computed:
#   - Faithfulness:       Does the answer stay grounded in context?
#   - Answer Relevance:   Is the answer relevant to the question?
#   - Context Precision:  Are the retrieved chunks precise?
#   - Context Recall:     Are all necessary facts retrieved?
#
# RAGAS operates on a Dataset of (question, answer, contexts,
# ground_truth) tuples and returns per-metric scores 0.0–1.0.
# ============================================================

import json
from datetime import datetime
from pathlib import Path
from typing import Any

import pandas as pd
from datasets import Dataset
from langchain_core.documents import Document
from langchain_groq import ChatGroq
from langchain_huggingface import HuggingFaceEmbeddings
from loguru import logger
from ragas import evaluate
from ragas.metrics import (
    faithfulness,
    answer_relevancy,
    context_precision,
    context_recall,
)

from src.config.settings import settings


# ── RAGAS metric set ──────────────────────────────────────────

RAGAS_METRICS = [
    faithfulness,         # Factual grounding in retrieved context
    answer_relevancy,     # Relevance of answer to question
    context_precision,    # Precision of retrieved context chunks
    context_recall,       # Recall of relevant context chunks
]


# ── Evaluation data preparation ───────────────────────────────

def prepare_eval_dataset(
    pipeline_outputs: list[dict[str, Any]],
    ground_truths: list[str] | None = None,
) -> Dataset:
    """
    Convert pipeline outputs into a RAGAS-compatible HuggingFace Dataset.

    Args:
        pipeline_outputs: List of dicts from RAGPipeline.run().
                          Each must have: query, answer, retrieved_docs.
        ground_truths:    Optional list of reference answers for
                          context_recall computation. If None,
                          context_recall is skipped.

    Returns:
        HuggingFace Dataset ready for RAGAS evaluation.
    """
    questions, answers, contexts_list, gt_list = [], [], [], []

    for idx, output in enumerate(pipeline_outputs):
        question = output.get("query", "")
        answer = output.get("answer", "")
        docs: list[Document] = output.get("retrieved_docs", [])

        # Extract plain text from retrieved documents
        contexts = [doc.page_content for doc in docs if doc.page_content]

        # Ground truth: use provided, or fall back to empty string
        ground_truth = (
            ground_truths[idx]
            if ground_truths and idx < len(ground_truths)
            else ""
        )

        questions.append(question)
        answers.append(answer)
        contexts_list.append(contexts)
        gt_list.append(ground_truth)

    dataset_dict = {
        "question": questions,
        "answer": answers,
        "contexts": contexts_list,
        "ground_truth": gt_list,
    }

    logger.info(
        f"[RAGAS] Prepared evaluation dataset with "
        f"{len(questions)} sample(s)."
    )

    return Dataset.from_dict(dataset_dict)


# ── Core evaluation function ──────────────────────────────────

def evaluate_rag(
    pipeline_outputs: list[dict[str, Any]],
    ground_truths: list[str] | None = None,
    save_results: bool = True,
    output_dir: Path | None = None,
) -> dict[str, float]:
    """
    Run RAGAS evaluation on a set of pipeline outputs.

    Args:
        pipeline_outputs: List of dicts from RAGPipeline.run().
        ground_truths:    Optional reference answers (improves recall score).
        save_results:     If True, save results to a JSON + CSV file.
        output_dir:       Directory to save evaluation results.
                          Defaults to project_root/evaluation_results/.

    Returns:
        Dict mapping metric name → score (0.0–1.0).
        Example: {"faithfulness": 0.87, "answer_relevancy": 0.91, ...}
    """
    if not pipeline_outputs:
        logger.warning("[RAGAS] No pipeline outputs provided for evaluation.")
        return {}

    # ── Prepare dataset ──────────────────────────────────────
    eval_dataset = prepare_eval_dataset(pipeline_outputs, ground_truths)

    # ── Configure RAGAS LLM and embeddings ───────────────────
    # RAGAS uses its own LLM instance for judge-model scoring
    ragas_llm = ChatGroq(
        groq_api_key=settings.groq_api_key,
        model_name=settings.llm_model_name,
        temperature=0.0,
    )

    ragas_embeddings = HuggingFaceEmbeddings(
        model_name=settings.text_embedding_model,
        model_kwargs={"device": "cpu"},
        encode_kwargs={"normalize_embeddings": True},
    )

    # Choose metrics: context_recall requires ground truths
    metrics = RAGAS_METRICS
    if not ground_truths or all(gt == "" for gt in (ground_truths or [])):
        logger.info(
            "[RAGAS] No ground truths provided. "
            "Skipping context_recall metric."
        )
        metrics = [faithfulness, answer_relevancy, context_precision]

    logger.info(
        f"[RAGAS] Starting evaluation with metrics: "
        f"{[m.name for m in metrics]}"
    )

    # ── Run evaluation ───────────────────────────────────────
    try:
        result = evaluate(
            dataset=eval_dataset,
            metrics=metrics,
            llm=ragas_llm,
            embeddings=ragas_embeddings,
            raise_exceptions=False,   # Log errors, don't crash
        )

        scores = dict(result)

        # Ensure all values are plain Python floats (not numpy)
        scores = {k: float(v) for k, v in scores.items() if v is not None}

        logger.info(f"[RAGAS] Evaluation complete. Scores: {scores}")

    except Exception as exc:
        import traceback
        logger.error(f"[RAGAS] Evaluation failed: {exc}")
        traceback.print_exc()
        return {}

    # ── Save results ─────────────────────────────────────────
    if save_results:
        _save_evaluation_results(scores, eval_dataset, output_dir)

    return scores


# ── Single-sample evaluation (for live UI feedback) ───────────

def evaluate_single_response(
    query: str,
    answer: str,
    retrieved_docs: list[Document],
    ground_truth: str = "",
) -> dict[str, float]:
    """
    Evaluate a single RAG response for quick feedback.
    Wraps the batch evaluation function with a single sample.

    Args:
        query:          User question.
        answer:         LLM-generated answer.
        retrieved_docs: Documents used to generate the answer.
        ground_truth:   Optional reference answer.

    Returns:
        Dict of metric scores.
    """
    pipeline_output = {
        "query": query,
        "answer": answer,
        "retrieved_docs": retrieved_docs,
    }

    return evaluate_rag(
        pipeline_outputs=[pipeline_output],
        ground_truths=[ground_truth] if ground_truth else None,
        save_results=False,
    )


# ── Results persistence ───────────────────────────────────────

def _save_evaluation_results(
    scores: dict[str, float],
    dataset: Dataset,
    output_dir: Path | None,
) -> None:
    """
    Save evaluation scores and dataset to disk as JSON and CSV.

    Args:
        scores:     Metric scores dict.
        dataset:    RAGAS evaluation dataset.
        output_dir: Target directory for output files.
    """
    output_dir = output_dir or (
        Path(__file__).resolve().parents[2] / "evaluation_results"
    )
    output_dir.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    # Save scores as JSON
    scores_path = output_dir / f"ragas_scores_{timestamp}.json"
    with open(scores_path, "w") as f:
        json.dump(
            {
                "timestamp": timestamp,
                "scores": scores,
                "sample_count": len(dataset),
            },
            f,
            indent=2,
        )

    # Save full dataset with scores as CSV
    df = dataset.to_pandas()
    csv_path = output_dir / f"ragas_dataset_{timestamp}.csv"
    df.to_csv(csv_path, index=False)

    logger.info(
        f"[RAGAS] Results saved → "
        f"Scores: {scores_path}, Dataset: {csv_path}"
    )


# ── Utility: format scores for display ───────────────────────

def format_scores_for_display(scores: dict[str, float]) -> str:
    """
    Format RAGAS scores into a human-readable markdown table.

    Args:
        scores: Dict of metric name → score.

    Returns:
        Markdown-formatted string.
    """
    if not scores:
        return "⚠️ No evaluation scores available."

    # Human-readable metric labels
    labels = {
        "faithfulness": "📌 Faithfulness",
        "answer_relevancy": "🎯 Answer Relevancy",
        "context_precision": "🔍 Context Precision",
        "context_recall": "📚 Context Recall",
    }

    rows = ["| Metric | Score | Rating |", "|--------|-------|--------|"]
    for metric, score in scores.items():
        label = labels.get(metric, metric.replace("_", " ").title())
        rating = _score_rating(score)
        rows.append(f"| {label} | {score:.3f} | {rating} |")

    return "\n".join(rows)


def _score_rating(score: float) -> str:
    """Convert a 0–1 score to a qualitative rating emoji."""
    if score >= 0.85:
        return "🟢 Excellent"
    elif score >= 0.70:
        return "🟡 Good"
    elif score >= 0.55:
        return "🟠 Fair"
    else:
        return "🔴 Needs Improvement"
