# ============================================================
# src/agents/risk_agent.py
# Risk Agent for detecting hazard type from user queries.
#
# Two-stage classification:
#   Stage 1: Fast rule-based keyword matching (no API call)
#   Stage 2: LLM-based classification for ambiguous queries
#
# Returns a structured RiskContext with hazard type, confidence,
# query intent, and whether structured output is needed.
# ============================================================

import re
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional

from langchain_groq import ChatGroq
from langchain_core.messages import HumanMessage, SystemMessage
from loguru import logger

from src.config.settings import settings


# ── Enums and constants ───────────────────────────────────────

class HazardType(str, Enum):
    FLOOD = "flood"
    CYCLONE = "cyclone"
    HEATWAVE = "heatwave"
    EARTHQUAKE = "earthquake"
    DROUGHT = "drought"
    GENERAL = "general"


class QueryIntent(str, Enum):
    PREPAREDNESS = "preparedness"   # Before/During/After structured response
    INFORMATION = "information"     # General information request
    EMERGENCY = "emergency"         # Immediate action needed


# Keyword → hazard mappings for rule-based detection
_HAZARD_KEYWORD_MAP: dict[str, HazardType] = {
    # Flood
    "flood": HazardType.FLOOD,
    "flooding": HazardType.FLOOD,
    "inundation": HazardType.FLOOD,
    "flash flood": HazardType.FLOOD,
    "waterlogging": HazardType.FLOOD,
    "river overflow": HazardType.FLOOD,
    # Cyclone
    "cyclone": HazardType.CYCLONE,
    "hurricane": HazardType.CYCLONE,
    "typhoon": HazardType.CYCLONE,
    "storm surge": HazardType.CYCLONE,
    "tropical storm": HazardType.CYCLONE,
    "windstorm": HazardType.CYCLONE,
    # Heatwave
    "heatwave": HazardType.HEATWAVE,
    "heat wave": HazardType.HEATWAVE,
    "extreme heat": HazardType.HEATWAVE,
    "heat stress": HazardType.HEATWAVE,
    "heat stroke": HazardType.HEATWAVE,
    "hyperthermia": HazardType.HEATWAVE,
    # Earthquake
    "earthquake": HazardType.EARTHQUAKE,
    "seismic": HazardType.EARTHQUAKE,
    "tremor": HazardType.EARTHQUAKE,
    "aftershock": HazardType.EARTHQUAKE,
    "fault line": HazardType.EARTHQUAKE,
    "richter": HazardType.EARTHQUAKE,
    # Drought
    "drought": HazardType.DROUGHT,
    "water scarcity": HazardType.DROUGHT,
    "dry spell": HazardType.DROUGHT,
    "water shortage": HazardType.DROUGHT,
    "crop failure": HazardType.DROUGHT,
}

# Keywords that signal a preparedness intent
_PREPAREDNESS_KEYWORDS = {
    "prepare", "preparedness", "how to prepare", "what to do",
    "before", "during", "after", "survive", "survival",
    "emergency kit", "evacuation", "safety tips", "precautions",
    "protect", "protect yourself", "steps", "checklist",
    "plan", "get ready", "be ready", "action plan",
}

# Keywords signaling emergency / immediate need
_EMERGENCY_KEYWORDS = {
    "help", "emergency", "right now", "immediate", "urgent",
    "currently happening", "sos", "danger",
}

# Keywords that strictly signal an information intent (overriding others)
_INFORMATION_KEYWORDS = {
    "contact", "number", "helpline", "what is", "what are",
    "explain", "tell me about", "cause", "definition", "fact",
    "government", "agency", "organization", "department",
}


# ── Data structures ───────────────────────────────────────────

@dataclass
class RiskContext:
    """
    Structured output from the Risk Agent.
    Passed downstream to retrieval and generation stages.
    """
    hazard: HazardType = HazardType.GENERAL
    confidence: float = 0.0                    # 0.0 – 1.0
    intent: QueryIntent = QueryIntent.INFORMATION
    needs_structured_output: bool = False      # Whether to use Before/During/After format
    raw_query: str = ""
    detected_keywords: list[str] = field(default_factory=list)
    expanded_keywords: list[str] = field(default_factory=list)
    classification_method: str = "rule-based"  # "rule-based" | "llm"

    def to_dict(self) -> dict:
        return {
            "hazard": self.hazard.value,
            "confidence": self.confidence,
            "intent": self.intent.value,
            "needs_structured_output": self.needs_structured_output,
            "raw_query": self.raw_query,
            "detected_keywords": self.detected_keywords,
            "expanded_keywords": self.expanded_keywords,
            "classification_method": self.classification_method,
        }


# ── Fast rule-based intent classifier ─────────────────────────

def _fast_classify_intent(query: str) -> QueryIntent | None:
    """
    Rule-based fast-path for obvious intent classification.
    Returns None if the query is ambiguous and needs LLM.
    """
    lower = query.lower()

    # Information — overrides like "emergency contacts" or "what is"
    for kw in _INFORMATION_KEYWORDS:
        if kw in lower:
            return QueryIntent.INFORMATION

    # Emergency — highest priority for actual danger
    for kw in _EMERGENCY_KEYWORDS:
        if kw in lower:
            return QueryIntent.EMERGENCY

    # Preparedness — any phrasing about actions / steps / safety
    for kw in _PREPAREDNESS_KEYWORDS:
        if kw in lower:
            return QueryIntent.PREPAREDNESS

    return None  # Ambiguous — defer to LLM


def _fast_classify_hazard(query: str) -> HazardType:
    """
    Rule-based hazard detection using keyword map.
    """
    lower = query.lower()
    for keyword, hazard in _HAZARD_KEYWORD_MAP.items():
        if keyword in lower:
            return hazard
    return HazardType.GENERAL


# ── LLM-based fallback classifier ─────────────────────────────

def _llm_analyze_query(query: str) -> tuple[HazardType, QueryIntent, float, list[str]]:
    """
    Use LLaMA via Groq to classify ambiguous queries.
    Only called when rule-based classification is uncertain.
    """
    try:
        llm = ChatGroq(
            groq_api_key=settings.groq_api_key,
            model_name=settings.llm_model_name,
            temperature=0.0,
            max_tokens=60,
        )

        system_prompt = (
            "You are a climate disaster query classifier. Respond with EXACTLY ONE line:\n"
            "HAZARD|INTENT|keyword1, keyword2\n\n"
            "HAZARD: flood, cyclone, heatwave, earthquake, drought, general\n"
            "INTENT: preparedness, information, emergency\n\n"
            "INTENT rules:\n"
            "- information = Questions about contact numbers, helplines, government bodies, "
            "agencies, causes, definitions, facts. Any 'what is', 'what are', 'explain', "
            "or general emergency contact queries.\n"
            "- preparedness = ONLY for 'what should I do', 'how to prepare', 'steps to', "
            "'checklist', 'how do I survive', 'evacuation', 'before/during/after' regarding a specific hazard.\n"
            "- emergency = user is in active danger RIGHT NOW.\n\n"
            "Output ONLY the classification line. No explanation."
        )

        messages = [
            SystemMessage(content=system_prompt),
            HumanMessage(content=query),
        ]

        response = llm.invoke(messages)
        first_line = response.content.strip().split("\n")[0].strip().lower()

        parts = [p.strip() for p in first_line.split("|")]
        raw_hazard = parts[0] if len(parts) > 0 else "general"
        raw_intent = parts[1] if len(parts) > 1 else "information"
        kw_str = parts[2] if len(parts) > 2 else ""

        keywords = [k.strip() for k in kw_str.split(",") if k.strip()][:3]

        hazard_map = {h.value: h for h in HazardType}
        hazard = hazard_map.get(raw_hazard, HazardType.GENERAL)

        intent_map = {i.value: i for i in QueryIntent}
        intent = intent_map.get(raw_intent, QueryIntent.INFORMATION)

        logger.info(
            f"[RiskAgent] LLM classified hazard='{hazard.value}', intent='{intent.value}', "
            f"keywords={keywords} for query: '{query[:60]}'"
        )
        return hazard, intent, 0.90, keywords

    except Exception as exc:
        logger.error(f"[RiskAgent] LLM classification failed: {exc}")
        return HazardType.GENERAL, QueryIntent.INFORMATION, 0.0, []


# ── Main Risk Agent ───────────────────────────────────────────

class RiskAgent:
    """
    Orchestrates hazard and intent detection for incoming user queries.
    """

    def analyze(self, query: str) -> RiskContext:
        """
        Analyze a user query and return a structured RiskContext.

        Strategy:
          1. Fast rule-based hazard detection (always)
          2. Fast rule-based intent detection (for obvious queries)
          3. LLM fallback only for ambiguous intent
        """
        logger.info(f"[RiskAgent] Analyzing query: '{query[:80]}'")

        # ── Stage 1: Fast hazard detection (rule-based) ───────
        hazard = _fast_classify_hazard(query)

        # ── Stage 2: Fast intent detection (rule-based) ───────
        fast_intent = _fast_classify_intent(query)
        expanded_keywords = []
        classification_method = "rule-based"

        if fast_intent is not None:
            # Rule-based caught it — skip LLM call entirely
            intent = fast_intent
            confidence = 0.95
            logger.info(
                f"[RiskAgent] Rule-based: hazard={hazard.value}, intent={intent.value}"
            )
        else:
            # Ambiguous — ask LLM
            llm_hazard, intent, confidence, expanded_keywords = _llm_analyze_query(query)
            # LLM may provide a more specific hazard
            if hazard == HazardType.GENERAL and llm_hazard != HazardType.GENERAL:
                hazard = llm_hazard
            classification_method = "llm"

        needs_structured = intent in (
            QueryIntent.PREPAREDNESS,
            QueryIntent.EMERGENCY,
        )

        context = RiskContext(
            hazard=hazard,
            confidence=confidence,
            intent=intent,
            needs_structured_output=needs_structured,
            raw_query=query,
            detected_keywords=[],
            expanded_keywords=expanded_keywords,
            classification_method=classification_method,
        )

        logger.info(
            f"[RiskAgent] Result -> hazard={hazard.value}, "
            f"confidence={confidence:.2f}, intent={intent.value}, "
            f"structured={needs_structured}, method={classification_method}"
        )
        return context


# ── Singleton ─────────────────────────────────────────────────
risk_agent = RiskAgent()
