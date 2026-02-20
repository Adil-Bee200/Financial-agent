"""
Unit tests for LLM Service

Tests all three main functions:
1. Relevance Gate
2. Summarization
3. Sentiment Classification
"""
import pytest
import json
from unittest.mock import Mock, patch
from openai import OpenAIError

from app.services.llm.ai_service import LLMService, MAX_CONTENT_LENGTH
from app.schemas.schemas_v1 import RelevanceResult, SentimentResult


class TestRelevanceGate:
    """Tests for relevance gate functionality"""
    
    def test_relevance_relevant_article(self, llm_service, sample_article, sample_tickers):
        """Test that relevant articles are correctly identified"""
        # Setup mock response
        mock_response = {
            "relevant": True,
            "companies": ["NVDA"],
            "confidence": 0.91
        }
        # Create new mock response object
        mock_message = Mock()
        mock_message.content = json.dumps(mock_response)
        mock_choice = Mock()
        mock_choice.message = mock_message
        mock_response_obj = Mock()
        mock_response_obj.choices = [mock_choice]
        llm_service.client.chat.completions.create.return_value = mock_response_obj
        
        result = llm_service.check_relevance(
            article_title=sample_article["title"],
            article_content=sample_article["content"],
            tracked_tickers=sample_tickers
        )
        
        assert isinstance(result, RelevanceResult)
        assert result.relevant is True
        assert "NVDA" in result.companies
        assert result.confidence == 0.91
        assert llm_service.client.chat.completions.create.called
    
    def test_relevance_not_relevant_article(self, llm_service, sample_tickers):
        """Test that irrelevant articles are correctly identified"""
        mock_response = {
            "relevant": False,
            "companies": [],
            "confidence": 0.15
        }
        mock_message = Mock()
        mock_message.content = json.dumps(mock_response)
        mock_choice = Mock()
        mock_choice.message = mock_message
        mock_response_obj = Mock()
        mock_response_obj.choices = [mock_choice]
        llm_service.client.chat.completions.create.return_value = mock_response_obj
        
        result = llm_service.check_relevance(
            article_title="Unrelated News Article",
            article_content="This article has nothing to do with technology stocks.",
            tracked_tickers=sample_tickers
        )
        
        assert result.relevant is False
        assert len(result.companies) == 0
        assert result.confidence < 0.5
    
    def test_relevance_empty_tickers(self, llm_service, sample_article):
        """Test that empty ticker list returns not relevant"""
        result = llm_service.check_relevance(
            article_title=sample_article["title"],
            article_content=sample_article["content"],
            tracked_tickers=[]
        )
        
        assert result.relevant is False
        assert len(result.companies) == 0
        assert result.confidence == 0.0
        # Should not call API if no tickers
        assert not llm_service.client.chat.completions.create.called
    
    def test_relevance_content_truncation(self, llm_service, sample_tickers):
        """Test that long content is truncated"""
        long_content = "A" * (MAX_CONTENT_LENGTH + 1000)
        
        result = llm_service.check_relevance(
            article_title="Test",
            article_content=long_content,
            tracked_tickers=sample_tickers
        )
        
        # Verify API was called (content was processed)
        assert llm_service.client.chat.completions.create.called
        # Check that the content passed to API was truncated
        call_args = llm_service.client.chat.completions.create.call_args
        prompt = call_args[1]["messages"][1]["content"]
        assert len(prompt) < len(long_content) + 500  # Some overhead for prompt template
    
    def test_relevance_api_error_handling(self, llm_service, sample_article, sample_tickers):
        """Test error handling when API fails"""
        llm_service.client.chat.completions.create.side_effect = OpenAIError("API Error")
        
        result = llm_service.check_relevance(
            article_title=sample_article["title"],
            article_content=sample_article["content"],
            tracked_tickers=sample_tickers
        )
        
        # Should fail open (assume relevant)
        assert result.relevant is True
        assert result.confidence == 0.5
    
    def test_relevance_json_parse_error(self, llm_service, sample_article, sample_tickers):
        """Test handling of invalid JSON response"""
        mock_message = Mock()
        mock_message.content = "Invalid JSON"
        mock_choice = Mock()
        mock_choice.message = mock_message
        mock_response_obj = Mock()
        mock_response_obj.choices = [mock_choice]
        llm_service.client.chat.completions.create.return_value = mock_response_obj
        
        # Should handle gracefully
        result = llm_service.check_relevance(
            article_title=sample_article["title"],
            article_content=sample_article["content"],
            tracked_tickers=sample_tickers
        )
        
        # Should fail open
        assert result.relevant is True


class TestSummarization:
    """Tests for article summarization"""
    
    def test_summarize_article_success(self, llm_service, sample_article):
        """Test successful article summarization"""
        mock_summary = "NVIDIA unveiled a new AI chip with improved performance and energy efficiency."
        mock_message = Mock()
        mock_message.content = mock_summary
        mock_choice = Mock()
        mock_choice.message = mock_message
        mock_response_obj = Mock()
        mock_response_obj.choices = [mock_choice]
        llm_service.client.chat.completions.create.return_value = mock_response_obj
        
        result = llm_service.summarize_article(
            article_title=sample_article["title"],
            article_content=sample_article["content"]
        )
        
        assert isinstance(result, str)
        assert len(result) > 0
        assert "NVIDIA" in result or "AI" in result or "chip" in result
        assert llm_service.client.chat.completions.create.called
    
    def test_summarize_respects_max_length(self, llm_service, sample_article):
        """Test that summary respects max_length parameter"""
        mock_summary = "A" * 500  # Long summary
        mock_message = Mock()
        mock_message.content = mock_summary
        mock_choice = Mock()
        mock_choice.message = mock_message
        mock_response_obj = Mock()
        mock_response_obj.choices = [mock_choice]
        llm_service.client.chat.completions.create.return_value = mock_response_obj
        
        max_length = 100
        result = llm_service.summarize_article(
            article_title=sample_article["title"],
            article_content=sample_article["content"],
            max_length=max_length
        )
        
        assert len(result) <= max_length + 10  # Small buffer for truncation
    
    def test_summarize_content_truncation(self, llm_service):
        """Test that long article content is truncated"""
        long_content = "B" * (MAX_CONTENT_LENGTH + 2000)
        mock_message = Mock()
        mock_message.content = "Summary"
        mock_choice = Mock()
        mock_choice.message = mock_message
        mock_response_obj = Mock()
        mock_response_obj.choices = [mock_choice]
        llm_service.client.chat.completions.create.return_value = mock_response_obj
        
        result = llm_service.summarize_article(
            article_title="Test",
            article_content=long_content
        )
        
        # Verify API was called
        assert llm_service.client.chat.completions.create.called
        # Check content was truncated in the prompt
        call_args = llm_service.client.chat.completions.create.call_args
        prompt = call_args[1]["messages"][1]["content"]
        assert len(prompt) < len(long_content) + 500
    
    def test_summarize_api_error_handling(self, llm_service, sample_article):
        """Test error handling when API fails"""
        llm_service.client.chat.completions.create.side_effect = OpenAIError("API Error")
        
        result = llm_service.summarize_article(
            article_title=sample_article["title"],
            article_content=sample_article["content"]
        )
        
        # Should return truncated original content as fallback
        assert isinstance(result, str)
        assert len(result) > 0


class TestSentimentClassification:
    """Tests for sentiment classification"""
    
    def test_sentiment_positive(self, llm_service, sample_article):
        """Test positive sentiment classification"""
        mock_response = {
            "sentiment_score": 0.75,
            "sentiment_label": "positive",
            "confidence": 0.88
        }
        mock_message = Mock()
        mock_message.content = json.dumps(mock_response)
        mock_choice = Mock()
        mock_choice.message = mock_message
        mock_response_obj = Mock()
        mock_response_obj.choices = [mock_choice]
        llm_service.client.chat.completions.create.return_value = mock_response_obj
        
        result = llm_service.classify_sentiment(
            article_title=sample_article["title"],
            article_content=sample_article["content"]
        )
        
        assert isinstance(result, SentimentResult)
        assert result.sentiment_score > 0
        assert result.sentiment_label == "positive"
        assert result.confidence == 0.88
        assert llm_service.client.chat.completions.create.called
    
    def test_sentiment_negative(self, llm_service):
        """Test negative sentiment classification"""
        mock_response = {
            "sentiment_score": -0.65,
            "sentiment_label": "negative",
            "confidence": 0.82
        }
        mock_message = Mock()
        mock_message.content = json.dumps(mock_response)
        mock_choice = Mock()
        mock_choice.message = mock_message
        mock_response_obj = Mock()
        mock_response_obj.choices = [mock_choice]
        llm_service.client.chat.completions.create.return_value = mock_response_obj
        
        result = llm_service.classify_sentiment(
            article_title="Company Misses Earnings",
            article_content="The company reported disappointing quarterly results..."
        )
        
        assert result.sentiment_score < 0
        assert result.sentiment_label == "negative"
        assert result.confidence == 0.82
    
    def test_sentiment_neutral(self, llm_service):
        """Test neutral sentiment classification"""
        mock_response = {
            "sentiment_score": 0.05,
            "sentiment_label": "neutral",
            "confidence": 0.70
        }
        mock_message = Mock()
        mock_message.content = json.dumps(mock_response)
        mock_choice = Mock()
        mock_choice.message = mock_message
        mock_response_obj = Mock()
        mock_response_obj.choices = [mock_choice]
        llm_service.client.chat.completions.create.return_value = mock_response_obj
        
        result = llm_service.classify_sentiment(
            article_title="Company Updates Policy",
            article_content="The company announced routine policy updates..."
        )
        
        assert -0.2 < result.sentiment_score < 0.2
        assert result.sentiment_label == "neutral"
    
    def test_sentiment_score_range(self, llm_service, sample_article):
        """Test that sentiment scores are in valid range"""
        test_cases = [
            {"sentiment_score": -1.0, "sentiment_label": "negative", "confidence": 0.9},
            {"sentiment_score": 0.0, "sentiment_label": "neutral", "confidence": 0.8},
            {"sentiment_score": 1.0, "sentiment_label": "positive", "confidence": 0.9},
        ]
        
        for mock_response in test_cases:
            mock_message = Mock()
            mock_message.content = json.dumps(mock_response)
            mock_choice = Mock()
            mock_choice.message = mock_message
            mock_response_obj = Mock()
            mock_response_obj.choices = [mock_choice]
            llm_service.client.chat.completions.create.return_value = mock_response_obj
            
            result = llm_service.classify_sentiment(
                article_title=sample_article["title"],
                article_content=sample_article["content"]
            )
            
            assert -1.0 <= result.sentiment_score <= 1.0
    
    def test_sentiment_api_error_handling(self, llm_service, sample_article):
        """Test error handling when API fails"""
        llm_service.client.chat.completions.create.side_effect = OpenAIError("API Error")
        
        result = llm_service.classify_sentiment(
            article_title=sample_article["title"],
            article_content=sample_article["content"]
        )
        
        # Should return neutral sentiment on error
        assert result.sentiment_score == 0.0
        assert result.sentiment_label == "neutral"
        assert result.confidence == 0.0
    
    def test_sentiment_content_truncation(self, llm_service):
        """Test that long content is truncated for sentiment analysis"""
        long_content = "C" * (MAX_CONTENT_LENGTH + 1000)
        
        mock_response = {
            "sentiment_score": 0.5,
            "sentiment_label": "neutral",
            "confidence": 0.7
        }
        mock_message = Mock()
        mock_message.content = json.dumps(mock_response)
        mock_choice = Mock()
        mock_choice.message = mock_message
        mock_response_obj = Mock()
        mock_response_obj.choices = [mock_choice]
        llm_service.client.chat.completions.create.return_value = mock_response_obj
        
        result = llm_service.classify_sentiment(
            article_title="Test",
            article_content=long_content
        )
        
        # Verify API was called
        assert llm_service.client.chat.completions.create.called
        # Check content was truncated
        call_args = llm_service.client.chat.completions.create.call_args
        prompt = call_args[1]["messages"][1]["content"]
        assert len(prompt) < len(long_content) + 500


class TestLLMServiceInitialization:
    """Tests for LLMService initialization"""
    
    def test_init_with_api_key(self):
        """Test initialization with provided API key"""
        with patch('app.services.llm.ai_service.OpenAI') as mock_openai:
            service = LLMService(api_key="test-key")
            assert service.api_key == "test-key"
            mock_openai.assert_called_once_with(api_key="test-key")
    
    def test_init_without_api_key_uses_settings(self):
        """Test initialization uses settings if no API key provided"""
        with patch('app.services.llm.ai_service.OpenAI') as mock_openai, \
             patch('app.services.llm.ai_service.settings') as mock_settings:
            mock_settings.OPENAI_API_KEY = "settings-key"
            service = LLMService()
            assert service.api_key == "settings-key"
            mock_openai.assert_called_once_with(api_key="settings-key")
    
    def test_init_missing_api_key_raises_error(self):
        """Test that missing API key raises ValueError"""
        with patch('app.services.llm.ai_service.settings') as mock_settings:
            mock_settings.OPENAI_API_KEY = ""
            with pytest.raises(ValueError, match="OpenAI API key is required"):
                LLMService()
