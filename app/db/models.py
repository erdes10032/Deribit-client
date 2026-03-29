from sqlalchemy import Column, Integer, Float, String, BigInteger, UniqueConstraint
from sqlalchemy.orm import declarative_base

Base = declarative_base()

class Price(Base):
    __tablename__ = "prices"

    id = Column(Integer, primary_key=True)
    ticker = Column(String, index=True)
    price = Column(Float)
    timestamp = Column(BigInteger)


class NotificationSubscription(Base):
    __tablename__ = "notification_subscriptions"

    __table_args__ = (
        UniqueConstraint("telegram_user_id", "ticker", name="uq_notification_subscriptions_user_ticker"),
    )

    id = Column(Integer, primary_key=True)
    telegram_user_id = Column(BigInteger, index=True)
    ticker = Column(String, index=True)