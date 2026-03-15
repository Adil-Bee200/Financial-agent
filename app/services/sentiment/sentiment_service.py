from datetime import datetime
from typing import List
from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.schemas.schemas_v1 import SentimentDaily


class SentimentService:
    def __init__(self, db: Session):
        self.db = db

    def create_sentiment_for_ticker(self, ticker: str, date: datetime, avg_sentiment: float, article_count: int, momentum: float) -> SentimentDaily:
        existing_sentiment = self.get_sentiment_for_ticker_by_date(ticker, date)
        if existing_sentiment:
            raise HTTPException(status_code=400, detail="Sentiment already exists for ticker")
        new_sentiment = SentimentDaily(ticker=ticker, date=date, avg_sentiment=avg_sentiment, article_count=article_count, momentum=momentum)
        self.db.add(new_sentiment)
        self.db.commit()
        self.db.refresh(new_sentiment)
        return new_sentiment
    

    ## Getters

    def get_sentiment_for_all_tickers(self) -> List[SentimentDaily]:
        return self.db.query(SentimentDaily).all()
    

    def get_sentiment_for_ticker_by_date(self, ticker: str, date: datetime) -> SentimentDaily:
        existing_sentiment = self.db.query(SentimentDaily).filter(SentimentDaily.ticker == ticker).filter(SentimentDaily.date == date).first()
        if not existing_sentiment:
            raise HTTPException(status_code=404, detail="Sentiment not found for ticker")
        return existing_sentiment

    def get_sentiment_for_all_tickers_by_date(self, date: datetime) -> List[SentimentDaily]:
        return self.db.query(SentimentDaily).filter(SentimentDaily.date == date).all()

    def get_sentiment_for_ticker_by_date_range(self, ticker: str, start_date: datetime, end_date: datetime) -> List[SentimentDaily]:
        return self.db.query(SentimentDaily).filter(SentimentDaily.ticker == ticker).filter(SentimentDaily.date >= start_date).filter(SentimentDaily.date <= end_date).all()
    
    def get_sentiment_for_all_tickers_by_date_range(self, start_date: datetime, end_date: datetime) -> List[SentimentDaily]:
        return self.db.query(SentimentDaily).filter(SentimentDaily.date >= start_date).filter(SentimentDaily.date <= end_date).all()
    
    def get_sentiment_for_all_tickers_by_date_above_threshold(self, date: datetime, threshold: float) -> List[SentimentDaily]:
        return self.db.query(SentimentDaily).filter(SentimentDaily.date == date).filter(SentimentDaily.avg_sentiment > threshold).all()
    
    def get_sentiment_for_all_tickers_by_date_below_threshold(self, date: datetime, threshold: float) -> List[SentimentDaily]:
        return self.db.query(SentimentDaily).filter(SentimentDaily.date == date).filter(SentimentDaily.avg_sentiment < threshold).all()
    


    ## Setters

    
    def update_sentiment_for_ticker(self, ticker: str, date: datetime, avg_sentiment: float, article_count: int, momentum: float) -> SentimentDaily:
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
        existing_sentiment = self.get_sentiment_for_ticker_by_date(ticker, date)
        self.db.delete(existing_sentiment)
        self.db.commit()

    