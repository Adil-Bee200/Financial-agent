from datetime import datetime, timedelta
from typing import List, Optional, Tuple

from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.models.article import ArticleEntities, Articles
from app.models.sentiment import SentimentDaily


class SentimentService:
    def __init__(self, db: Session):
        self.db = db

    def _day_bounds(self, date: datetime) -> Tuple[datetime, datetime]:
        """Start (inclusive) and end (exclusive) of the calendar day for range queries."""
        day_start = self.normalize_date_to_midnight(date)
        return day_start, day_start + timedelta(days=1)

    def _articles_for_ticker_on_date(self, ticker: str, date: datetime) -> List[Articles]:
        day_start, day_end = self._day_bounds(date)
        return (
            self.db.query(Articles)
            .join(ArticleEntities, ArticleEntities.article_id == Articles.article_id)
            .filter(ArticleEntities.ticker == ticker)
            .filter(Articles.published_at >= day_start)
            .filter(Articles.published_at < day_end)
            .all()
        )

    def _tickers_with_articles_on_date(self, date: datetime) -> List[str]:
        day_start, day_end = self._day_bounds(date)
        rows = (
            self.db.query(ArticleEntities.ticker)
            .join(Articles, ArticleEntities.article_id == Articles.article_id)
            .filter(Articles.published_at >= day_start)
            .filter(Articles.published_at < day_end)
            .distinct()
            .all()
        )
        return [r[0] for r in rows]

    def create_sentiment_for_ticker(self, ticker: str, date: datetime, avg_sentiment: float, article_count: int, momentum: float) -> SentimentDaily:
        date = self.normalize_date_to_midnight(date)
        existing_sentiment = self.get_sentiment_for_ticker_by_date(ticker, date)
        if existing_sentiment:
            existing_sentiment = self.update_sentiment_for_ticker(ticker, date, avg_sentiment, article_count, momentum)
            return existing_sentiment
        new_sentiment = SentimentDaily(ticker=ticker, date=date, avg_sentiment=avg_sentiment, article_count=article_count, momentum=momentum)
        self.db.add(new_sentiment)
        self.db.commit()
        self.db.refresh(new_sentiment)
        return new_sentiment
    

    ## Getters

    def get_sentiment_for_all_tickers(self) -> List[SentimentDaily]:
        return self.db.query(SentimentDaily).all()
    

    def get_sentiment_for_ticker_by_date(self, ticker: str, date: datetime) -> Optional[SentimentDaily]:
        date = self.normalize_date_to_midnight(date)
        existing_sentiment = self.db.query(SentimentDaily).filter(SentimentDaily.ticker == ticker).filter(SentimentDaily.date == date).first()
        if not existing_sentiment:
            return None
        return existing_sentiment

    def get_sentiment_for_all_tickers_by_date(self, date: datetime) -> List[SentimentDaily]:
        date = self.normalize_date_to_midnight(date)
        return self.db.query(SentimentDaily).filter(SentimentDaily.date == date).all()

    def get_sentiment_for_ticker_by_date_range(self, ticker: str, start_date: datetime, end_date: datetime) -> List[SentimentDaily]:
        start_date = self.normalize_date_to_midnight(start_date)
        end_date = self.normalize_date_to_midnight(end_date)
        return self.db.query(SentimentDaily).filter(SentimentDaily.ticker == ticker).filter(SentimentDaily.date >= start_date).filter(SentimentDaily.date <= end_date).all()
    
    def get_sentiment_for_all_tickers_by_date_range(self, start_date: datetime, end_date: datetime) -> List[SentimentDaily]:
        start_date = self.normalize_date_to_midnight(start_date)
        end_date = self.normalize_date_to_midnight(end_date)
        return self.db.query(SentimentDaily).filter(SentimentDaily.date >= start_date).filter(SentimentDaily.date <= end_date).all()
    
    def get_sentiment_for_all_tickers_by_date_above_threshold(self, date: datetime, threshold: float) -> List[SentimentDaily]:
        date = self.normalize_date_to_midnight(date)
        return self.db.query(SentimentDaily).filter(SentimentDaily.date == date).filter(SentimentDaily.avg_sentiment > threshold).all()
    
    def get_sentiment_for_all_tickers_by_date_below_threshold(self, date: datetime, threshold: float) -> List[SentimentDaily]:
        date = self.normalize_date_to_midnight(date)
        return self.db.query(SentimentDaily).filter(SentimentDaily.date == date).filter(SentimentDaily.avg_sentiment < threshold).all()
    


    ## Setters

    
    def update_sentiment_for_ticker(self, ticker: str, date: datetime, avg_sentiment: float, article_count: int, momentum: float) -> SentimentDaily:
        date = self.normalize_date_to_midnight(date)
        existing_sentiment = self.db.query(SentimentDaily).filter(SentimentDaily.ticker == ticker).filter(SentimentDaily.date == date).first()
        if not existing_sentiment:
            raise HTTPException(status_code=404, detail="Sentiment not found for ticker")
            
        existing_sentiment.avg_sentiment = avg_sentiment
        existing_sentiment.article_count = article_count
        existing_sentiment.momentum = momentum
        self.db.commit()
        self.db.refresh(existing_sentiment)
        return existing_sentiment


    def delete_sentiment_for_ticker(self, ticker: str, date: datetime) -> None:
        date = self.normalize_date_to_midnight(date)
        existing_sentiment = self.get_sentiment_for_ticker_by_date(ticker, date)
        if not existing_sentiment:
            return
        self.db.delete(existing_sentiment)
        self.db.commit()

    

    ## Utility functions

    def normalize_date_to_midnight(self, date: datetime) -> datetime:
        return date.replace(hour=0, minute=0, second=0, microsecond=0)
    
    

    ## Aggregation functions
    def aggregate_sentiment_for_ticker(self, ticker: str, date: datetime) -> SentimentDaily:
        date = self.normalize_date_to_midnight(date)
        articles_today = self._articles_for_ticker_on_date(ticker, date)
        if not articles_today:
            previous = self.get_sentiment_for_ticker_by_date(ticker, date - timedelta(days=1))
            momentum = (0.0 - previous.avg_sentiment) if previous else 0.0
            return self.create_sentiment_for_ticker(ticker, date, 0.0, 0, momentum)

        scores = [a.sentiment_score for a in articles_today if a.sentiment_score is not None]
        article_count = len(articles_today)
        avg_sentiment = sum(scores) / len(scores) if scores else 0.0

        previous_sentiment = self.get_sentiment_for_ticker_by_date(ticker, date - timedelta(days=1))
        if not previous_sentiment:
            previous_sentiment = self.create_sentiment_for_ticker(
                ticker, date - timedelta(days=1), 0.0, 0, 0.0
            )

        momentum = avg_sentiment - previous_sentiment.avg_sentiment
        return self.create_sentiment_for_ticker(ticker, date, avg_sentiment, article_count, momentum)

    def aggregate_sentiment_for_all_tickers(self, date: datetime) -> List[SentimentDaily]:
        date = self.normalize_date_to_midnight(date)
        tickers = self._tickers_with_articles_on_date(date)
        if not tickers:
            return []
        return [self.aggregate_sentiment_for_ticker(t, date) for t in tickers]
