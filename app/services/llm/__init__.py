"""
LLM Service Module

Provides AI-powered article processing:
- Relevance gate
- Summarization
- Sentiment classification
"""

from app.services.llm.ai_service import (
    LLMService,
    RelevanceResult,
    SentimentResult,
    get_llm_service,
)

__all__ = [
    "LLMService",
    "RelevanceResult",
    "SentimentResult",
    "get_llm_service",
]
