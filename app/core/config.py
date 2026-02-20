from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    # Database - can use DATABASE_URL directly or construct from components
    DATABASE_URL: Optional[str] = None
    database_hostname: str = "localhost"
    database_port: str = "5432"
    database_password: str = "postgres"
    database_name: str = "financial_agent"
    database_username: str = "postgres"
    
    def get_database_url(self) -> str:
        """Get database URL, either from DATABASE_URL or construct from components"""
        if self.DATABASE_URL:
            return self.DATABASE_URL
        return f"postgresql://{self.database_username}:{self.database_password}@{self.database_hostname}:{self.database_port}/{self.database_name}"
    secret_key: str = "your-secret-key-change-in-production"
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 30
    
    # Redis
    REDIS_URL: str = "redis://localhost:6379/0"
    REDIS_HOST: str = "localhost"
    REDIS_PORT: int = 6379
    REDIS_DB: int = 0
    
    # Celery
    CELERY_BROKER_URL: str = "redis://localhost:6379/0"
    CELERY_RESULT_BACKEND: str = "redis://localhost:6379/0"
    
    # OpenAI
    OPENAI_API_KEY: str = ""
    
    # Discord
    DISCORD_WEBHOOK_URL: Optional[str] = None
    
    # Use NewsAPI, Alpha Vantage, or Financial Modeling Prep
    NEWS_API_KEY: Optional[str] = None
    NEWS_API_BASE_URL: str = "https://newsapi.org/v2"
    
    # Application
    APP_NAME: str = "Financial Research Agent"
    DEBUG: bool = False
    ENVIRONMENT: str = "development"
    
    # Ingestion
    INGESTION_INTERVAL_MINUTES: int = 5
    
    # Alert thresholds
    SENTIMENT_THRESHOLD: float = -0.3  # Negative sentiment threshold
    VOLUME_SPIKE_MULTIPLIER: float = 2.0  # 2x average volume triggers alert
    ROLLING_WINDOW_DAYS: int = 7  # Days for rolling average
    
    class Config:
        env_file = ".env"
        case_sensitive = True


settings = Settings()
