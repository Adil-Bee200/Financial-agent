import json
import logging
from typing import List, Optional
from sqlalchemy.orm import Session
from fastapi import HTTPException
from redis import Redis

from app.models.portfolio import Portfolio, PortfolioTickers
from app.core.config import settings

logger = logging.getLogger(__name__)

# Cache configuration
CACHE_KEY_ALL_TICKERS = "tracked_tickers:all"
CACHE_KEY_USER_TICKERS = "tracked_tickers:user:{}"
CACHE_TTL = 300  # 5 minutes as tickers don't change frequently


class PortfolioService:
    def __init__(self, db: Session, redis_client: Optional[Redis] = None):
        self.db = db
        # Initialize Redis client for caching (lazy initialization)
        self._redis_client = redis_client
        self._redis_initialized = False
    
    def _get_redis_client(self) -> Optional[Redis]:
        """Lazy initialization of Redis client for caching."""
        if self._redis_client is not None:
            return self._redis_client
        
        if not self._redis_initialized:
            try:
                self._redis_client = Redis(
                    host=settings.REDIS_HOST,
                    port=settings.REDIS_PORT,
                    db=settings.REDIS_DB,
                    decode_responses=True  # Get strings instead of bytes
                )
                self._redis_client.ping()
                self._redis_initialized = True
                logger.debug("Redis cache client initialized")
            except Exception as e:
                logger.warning(f"Redis cache unavailable: {e}. Continuing without cache.")
                self._redis_client = None
                self._redis_initialized = True
        
        return self._redis_client
    
    def _invalidate_ticker_cache(self):
        """Invalidate all ticker-related caches when tickers are modified."""
        redis = self._get_redis_client()
        if redis:
            try:
                keys = redis.keys("tracked_tickers:*")
                if keys:
                    redis.delete(*keys)
                    logger.debug(f"Invalidated {len(keys)} ticker cache keys")
            except Exception as e:
                logger.warning(f"Error invalidating cache: {e}")

    def create_portfolio(self, portfolio: Portfolio) -> Portfolio:
        self.db.add(portfolio)
        self.db.commit()
        self.db.refresh(portfolio)
        return portfolio
    
    def get_portfolio(self, portfolio_id: int) -> Portfolio:
        portfolio = self.db.query(Portfolio).filter(Portfolio.portfolio_id == portfolio_id).first()
        if not portfolio:
            raise HTTPException(status_code=404, detail="Portfolio not found")
        return portfolio

    def update_portfolio(self, portfolio_id: int, portfolio: Portfolio) -> Portfolio:
        self.db.query(Portfolio).filter(Portfolio.portfolio_id == portfolio_id).update(portfolio.model_dump())
        self.db.commit()
        self.db.refresh(portfolio)
        return portfolio

    def delete_portfolio(self, portfolio_id: int) -> None:
        self.db.query(Portfolio).filter(Portfolio.portfolio_id == portfolio_id).delete()
        self.db.commit()
        
        # Invalidate cache when portfolio is deleted (tickers are cascade deleted)
        self._invalidate_ticker_cache()

    def get_all_portfolios(self) -> List[Portfolio]:
        return self.db.query(Portfolio).all()

    ## User can have multiple portfolios
    def get_portfolio_by_user_id(self, user_id: int) -> List[Portfolio]:
        return self.db.query(Portfolio).filter(Portfolio.user_id == user_id).all()

    def add_ticker_to_portfolio(self, portfolio_id: int, ticker: str) -> None:
        # Check if ticker already exists (without raising exception)
        existing_ticker = self.db.query(PortfolioTickers).filter(
            PortfolioTickers.portfolio_id == portfolio_id,
            PortfolioTickers.ticker == ticker
        ).first()
        
        if existing_ticker:
            raise HTTPException(status_code=400, detail="Ticker already exists in portfolio")
        
        new_ticker = PortfolioTickers(portfolio_id=portfolio_id, ticker=ticker)
        self.db.add(new_ticker)
        self.db.commit()
        self.db.refresh(new_ticker)
        
        # Invalidate cache when tickers change
        self._invalidate_ticker_cache()
        
        return new_ticker

    # Remove ticker from given portfolio
    def remove_ticker_from_portfolio(self, portfolio_id: int, ticker: str) -> None:
        existing_ticker = self.get_ticker_from_portfolio(portfolio_id, ticker)
        self.db.delete(existing_ticker)
        self.db.commit()
        
        # Invalidate cache when tickers change
        self._invalidate_ticker_cache()
    
    # Get all tickers from given portfolio
    def get_all_tickers_from_portfolio(self, portfolio_id: int) -> List[PortfolioTickers]:
        portfolio_tickers = self.db.query(PortfolioTickers).filter(PortfolioTickers.portfolio_id == portfolio_id).all()
        return portfolio_tickers

    # Get specific ticker from given portfolio
    def get_ticker_from_portfolio(self, portfolio_id: int, ticker: str) -> PortfolioTickers:
        existing_ticker = self.db.query(PortfolioTickers).filter(PortfolioTickers.portfolio_id == portfolio_id).filter(PortfolioTickers.ticker == ticker).first()
        if not existing_ticker:
            raise HTTPException(status_code=404, detail="Ticker not found in portfolio")
        return existing_ticker
    
    # Get all unique tickers across all portfolios (for article processing)
    def get_all_tracked_tickers(self) -> List[str]:
        """
        Get all unique tickers tracked across all portfolios.
        Uses Redis cache to avoid database queries on every article.
        
        This is called frequently during article processing, so caching is critical.
        
        Returns:
            List of unique ticker symbols (e.g., ["NVDA", "AAPL", "MSFT"])
        """
        redis = self._get_redis_client()
        
        # Try to get from cache first
        if redis:
            try:
                cached = redis.get(CACHE_KEY_ALL_TICKERS)
                if cached:
                    tickers = json.loads(cached)
                    logger.debug(f"Cache hit: Retrieved {len(tickers)} tickers from cache")
                    return tickers
            except Exception as e:
                logger.warning(f"Cache read error: {e}. Falling back to database.")
        
        # Cache miss - query database
        tickers_result = self.db.query(PortfolioTickers.ticker).distinct().all()
        tickers = [ticker[0] for ticker in tickers_result]
        
        # Store in cache
        if redis:
            try:
                redis.setex(
                    CACHE_KEY_ALL_TICKERS,
                    CACHE_TTL,
                    json.dumps(tickers)
                )
                logger.debug(f"Cache updated: Stored {len(tickers)} tickers (TTL: {CACHE_TTL}s)")
            except Exception as e:
                logger.warning(f"Cache write error: {e}")
        
        return tickers
    
    # Get all unique tickers for a specific user's portfolios
    def get_tracked_tickers_by_user(self, user_id: int) -> List[str]:
        """
        Get all unique tickers tracked in a specific user's portfolios.
        Uses Redis cache to avoid repeated database queries.
        
        Args:
            user_id: User ID to get tickers for
            
        Returns:
            List of unique ticker symbols
        """
        redis = self._get_redis_client()
        cache_key = CACHE_KEY_USER_TICKERS.format(user_id)
        
        # Try to get from cache first
        if redis:
            try:
                cached = redis.get(cache_key)
                if cached:
                    tickers = json.loads(cached)
                    logger.debug(f"Cache hit: Retrieved {len(tickers)} tickers for user {user_id}")
                    return tickers
            except Exception as e:
                logger.warning(f"Cache read error: {e}. Falling back to database.")
        
        # Cache miss - query database
        tickers_result = (
            self.db.query(PortfolioTickers.ticker)
            .join(Portfolio, PortfolioTickers.portfolio_id == Portfolio.portfolio_id)
            .filter(Portfolio.user_id == user_id)
            .distinct()
            .all()
        )
        tickers = [ticker[0] for ticker in tickers_result]
        
        # Store in cache
        if redis:
            try:
                redis.setex(cache_key, CACHE_TTL, json.dumps(tickers))
                logger.debug(f"Cache updated: Stored {len(tickers)} tickers for user {user_id}")
            except Exception as e:
                logger.warning(f"Cache write error: {e}")
        
        return tickers
    