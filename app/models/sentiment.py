from sqlalchemy import Column, String, DateTime, Float, Integer, UniqueConstraint
from sqlalchemy.sql import func
from app.core.database import Base


class SentimentDaily(Base):
    __tablename__ = "sentiment_daily"

    id = Column(Integer, primary_key=True)
    ticker = Column(String, nullable=False, index=True)
    date = Column(DateTime(timezone=True), nullable=False, index=True)
    avg_sentiment = Column(Float, nullable=False)
    article_count = Column(Integer, nullable=False, default=0)
    momentum = Column(Float, nullable=True)

    ## Ensures one record per ticker per day
    __table_args__ = (UniqueConstraint('ticker', 'date', name='unique_ticker_date'),)
