import pathlib
import sys

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# Гарантируем, что корень проекта (в Docker это /app) есть в sys.path
ROOT_DIR = pathlib.Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from app.main import app
from app.db.models import Base, Price
import app.db.database as db
import app.api.routes as routes


TEST_DATABASE_URL = "sqlite:///./test_api.db"

engine = create_engine(
    TEST_DATABASE_URL, connect_args={"check_same_thread": False}
)
TestingSessionLocal = sessionmaker(
    autocommit=False, autoflush=False, bind=engine
)


db.SessionLocal = TestingSessionLocal
routes.SessionLocal = TestingSessionLocal
Base.metadata.create_all(bind=engine)

client = TestClient(app)


@pytest.fixture(autouse=True)
def setup_test_data():
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)

    session = TestingSessionLocal()
    try:
        session.add_all(
            [
                Price(id=1, ticker="btc_usd", price=100.0, timestamp=10),
                Price(id=2, ticker="btc_usd", price=110.0, timestamp=20),
                Price(id=3, ticker="eth_usd", price=200.0, timestamp=15),
            ]
        )
        session.commit()
    finally:
        session.close()

    yield


def test_get_prices_returns_only_requested_ticker():
    response = client.get("/prices", params={"ticker": "btc_usd"})

    assert response.status_code == 200
    data = response.json()

    assert len(data) == 2
    assert all(item["ticker"] == "btc_usd" for item in data)


def test_get_latest_price_returns_max_timestamp():
    response = client.get("/price/latest", params={"ticker": "btc_usd"})

    assert response.status_code == 200
    item = response.json()

    assert item["ticker"] == "btc_usd"
    assert item["timestamp"] == 20
    assert item["price"] == 110.0


def test_get_price_by_date_filters_range_correctly():
    response = client.get(
        "/price/by-date",
        params={"ticker": "btc_usd", "start": 0, "end": 15},
    )

    assert response.status_code == 200
    data = response.json()

    assert len(data) == 1
    assert data[0]["ticker"] == "btc_usd"
    assert data[0]["timestamp"] == 10
