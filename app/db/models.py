from sqlalchemy import Column, Integer, Float, String, BigInteger
from sqlalchemy.orm import declarative_base

Base = declarative_base()

class Price(Base):
    __tablename__ = "prices"

    id = Column(Integer, primary_key=True)
    ticker = Column(String, index=True)
    price = Column(Float)
    timestamp = Column(BigInteger)