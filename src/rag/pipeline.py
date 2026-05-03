# ============================================================
# src/rag/pipeline.py
# Full RAG pipeline using LangChain LCEL (LangChain Expression
# Language) chains.
#
# Flow:
#   User query
#     → RiskAgent (hazard detection + intent classification)
#     → Retriever  (vector similarity search, metadata filtered)
#     → Reranker   (cross-encoder scoring)
#     → Prompt     (structured or freeform based on intent)
#     → LLM        (Groq LLaMA 3.1)
#     → Output     (structured dict + source citations)
# ============================================================

from typing import Any

from langchain_core.documents import Document
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import RunnablePassthrough, RunnableLambda
from langchain_groq import ChatGroq
from loguru import logger
from tenacity import retry, stop_after_attempt, wait_exponential

from src.agents.risk_agent import risk_agent, RiskContext, QueryIntent
from src.config.settings import settings
from src.retrieval.retriever import retrieve_text_chunks, retrieve_similar_images
from src.retrieval.reranker import rerank_documents


# ── Prompt templates ──────────────────────────────────────────

# Template for preparedness-related queries (structured output)
PREPAREDNESS_SYSTEM_PROMPT = """\
You are an expert Climate Risk Preparedness Advisor. Your role is to provide \
accurate, actionable, and grounded guidance.

CRITICAL RULES:
- Prioritize using the provided context documents for your answer.
- If the context lacks information to fully answer the question, you MUST use your own expert general knowledge to provide helpful, life-saving advice.
- Do not say "This information is not available". Instead, provide the best known general preparedness advice.
- Be specific, practical, and prioritize life-safety information.
- Be concise. Start directly with the answer. No introductory filler, no closing summary. Stop when the information is complete.
- MATCH LENGTH TO QUESTION COMPLEXITY: Keep items concise, no fluff. Never pad answers with background context or summarizing conclusions.
- CUT FILLER: No opening filler lines, no closing summary paragraphs.

Context Documents:
{context}

Hazard Type: {hazard}
"""

PREPAREDNESS_HUMAN_PROMPT = """\
Question: {question}

You MUST organize your response using ALL of these exact markdown headers, in this exact order:

## 🔴 Before
(List preparedness steps to take BEFORE the disaster strikes)

## 🟡 During
(List survival actions to take DURING the active emergency)

## 🟢 After
(List recovery steps to take AFTER the disaster has passed)

## 🏥 Health Safety
(List health precautions, symptoms to watch for, and when to seek medical help)

FORMATTING RULES:
- Every section MUST be present even if the user only asked about one phase. Provide at least 2 items per section.
- Use bullet points (- ) for each action item. Do NOT use numbered lists.
- Keep items concise and actionable — one clear instruction per bullet.
- Do NOT include any text before the first ## header.
- Do NOT add a Sources section — sources are handled separately.
"""

# Template for general information queries (freeform output)
GENERAL_SYSTEM_PROMPT = """\
You are an expert Climate Risk Preparedness Advisor. Provide clear, accurate \
information to the user.

CRITICAL RULES:
- Prioritize your answer based on the provided context documents.
- If the specific answer is not in the context, use your general expert knowledge to answer the question helpfully.
- Never say "This is not in the context". Just answer the question as an expert.
- Cite specific documents when you use information from the context.
- Be concise. Start directly with the answer. No introductory filler, no closing summary. Stop when the information is complete.
- MATCH LENGTH TO QUESTION COMPLEXITY: Simple questions → 2-3 short paragraphs MAX or 4-6 bullets. Detailed questions → can be longer but still concise. Never pad answers.
- CUT FILLER: Never use opening filler lines (e.g., "When it comes to..."). Never use closing summary paragraphs (e.g., "Overall..."). No background/historical context unless directly asked.
- FOR CONTACT QUESTIONS: Give actual numbers and names directly. Do not explain how the contact system is organized.

Context Documents:
{context}

Hazard Type: {hazard}
"""

GENERAL_HUMAN_PROMPT = """\
Question: {question}

Provide a natural, conversational, and informative answer based on the context. \
Explain concepts clearly as if you are a helpful ChatGPT-like assistant. \
Do NOT use the Before/During/After template format. \
Include relevant facts, explanations, and practical insights.
"""


# ── LLM factory ──────────────────────────────────────────────

def _get_llm() -> ChatGroq:
    """Create and return a Groq LLaMA 3.1 LLM instance."""
    return ChatGroq(
        groq_api_key=settings.groq_api_key,
        model_name=settings.llm_model_name,
        temperature=settings.llm_temperature,
        max_tokens=settings.llm_max_tokens,
    )


# ── Context formatting ────────────────────────────────────────

def _format_context(documents: list[Document]) -> str:
    """
    Format retrieved documents into a numbered context string
    for insertion into the LLM prompt.

    Args:
        documents: Reranked LangChain Documents.

    Returns:
        Formatted context string with source citations.
    """
    if not documents:
        return "No relevant context found in the knowledge base."

    formatted_parts = []
    for idx, doc in enumerate(documents, start=1):
        source = doc.metadata.get("source", "Unknown Source")
        page = doc.metadata.get("page", "?")
        hazard = doc.metadata.get("hazard", "general")

        formatted_parts.append(
            f"[Document {idx}] "
            f"Source: {source} | Page: {page} | Hazard: {hazard}\n"
            f"{doc.page_content}"
        )

    return "\n\n---\n\n".join(formatted_parts)


def _format_sources(documents: list[Document]) -> list[dict]:
    """
    Extract clean source citation dicts from retrieved documents.

    Returns:
        List of source metadata dicts (deduplicated by source+page).
    """
    seen = set()
    sources = []

    for doc in documents:
        source = doc.metadata.get("source", "Unknown")
        page = doc.metadata.get("page", "?")
        hazard = doc.metadata.get("hazard", "general")
        key = f"{source}_p{page}"

        if key not in seen:
            seen.add(key)
            sources.append(
                {
                    "source": source,
                    "page": page,
                    "hazard": hazard,
                    "rerank_score": doc.metadata.get("rerank_score", None),
                }
            )

    return sources


# ── RAG Pipeline ──────────────────────────────────────────────

class RAGPipeline:
    """
    End-to-end Retrieval-Augmented Generation pipeline.

    Orchestrates: RiskAgent → Retrieval → Reranking → Generation.
    Returns structured output with answer, sources, and risk context.
    """

    def __init__(self):
        self.llm = _get_llm()
        self.output_parser = StrOutputParser()

    def _build_chain(self, needs_structured: bool):
        """
        Build the appropriate LCEL chain based on query intent.

        Args:
            needs_structured: If True, use preparedness prompt template.

        Returns:
            LCEL chain (prompt | llm | parser).
        """
        if needs_structured:
            prompt = ChatPromptTemplate.from_messages(
                [
                    ("system", PREPAREDNESS_SYSTEM_PROMPT),
                    ("human", PREPAREDNESS_HUMAN_PROMPT),
                ]
            )
        else:
            prompt = ChatPromptTemplate.from_messages(
                [
                    ("system", GENERAL_SYSTEM_PROMPT),
                    ("human", GENERAL_HUMAN_PROMPT),
                ]
            )

        return prompt | self.llm | self.output_parser

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        reraise=True,
    )
    def run(self, query: str) -> dict[str, Any]:
        """
        Execute the full RAG pipeline for a user query.

        Steps:
            1. RiskAgent classifies hazard type and intent
            2. Retrieve top-k text chunks (with hazard filter)
            3. Rerank chunks with cross-encoder
            4. Format context and invoke LLM
            5. Return structured response dict

        Args:
            query: Raw user question.

        Returns:
            Dict with keys:
                - answer:         LLM-generated response string
                - sources:        List of source citation dicts
                - risk_context:   RiskContext.to_dict()
                - retrieved_docs: Raw Document objects (for evaluation)
                - image_results:  Relevant image hits (CLIP retrieval)
                - query:          Original query
        """
        logger.info(f"[RAGPipeline] Processing query: '{query[:80]}…'")

        # ── Step 1: Risk Analysis ────────────────────────────
        risk_ctx: RiskContext = risk_agent.analyze(query)

        # ── Step 2: Text Retrieval ───────────────────────────
        search_query = query
        if risk_ctx.expanded_keywords:
            search_query += " " + " ".join(risk_ctx.expanded_keywords)
            logger.info(f"[RAGPipeline] Enhanced retrieval query: '{search_query[:80]}'")

        raw_docs = retrieve_text_chunks(
            query=search_query,
            hazard_filter=risk_ctx.hazard.value,
            top_k=settings.retrieval_top_k,
        )

        # ── Step 3: Reranking ────────────────────────────────
        reranked_docs = rerank_documents(
            query=query,
            documents=raw_docs,
            top_n=settings.rerank_top_n,
        )

        # ── Step 4: Image Retrieval (multimodal) ─────────────
        # Only use CLIP if the user specifically asks for visual information
        # to save memory and stay text-based by default.
        image_keywords = ["map", "picture", "photo", "image", "diagram", "show", "visual"]
        needs_images = any(kw in query.lower() for kw in image_keywords)
        
        image_results = []
        if needs_images:
            logger.info("[RAGPipeline] Visual query detected. Lazy-loading CLIP for image retrieval...")
            image_results = retrieve_similar_images(
                query=query,
                hazard_filter=risk_ctx.hazard.value,
                top_k=2,
            )
        else:
            logger.info("[RAGPipeline] Text-only query. Skipping CLIP image retrieval.")

        # ── Step 5: Generate Response ────────────────────────
        context_str = _format_context(reranked_docs)
        sources = _format_sources(reranked_docs)

        chain = self._build_chain(
            needs_structured=risk_ctx.needs_structured_output
        )

        try:
            answer = chain.invoke(
                {
                    "context": context_str,
                    "hazard": risk_ctx.hazard.value,
                    "question": query,
                }
            )
        except Exception as exc:
            logger.error(f"[RAGPipeline] LLM generation failed: {exc}")
            answer = (
                "I apologize, but I was unable to generate a response. "
                "Please check your API key and try again."
            )

        logger.info("[RAGPipeline] Response generated successfully.")

        return {
            "answer": answer,
            "sources": sources,
            "risk_context": risk_ctx.to_dict(),
            "retrieved_docs": reranked_docs,   # kept for RAGAS evaluation
            "image_results": image_results,
            "query": query,
        }


# ── Singleton ─────────────────────────────────────────────────
rag_pipeline = RAGPipeline()
