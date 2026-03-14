import pathlib
import sys

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# Гарантируем, что корень проекта (в Docker это /app) есть в sys.path
ROOT_DIR = pathlib.Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from app.db.models import Base, Price
import app.db.database as db
import app.tasks.celery_tasks as tasks


TEST_DATABASE_URL = "sqlite:///:memory:"

engine = create_engine(
    TEST_DATABASE_URL, connect_args={"check_same_thread": False}
)
TestingSessionLocal = sessionmaker(
    autocommit=False, autoflush=False, bind=engine
)


db.SessionLocal = TestingSessionLocal
tasks.SessionLocal = TestingSessionLocal
Base.metadata.create_all(bind=engine)


class FakeDeribitClient:
    def __init__(self, session=None):
        self.session = session

    async def get_index_price(self, ticker: str):
        if ticker == "btc_usd":
            return 100.0
        if ticker == "eth_usd":
            return 200.0
        return 0.0


def test_fetch_prices_creates_two_price_rows(monkeypatch):
    # Подменяем реальный DeribitClient,
    # чтобы не ходить во внешний API
    monkeypatch.setattr(tasks, "DeribitClient", FakeDeribitClient)

    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)

    # Вызываем исходную функцию задачи напрямую
    tasks.fetch_prices.run()

    session = TestingSessionLocal()
    try:
        rows = session.query(Price).order_by(Price.ticker).all()
        assert len(rows) == 2

        assert rows[0].ticker == "btc_usd"
        assert rows[0].price == 100.0

        assert rows[1].ticker == "eth_usd"
        assert rows[1].price == 200.0
    finally:
        session.close()
