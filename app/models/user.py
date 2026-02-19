from sqlalchemy import Column, Integer, String, DateTime
from sqlalchemy.sql import func
from app.core.database import Base
from sqlalchemy.orm import relationship


class User(Base):
    __tablename__ = "users"

    user_id = Column(Integer, primary_key=True)
    email = Column(String, unique=True, index=True, nullable=False)      ## Unique + high cardinality = index
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    portfolios = relationship("Portfolio", back_populates="user", cascade="all, delete-orphan")


