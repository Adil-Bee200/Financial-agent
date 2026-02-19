from datetime import datetime
from typing import Optional
from pydantic import BaseModel, EmailStr, Field, HttpUrl
from typing import Annotated


class User(BaseModel):
    user_id: int
    email: EmailStr
    created_at: datetime

class Alerts(BaseModel):
    alert_id: int
    ticker: str 
    tigger_reason: str 
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

