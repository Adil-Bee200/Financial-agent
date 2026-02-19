from sqlalchemy import Column, Integer, String, DateTime, Float, ForeignKey
from sqlalchemy.sql import func
from app.core.database import Base
from sqlalchemy.orm import relationship


class Alerts(Base):
    __tablename__ = "alerts"

    alert_id = Column(Integer, primary_key=True)
    portfolio_id = Column(Integer, ForeignKey("portfolios.portfolio_id"), nullable=False)
    ticker = Column(String, nullable=False, index=True)
    trigger_reason = Column(String, nullable=False)
    sentiment_value = Column(Float, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False, index=True)

    portfolio = relationship("Portfolio", back_populates="alerts")
