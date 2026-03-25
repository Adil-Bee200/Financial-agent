"""
Ingestion Service Module

Provides article fetching and queueing functionality.
"""

from app.services.ingestion.article_ingestion_service import ArticleIngestionService

__all__ = ["ArticleIngestionService"]
