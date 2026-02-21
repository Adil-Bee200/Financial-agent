"""
Ingestion Service for Financial Article Processing

This service handles:
1. Fetching articles from the news API
2. Queueing articles for processing
"""

import logging
import requests
import json 
from app.core.config import settings
from typing import List, Dict, Any

logger = logging.getLogger(__name__)


class ArticleIngestionService:
    """
    Service for fetching articles from the news API and queueing them for processing
    """

    def __init__(self, news_api_key: str, news_api_base_url: str):
        """
        Initialize the article ingestion service.
        """

        # Set the news API key and base URL
        if not news_api_key:
            self.news_api_key = settings.NEWS_API_KEY
        else:
            self.news_api_key = news_api_key
        if not news_api_base_url:
            self.news_api_base_url = settings.NEWS_API_BASE_URL
        else:
            self.news_api_base_url = news_api_base_url

        if not self.news_api_key:
            raise ValueError("News API key is required. Set NEWS_API_KEY in .env")
        if not self.news_api_base_url:
            raise ValueError("News API base URL is required. Set NEWS_API_BASE_URL in .env")
        
        
        self.news_api_endpoint = f"{self.news_api_base_url}/everything"
        self.news_api_params = {
            "q": "financial",
            "sortBy": "publishedAt",
            "apiKey": self.news_api_key
        }

        logger.info(f"Article Ingestion Service initialized with news API key and base URL")


    def fetch_articles(self, query: str, from_date: str, to_date: str) -> List[Dict[str, Any]]:
        """
        Fetch articles from the news API.
        """

        try:
            response = requests.get(self.news_api_endpoint, params=self.news_api_params)
            response.raise_for_status()
            data = response.json()
            articles = data.get("articles", [])
            return articles
        except requests.exceptions.RequestException as e:
            logger.error(f"Error fetching articles from the news API: {e}")
            return []
        except Exception as e:
            logger.error(f"Error fetching articles from the news API: {e}")
            return []
        
    def queue_articles(self, articles: List[Dict[str, Any]]) -> None:
        """
        Queue articles for processing
        """
        try:
            for article in articles:
                self.queue.put(article)
        except Exception as e:
            logger.error(f"Error queuing articles for processing: {e}")
            return []
    
    