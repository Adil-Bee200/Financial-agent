from sqlalchemy import Column, Integer, String, DateTime, ForeignKey
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.core.database import Base


class Portfolio(Base):
    __tablename__ = "portfolios"

    portfolio_id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.user_id", ondelete="CASCADE"), nullable=False, index=True) 
    name = Column(String, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)


    user = relationship("User", back_populates="portfolios")

    # Relationships
    tickers = relationship("PortfolioTickers", back_populates="portfolio", cascade="all, delete-orphan")  ## if relationship is severed, all children are deleted
                                                                                                          ## whereas cascade deletes children only when parent is deleted
    
    alerts = relationship("Alert", back_populates="portfolio", cascade="all, delete-orphan")


class PortfolioTickers(Base):
    __tablename__ = "portfolio_tickers"

    ticker_id = Column(Integer, primary_key=True)
    portfolio_id = Column(Integer, ForeignKey("portfolios.portfolio_id"), unique=True, nullable=False, index=True)
    ticker = Column(String, nullable=False, index=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    portfolio = relationship("Portfolio", back_populates="tickers")
