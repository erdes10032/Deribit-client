import pathlib
import re
import sys

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# Гарантируем, что корень проекта есть в sys.path
ROOT_DIR = pathlib.Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from app.main import app
from app.db.models import Base, Price
from app.services.chart_service import ChartService
import app.api.routes as routes


client = TestClient(app)


@pytest.fixture()
def test_db_sessionlocal(monkeypatch):
    engine = create_engine(
        "sqlite:///./test_features.db",
        connect_args={"check_same_thread": False},
    )
    testing_session_local = sessionmaker(autocommit=False, autoflush=False, bind=engine)

    monkeypatch.setattr(routes, "SessionLocal", testing_session_local)

    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    yield testing_session_local
    Base.metadata.drop_all(bind=engine)


def _seed_prices(testing_session_local) -> None:
    with testing_session_local() as session:
        session.add_all(
            [
                Price(ticker="btc_usd", price=100.0, timestamp=10),
                Price(ticker="btc_usd", price=120.0, timestamp=20),
            ]
        )
        session.commit()


def test_prediction_returns_400_for_invalid_ticker():
    response = client.get("/prediction", params={"ticker": "doge_usd"})
    assert response.status_code == 400


def test_full_chart_endpoint_returns_file_when_data_exists(
    tmp_path,
    monkeypatch,
    test_db_sessionlocal,
):
    _seed_prices(test_db_sessionlocal)
    fake_chart = tmp_path / "btc_usd__full__01.01.2026_10-00-00__upto_20.png"
    fake_chart.write_bytes(b"\x89PNG\r\n\x1a\n")

    def fake_build_full_chart(self, ticker, prices):
        return str(fake_chart)

    monkeypatch.setattr(routes.ChartService, "build_full_chart", fake_build_full_chart)

    response = client.get("/charts/full", params={"ticker": "btc_usd"})
    assert response.status_code == 200
    assert response.content.startswith(b"\x89PNG")


def test_full_chart_filename_contains_creation_time(tmp_path):
    service = ChartService()
    service.OUTPUT_DIR = str(tmp_path)

    prices = [
        Price(ticker="eth_usd", price=1000.0, timestamp=100),
        Price(ticker="eth_usd", price=1010.0, timestamp=160),
    ]

    path = service.build_full_chart("eth_usd", prices)
    assert path
    filename = pathlib.Path(path).name

    # eth_usd__full__dd.mm.yyyy_HH-MM-SS__upto_<ts>.png
    assert re.match(
        r"^eth_usd__full__\d{2}\.\d{2}\.\d{4}_\d{2}-\d{2}-\d{2}__upto_\d+\.png$",
        filename,
    )
