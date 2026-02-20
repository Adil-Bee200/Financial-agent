"""
LLM Service for Financial Article Processing

This service handles:
1. Relevance Gate => Determines if an article is relevant to tracked tickers
2. Summarization => Creates concise summaries of articles
3. Sentiment Classification => Analyzes sentiment and returns a score
"""

import logging
import json
from typing import List, Optional
from app.schemas.schemas_v1 import RelevanceResult, SentimentResult

from app.core.config import settings

logger = logging.getLogger(__name__)

try:
    from openai import OpenAI, OpenAIError
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False
    logger.warning("OpenAI library not installed. Install with: pip install openai")

# Maximum length of article content to process 
MAX_CONTENT_LENGTH = 2000


class LLMService:
    """
    Service for interacting with OpenAI API for article processing.
    """
    
    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize the LLM service.
        
        Args:
            api_key: OpenAI API key. If None, uses OPENAI_API_KEY from settings.
        """
        self.api_key = api_key or settings.OPENAI_API_KEY
        
        if not self.api_key:
            raise ValueError("OpenAI API key is required. Set OPENAI_API_KEY in .env")
        
        if not OPENAI_AVAILABLE:
            raise ImportError("OpenAI library not installed. Install with: pip install openai")
        
        self.client = OpenAI(api_key=self.api_key)
        self.model = "gpt-4o-mini"  # Cost-effective model
        self.timeout = 30  # seconds
        
        logger.info(f"LLM Service initialized with model: {self.model}")
    
    def check_relevance(self, article_title: str, article_content: str, tracked_tickers: List[str]) -> RelevanceResult:
        """
        Check if an article is relevant to any of the tracked tickers.
        
        This is the "relevance gate" => filters articles before processing.
        
        Args:
            article_title: Article title
            article_content: Article content/text (can be truncated)
            tracked_tickers: List of ticker symbols to check against (e.g., ["NVDA", "AAPL"])
        
        Returns:
            RelevanceResult with relevant flag, companies mentioned, and confidence
        """
        if not tracked_tickers:
            return RelevanceResult(relevant=False, companies=[], confidence=0.0)
        
        tickers_str = ", ".join(tracked_tickers)
        
        # Truncate content if too long (to save tokens)
        max_content_length = MAX_CONTENT_LENGTH
        if len(article_content) > max_content_length:
            article_content = article_content[:max_content_length] + "..."
        
        prompt = f"""You are a financial news analyzer. Determine if this article is relevant to any of these stock tickers: {tickers_str}

Article Title: {article_title}

Article Content:
{article_content}

Respond with a JSON object containing:
- "relevant": true or false
- "companies": array of ticker symbols mentioned (e.g., ["NVDA"])
- "confidence": float between 0.0 and 1.0

Only include tickers that are actually mentioned or clearly referenced in the article.
Be strict, only mark as relevant if there's a clear connection to the tracked tickers."""

        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": "You are a financial news analyzer. Always respond with valid JSON only."
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                response_format={"type": "json_object"},
                temperature=0.1,  # Low temperature for consistent results
                timeout=self.timeout
            )
            
            result_text = response.choices[0].message.content
            result = json.loads(result_text)
            
            return RelevanceResult(relevant=result.get("relevant", False), companies=result.get("companies", []), confidence=result.get("confidence", 0.0))
            
        except OpenAIError as e:
            logger.error(f"OpenAI API error in relevance check: {e}")
            # Assume relevant if API fails (can be processed later)
            return RelevanceResult(relevant=True, companies=[], confidence=0.5)
        except Exception as e:
            logger.error(f"Error in relevance check: {e}")
            return RelevanceResult(relevant=True, companies=[], confidence=0.5)
    
    def summarize_article(self, article_title: str, article_content: str, max_length: int = 200) -> str:
        """
        Generate a concise summary of an article.
        
        Args:
            article_title: Article title
            article_content: Full article content
            max_length: Maximum length of summary in characters
        
        Returns:
            Summary string
        """
        # Truncate content if too long
        max_content_length = MAX_CONTENT_LENGTH
        if len(article_content) > max_content_length:
            article_content = article_content[:max_content_length] + "..."
        
        prompt = f"""Summarize this financial news article in {max_length} characters or less.
Focus on key financial implications, company performance, market impact, and important numbers.

Title: {article_title}

Content:
{article_content}

Provide a concise summary:"""

        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": "You are a financial news summarizer. Create concise, informative summaries."
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                temperature=0.3,
                timeout=self.timeout
            )
            
            summary = response.choices[0].message.content.strip()
            
            # Ensure summary doesn't exceed max_length
            if len(summary) > max_length:
                summary = summary[:max_length].rsplit(' ', 1)[0] + "..."
            
            return summary
            
        except OpenAIError as e:
            logger.error(f"OpenAI API error in summarization: {e}")
            # Fallback: return truncated content
            return article_content[:max_length] + "..." if len(article_content) > max_length else article_content
        except Exception as e:
            logger.error(f"Error in summarization: {e}")
            return article_content[:max_length] + "..." if len(article_content) > max_length else article_content
    
    def classify_sentiment(self, article_title: str, article_content: str) -> SentimentResult:
        """
        Classify the sentiment of an article.
        
        Returns a sentiment score from -1.0 (very negative) to 1.0 (very positive).
        
        Args:
            article_title: Article title
            article_content: Article content/text
        
        Returns:
            SentimentResult with score, label, and confidence
        """
        # Truncate content if too long
        max_content_length = MAX_CONTENT_LENGTH
        if len(article_content) > max_content_length:
            article_content = article_content[:max_content_length] + "..."
        
        prompt = f"""Analyze the sentiment of this financial news article.
Consider: stock price impact, company performance outlook, market sentiment, investor confidence.

Title: {article_title}

Content:
{article_content}

Respond with a JSON object containing:
- "sentiment_score": float between -1.0 (very negative) and 1.0 (very positive)
- "sentiment_label": "positive", "negative", or "neutral"
- "confidence": float between 0.0 and 1.0

Examples:
- Very negative news (scandal, major loss): -0.8 to -1.0
- Negative news (missed earnings, downgrade): -0.3 to -0.7
- Neutral news (routine updates): -0.2 to 0.2
- Positive news (beat earnings, upgrade): 0.3 to 0.7
- Very positive news (major win, acquisition): 0.8 to 1.0"""

        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": "You are a financial sentiment analyzer. Always respond with valid JSON only."
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                response_format={"type": "json_object"},
                temperature=0.2,  # Low temperature for consistent sentiment analysis
                timeout=self.timeout
            )
            
            result_text = response.choices[0].message.content
            result = json.loads(result_text)
            
            return SentimentResult(
                sentiment_score=float(result.get("sentiment_score", 0.0)),
                sentiment_label=result.get("sentiment_label", "neutral"),
                confidence=float(result.get("confidence", 0.5))
            )
            
        except OpenAIError as e:
            logger.error(f"OpenAI API error in sentiment classification: {e}")
            # Return neutral sentiment on error
            return SentimentResult(sentiment_score=0.0, sentiment_label="neutral", confidence=0.0)
        except Exception as e:
            logger.error(f"Error in sentiment classification: {e}")
            return SentimentResult(sentiment_score=0.0, sentiment_label="neutral", confidence=0.0)


# Singleton instance (can be initialized later)
_llm_service_instance: Optional[LLMService] = None


def get_llm_service() -> LLMService:
    """
    Get or create the singleton LLM service instance.
    
    Returns:
        LLMService instance
    """
    global _llm_service_instance
    if _llm_service_instance is None:
        _llm_service_instance = LLMService()
    return _llm_service_instance
