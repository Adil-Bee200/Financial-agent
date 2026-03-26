import logging
from typing import Optional

import httpx

from app.core.config import settings
from app.models.alert import Alerts

logger = logging.getLogger(__name__)

def send_discord_alert_if_configured(alert: Alerts) -> None:
    """
    POST a message to the configured Discord webhook. No-op if URL is unset.
    Failures are logged; they do not affect alert persistence.
    """
    url: Optional[str] = settings.DISCORD_WEBHOOK_URL
    if not url or not str(url).strip():
        logger.debug("Discord webhook not configured; skipping notification")
        return

    payload = {
        "content": f"Alert ID {alert.alert_id}: {alert.trigger_reason} for {alert.ticker} with sentiment value {alert.sentiment_value}"
    }

    response = httpx.post(str(url).strip(), json=payload, timeout=15.0).raise_for_status()
    return response.status_code == 200
