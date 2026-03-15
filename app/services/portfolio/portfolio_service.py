from typing import List
from sqlalchemy.orm import Session
from fastapi import HTTPException


from app.schemas.schemas_v1 import Portfolio, PortfolioTickers


class PortfolioService:
    def __init__(self, db: Session):
        self.db = db

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

    def get_all_portfolios(self) -> List[Portfolio]:
        return self.db.query(Portfolio).all()

    ## User can have multiple portfolios
    def get_portfolio_by_user_id(self, user_id: int) -> List[Portfolio]:
        return self.db.query(Portfolio).filter(Portfolio.user_id == user_id).all()

    def add_ticker_to_portfolio(self, portfolio_id: int, ticker: str) -> None:
        existing_ticker = self.get_ticker_from_portfolio(portfolio_id, ticker)
        
        if not existing_ticker:
            new_ticker = PortfolioTickers(portfolio_id=portfolio_id, ticker=ticker)
            self.db.add(new_ticker)
            self.db.commit()
            self.db.refresh(new_ticker)
            return new_ticker
        else:
            raise HTTPException(status_code=400, detail="Ticker already exists in portfolio")

    # Remove ticker from given portfolio
    def remove_ticker_from_portfolio(self, portfolio_id: int, ticker: str) -> None:
        existing_ticker = self.get_ticker_from_portfolio(portfolio_id, ticker)
        self.db.delete(existing_ticker)
        self.db.commit()
    
    # Get all tickers from given portfolio
    def get_all_tickers_from_portfolio(self, portfolio_id: int) -> List[PortfolioTickers]:
        portfolio = self.get_portfolio(portfolio_id)
        portfolio_tickers = portfolio.tickers
        return portfolio_tickers

    # Get specific ticker from given portfolio
    def get_ticker_from_portfolio(self, portfolio_id: int, ticker: str) -> PortfolioTickers:
        existing_ticker = self.db.query(PortfolioTickers).filter(PortfolioTickers.portfolio_id == portfolio_id).filter(PortfolioTickers.ticker == ticker).first()
        if not existing_ticker:
            raise HTTPException(status_code=404, detail="Ticker not found in portfolio")
        return existing_ticker

