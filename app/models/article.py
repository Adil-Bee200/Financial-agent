from sqlalchemy import Column, Integer, String, DateTime, Float, Text, ForeignKey, PrimaryKeyConstraint
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.core.database import Base


class Articles(Base):
    __tablename__ = "articles"

    article_id = Column(Integer, primary_key=True)
    title = Column(String, nullable=False, index=True)
    source = Column(String, nullable=False)
    url = Column(String, nullable=False, unique=True)
    published_at = Column(DateTime(timezone=True), nullable=False, index=True)
    summary = Column(Text, nullable=True)
    sentiment_score = Column(Float, nullable=True)
    relevance_score = Column(Float, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    processed_at = Column(DateTime(timezone=True), nullable=True)

    # Relationships
    entities = relationship("ArticleEntities", back_populates="article", cascade="all, delete-orphan")


class ArticleEntities(Base):
    """Maps an article to one ticker mention; composite PK allows multiple tickers per article."""

    __tablename__ = "article_entities"
    __table_args__ = (PrimaryKeyConstraint("article_id", "ticker", name="article_entities_pkey"),)

    article_id = Column(Integer, ForeignKey("articles.article_id", ondelete="CASCADE"), nullable=False)
    ticker = Column(String, nullable=False, index=True)
    confidence = Column(Float, nullable=False)

    article = relationship("Articles", back_populates="entities")
