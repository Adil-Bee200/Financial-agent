"""
Ingestion Service for Financial Article Processing

This service handles:
1. Fetching articles from the news API (with pagination)
2. Validating article structure
3. Queueing articles for processing via Celery
4. Rate limiting and error handling
"""

import logging
import requests
import json
import time
from datetime import datetime, timedelta
from typing import List, Dict, Any, Set, Optional
from app.core.config import settings
from app.core.database import SessionLocal
from app.models.article import Articles

logger = logging.getLogger(__name__)


class ArticleIngestionService:
    """
    Service for fetching articles from the news API and queueing them for processing.
    """

    def __init__(self, news_api_key: Optional[str] = None, news_api_base_url: Optional[str] = None):
        """
        Initialize the article ingestion service.
        
        Args:
            news_api_key: News API key (uses settings if None)
            news_api_base_url: News API base URL (uses settings if None)
        """
        # Set the news API key and base URL
        self.news_api_key = news_api_key or settings.NEWS_API_KEY
        self.news_api_base_url = news_api_base_url or settings.NEWS_API_BASE_URL

        if not self.news_api_key:
            raise ValueError("News API key is required. Set NEWS_API_KEY in .env")
        if not self.news_api_base_url:
            raise ValueError("News API base URL is required. Set NEWS_API_BASE_URL in .env")

        self.news_api_endpoint = f"{self.news_api_base_url}/everything"
        
        # Rate limiting
        self.last_request_time = 0
        self.min_request_interval = 1.0  # Minimum 1 second between requests
        self.max_retries = 3
        self.retry_delay = 2  # seconds

        logger.info("Article Ingestion Service initialized")

    def _rate_limit(self):
        """Enforce rate limiting between API requests."""
        elapsed = time.time() - self.last_request_time
        if elapsed < self.min_request_interval:
            sleep_time = self.min_request_interval - elapsed
            time.sleep(sleep_time)
        self.last_request_time = time.time()

    def _validate_article(self, article: Dict[str, Any]) -> bool:
        """
        Validate that article has required fields.
        
        Args:
            article: Article dictionary from NewsAPI
            
        Returns:
            True if valid, False otherwise
        """
        required_fields = ["title", "url", "publishedAt", "source"]
        
        # Check all required fields exist
        if not all(field in article for field in required_fields):
            missing = [f for f in required_fields if f not in article]
            logger.warning(f"Article missing required fields: {missing}")
            return False
        
        # Check fields are not None/empty
        if not article.get("url") or not article.get("title"):
            logger.warning(f"Article has empty URL or title: {article.get('url')}")
            return False
        
        return True

    def fetch_articles(
        self, 
        query: str = "financial",
        from_date: Optional[str] = None,
        to_date: Optional[str] = None,
        max_pages: int = 10
    ) -> List[Dict[str, Any]]:
        """
        Fetch articles from the news API with pagination support.
        
        Args:
            query: Search query (default: "financial")
            from_date: Start date in ISO format (YYYY-MM-DD) or None for recent
            to_date: End date in ISO format (YYYY-MM-DD) or None for now
            max_pages: Maximum number of pages to fetch (default: 10, ~1000 articles)
            
        Returns:
            List of article dictionaries
        """
        all_articles = []
        page = 1
        
        # Build base parameters
        params = {
            "q": query,
            "sortBy": "publishedAt",
            "apiKey": self.news_api_key,
            "pageSize": 100,  # NewsAPI max per page
        }
        
        # Add date filters if provided
        if from_date:
            params["from"] = from_date
        if to_date:
            params["to"] = to_date
        
        logger.info(f"Fetching articles with query: '{query}', pages: {max_pages}")
        
        while page <= max_pages:
            params["page"] = page
            
            # Rate limiting
            self._rate_limit()
            
            # Retry logic
            for attempt in range(self.max_retries):
                try:
                    response = requests.get(
                        self.news_api_endpoint, 
                        params=params,
                        timeout=30
                    )
                    response.raise_for_status()
                    data = response.json()
                    
                    # Check for API errors
                    if data.get("status") == "error":
                        error_msg = data.get("message", "Unknown API error")
                        logger.error(f"NewsAPI error: {error_msg}")
                        # Check if it's a rate limit error
                        if "rate limit" in error_msg.lower():
                            logger.warning("Rate limit hit, waiting before retry...")
                            time.sleep(60)  # Wait 1 minute for rate limit
                            continue
                        break  # Other errors, stop fetching
                    
                    articles = data.get("articles", [])
                    
                    if not articles:
                        logger.info(f"No more articles found at page {page}")
                        break  # No more articles
                    
                    # Validate articles
                    valid_articles = [a for a in articles if self._validate_article(a)]
                    all_articles.extend(valid_articles)
                    
                    logger.info(
                        f"Page {page}: Fetched {len(articles)} articles "
                        f"({len(valid_articles)} valid, {len(articles) - len(valid_articles)} invalid)"
                    )
                    
                    # Check if we got fewer than pageSize (last page)
                    if len(articles) < params["pageSize"]:
                        logger.info("Reached last page of results")
                        break
                    
                    page += 1
                    break  # Success, exit retry loop
                    
                except requests.exceptions.HTTPError as e:
                    if e.response.status_code == 429:  # Rate limit
                        logger.warning(f"Rate limit hit (429), waiting before retry {attempt + 1}/{self.max_retries}")
                        time.sleep(60 * (attempt + 1))  # Exponential backoff
                        continue
                    else:
                        logger.error(f"HTTP error fetching articles: {e}")
                        if attempt == self.max_retries - 1:
                            break
                        time.sleep(self.retry_delay * (attempt + 1))
                        
                except requests.exceptions.RequestException as e:
                    logger.error(f"Request error fetching articles (attempt {attempt + 1}/{self.max_retries}): {e}")
                    if attempt < self.max_retries - 1:
                        time.sleep(self.retry_delay * (attempt + 1))
                    else:
                        break
                        
                except Exception as e:
                    logger.error(f"Unexpected error fetching articles: {e}")
                    break
            
            # If we didn't get articles this page, stop
            if not articles:
                break
        
        logger.info(f"Total articles fetched: {len(all_articles)}")
        return all_articles

    def _get_existing_urls(self, article_urls: List[str]) -> Set[str]:
        """
        Check which article URLs already exist in the database.
        
        Args:
            article_urls: List of article URLs to check
            
        Returns:
            Set of URLs that already exist in the database
        """
        if not article_urls:
            return set()
        
        db = SessionLocal()
        try:
            existing_articles = db.query(Articles.url).filter(
                Articles.url.in_(article_urls)
            ).all()
            existing_urls = {url[0] for url in existing_articles}
            return existing_urls
        except Exception as e:
            logger.error(f"Error checking existing articles: {e}")
            return set()
        finally:
            db.close()
    
    def queue_articles(
        self, 
        articles: List[Dict[str, Any]],
        use_celery: bool = True
    ) -> Dict[str, int]:
        """
        Queue articles for processing with deduplication.
        Checks database for existing articles before queuing.
        
        Args:
            articles: List of articles to queue (NewsAPI format)
            use_celery: If True, use Celery tasks; if False, use raw Redis (for testing)
            
        Returns:
            Dictionary with counts: {
                'total': total articles,
                'new': newly queued articles,
                'duplicates': skipped duplicates,
                'invalid': invalid articles,
                'failed': failed to queue
            }
        """
        if not articles:
            return {'total': 0, 'new': 0, 'duplicates': 0, 'invalid': 0, 'failed': 0}
        
        # Validate articles first
        valid_articles = []
        invalid_count = 0
        
        for article in articles:
            if self._validate_article(article):
                valid_articles.append(article)
            else:
                invalid_count += 1
        
        if not valid_articles:
            logger.warning(f"All {len(articles)} articles failed validation")
            return {
                'total': len(articles),
                'new': 0,
                'duplicates': 0,
                'invalid': invalid_count,
                'failed': 0
            }
        
        # Extract URLs from valid articles
        article_urls = []
        url_to_article = {}
        
        for article in valid_articles:
            url = article.get('url')
            if url:
                article_urls.append(url)
                url_to_article[url] = article
        
        if not article_urls:
            logger.warning("No valid URLs found in articles")
            return {
                'total': len(articles),
                'new': 0,
                'duplicates': 0,
                'invalid': invalid_count,
                'failed': 0
            }
        
        # Check which URLs already exist in database
        existing_urls = self._get_existing_urls(article_urls)
        
        # Filter out duplicates
        new_articles = [
            url_to_article[url] 
            for url in article_urls 
            if url not in existing_urls
        ]
        
        # Queue only new articles
        queued_count = 0
        failed_count = 0
        
        if use_celery:
            # Use Celery tasks
            try:
                from app.workers.celery_worker import process_article_task
                
                for article in new_articles:
                    try:
                        process_article_task.delay(article)
                        queued_count += 1
                    except Exception as e:
                        logger.error(f"Error queuing article {article.get('url', 'unknown')}: {e}")
                        failed_count += 1
                        
            except ImportError:
                logger.error("Celery worker task not found, falling back to Redis")
                use_celery = False
        
        if not use_celery:
            # Fallback to raw Redis (for testing/development)
            from redis import Redis
            redis_client = Redis(
                host=settings.REDIS_HOST,
                port=settings.REDIS_PORT,
                db=settings.REDIS_DB
            )
            
            for article in new_articles:
                try:
                    redis_client.lpush("article_queue", json.dumps(article))
                    queued_count += 1
                except Exception as e:
                    logger.error(f"Error queuing article {article.get('url', 'unknown')}: {e}")
                    failed_count += 1
        
        duplicates_count = len(existing_urls)
        total_count = len(articles)
        
        logger.info(
            f"Article queueing complete: {queued_count} new, "
            f"{duplicates_count} duplicates skipped, {invalid_count} invalid, "
            f"{failed_count} failed (out of {total_count} total)"
        )
        
        return {
            'total': total_count,
            'new': queued_count,
            'duplicates': duplicates_count,
            'invalid': invalid_count,
            'failed': failed_count
        }
