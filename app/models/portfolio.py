from sqlalchemy import Column, Integer, String, DateTime, ForeignKey
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.core.database import Base


class Portfolio(Base):
    __tablename__ = "portfolios"

    portfolio_id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.user_id"), nullable=False, index=True)  ## Portfolio needs to have a user
    name = Column(String, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    # Relationships
    tickers = relationship("PortfolioTickers", back_populates="portfolio", cascade="all, delete-orphan")  ## if relationship is severed, all children are deleted
                                                                                                          ## whereas cascade deletes children only when parent is deleted


class PortfolioTickers(Base):
    __tablename__ = "portfolio_tickers"

    ticker_id = Column(Integer, primary_key=True)
    portfolio_id = Column(Integer, ForeignKey("portfolios.portfolio_id"), nullable=False, index=True)
    ticker = Column(String, nullable=False, index=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    # Relationships
    portfolio = relationship("Portfolio", back_populates="tickers")
