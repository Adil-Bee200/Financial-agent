from datetime import datetime
from typing import List
from pydantic import BaseModel, EmailStr, HttpUrl


class User(BaseModel):
    user_id: int
    email: EmailStr
    created_at: datetime

class Alerts(BaseModel):
    alert_id: int
    ticker: str 
    trigger_reason: str 
    sentiment_value: float
    created_at: datetime

class SentimentDaily(BaseModel):
    ticker: str 
    date: datetime 
    avg_sentiment: float
    article_count: int 
    momentum: float

class Portfolio(BaseModel):
    portfolio_id: int 
    user_id: int
    name: str
    created_at: datetime

class ArticleEntities(BaseModel):
    article_id: int 
    ticker: str
    confidence: float

class Articles(BaseModel):
    article_id: int
    title: str
    source: str 
    url: HttpUrl
    published_at: datetime
    summary: str 
    sentiment_score: float 
    relevance_score: float
    created_at: datetime
    processed_at: datetime      

class PortfolioTickers(BaseModel):
    ticker_id: int
    portfolio_id: int
    ticker: str 
    created_at: datetime

class RelevanceResult(BaseModel):
    """Result from relevance gate check"""
    relevant: bool
    companies: List[str]  # List of tickers/companies mentioned
    confidence: float  # 0.0 to 1.0


class SentimentResult(BaseModel):
    """Result from sentiment analysis"""
    sentiment_score: float  # -1.0 (very negative) to 1.0 (very positive)
    sentiment_label: str  # "positive", "negative", or "neutral"
    confidence: float  # 0.0 to 1.0