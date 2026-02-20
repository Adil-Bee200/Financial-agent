"""
Pytest configuration and fixtures
"""
import pytest
from unittest.mock import Mock, MagicMock, patch


@pytest.fixture
def mock_openai_client():
    """Mock OpenAI client for testing"""
    mock_client = Mock()
    mock_response = Mock()
    mock_choice = Mock()
    mock_message = Mock()
    
    # Default response
    mock_message.content = '{"relevant": true, "companies": ["NVDA"], "confidence": 0.9}'
    mock_choice.message = mock_message
    mock_response.choices = [mock_choice]
    
    # Setup the chat.completions.create chain
    mock_client.chat = Mock()
    mock_client.chat.completions = Mock()
    mock_client.chat.completions.create = Mock(return_value=mock_response)
    
    return mock_client


@pytest.fixture
def llm_service(mock_openai_client):
    """Create LLMService instance with mocked OpenAI client"""
    with patch('app.services.llm.ai_service.OpenAI', return_value=mock_openai_client):
        from app.services.llm.ai_service import LLMService
        service = LLMService(api_key="test-api-key")
        return service


@pytest.fixture
def sample_article():
    """Sample article data for testing"""
    return {
        "title": "NVIDIA Announces New AI Chip",
        "content": "NVIDIA has unveiled its latest AI chip designed for data centers. The new chip promises significant performance improvements and energy efficiency gains."
    }


@pytest.fixture
def sample_tickers():
    """Sample ticker list for testing"""
    return ["NVDA", "AAPL", "MSFT"]
