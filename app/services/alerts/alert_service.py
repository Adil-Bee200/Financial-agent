import logging
from datetime import datetime, timedelta
from typing import List, Optional, Tuple

from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.alert import Alerts
from app.services.sentiment.sentiment_service import SentimentService

logger = logging.getLogger(__name__)


class AlertService:
    """Alerts driven by rolling sentiment (article-weighted) and volume spikes vs prior-day baseline."""

    def __init__(self, db: Session):
        self.db = db
        self.sentiment_service = SentimentService(db)

    def rolling_window_bounds(self, end_date: datetime, window_days: int) -> Tuple[datetime, datetime]:
        """Inclusive calendar window [start, end] of length ``window_days``."""
        end = self.sentiment_service.normalize_date_to_midnight(end_date)
        start = end - timedelta(days=window_days - 1)
        return start, end

    def article_weighted_rolling_sentiment(self, ticker: str, start_date: datetime, end_date: datetime) -> Optional[float]:
        """
        Article-weighted mean of daily ``avg_sentiment`` over ``SentimentDaily`` rows in range.
        Days with no row are omitted (no coverage that day).
        """
        rows = self.sentiment_service.get_sentiment_for_ticker_by_date_range(ticker, start_date, end_date)
        if not rows:
            return None

        weighted = 0.0
        total_articles = 0
        for row in rows:
            weighted += row.avg_sentiment * row.article_count
            total_articles += row.article_count

        if total_articles == 0:
            return None
        return weighted / total_articles

    def rolling_sentiment_below_threshold(self, ticker: str, start_date: datetime, end_date: datetime, threshold: Optional[float] = None) -> bool:
        """
        True if article-weighted rolling sentiment is strictly below ``threshold``.
        Defaults to ``settings.SENTIMENT_THRESHOLD`` (e.g. sustained negative news).
        """
        limit = settings.NEGATIVE_SENTIMENT_THRESHOLD if threshold is None else threshold
        rolling = self.article_weighted_rolling_sentiment(ticker, start_date, end_date)
        if rolling is None:
            return False
        return rolling < limit
    
    def rolling_sentiment_above_threshold(self, ticker: str, start_date: datetime, end_date: datetime, threshold: Optional[float] = None) -> bool:
        """
        True if article-weighted rolling sentiment is strictly above ``threshold``.
        Defaults to ``settings.POSITIVE_SENTIMENT_THRESHOLD`` (e.g. sustained positive news).
        """
        limit = settings.POSITIVE_SENTIMENT_THRESHOLD if threshold is None else threshold
        rolling = self.article_weighted_rolling_sentiment(ticker, start_date, end_date)
        if rolling is None:
            return False
        return rolling > limit

    def volume_spike_ratio_latest_vs_prior(self, ticker: str, start_date: datetime, end_date: datetime, multiplier: Optional[float] = None) -> Optional[float]:
        """
        Compare **latest day** in range to **mean article_count of prior days** in the same range.

        Returns ``latest / baseline`` when ``latest >= multiplier * baseline``, else ``None``.
        Requires at least two days of rows. If baseline is 0 but the latest day has articles,
        returns a large ratio so callers can treat it as a spike from silence.
        """
        mult = settings.VOLUME_SPIKE_MULTIPLIER if multiplier is None else multiplier
        rows = self.sentiment_service.get_sentiment_for_ticker_by_date_range(ticker, start_date, end_date)
        if len(rows) < 2:
            return None

        ordered = sorted(rows, key=lambda r: r.date)
        prior = ordered[:-1]
        latest = ordered[-1]
        baseline = sum(r.article_count for r in prior) / len(prior)
        today_count = latest.article_count

        if baseline == 0:
            return float(today_count) if today_count > 0 else None

        ratio = today_count / baseline
        if today_count >= mult * baseline:
            return ratio
        return None

    def create_alert(self, ticker: str, trigger_reason: str, sentiment_value: float, portfolio_id: int) -> Alerts:
        alert = Alerts(ticker=ticker, trigger_reason=trigger_reason, sentiment_value=sentiment_value, portfolio_id=portfolio_id,)
        self.db.add(alert)
        self.db.commit()
        self.db.refresh(alert)
        return alert

    def get_alerts_for_portfolio(self, portfolio_id: int) -> List[Alerts]:
        return self.db.query(Alerts).filter(Alerts.portfolio_id == portfolio_id).all()
