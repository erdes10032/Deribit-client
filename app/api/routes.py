from fastapi import APIRouter, Query
from fastapi.responses import HTMLResponse
from app.db.database import SessionLocal
from app.db.models import Price
from app.schemas.price import PriceResponse

router = APIRouter()


@router.get("/", response_class=HTMLResponse)
def index():
    return """
    <!doctype html>
    <html lang="en">
    <head>
        <meta charset="utf-8">
        <title>Deribit Prices</title>
    </head>
    <body>
        <center>
        <h1>Deribit Price Viewer</h1>
        <p>Страница для работы с вашими эндпоинтами.</p>

        <h2>История цен</h2>
        <form method="get" action="/ui/prices" target="result">
            <label for="ticker">Ticker:</label>
            <input id="ticker" name="ticker" type="text" required>
            <button type="submit">Показать</button>
        </form>

        <h2>Последняя цена</h2>
        <form method="get" action="/ui/price/latest" target="result">
            <label for="latest_ticker">Ticker:</label>
            <input id="latest_ticker" name="ticker" type="text" required>
            <button type="submit">Показать</button>
        </form>

        <h2>Цена по диапазону времени</h2>
        <form method="get" action="/ui/price/by-date" target="result">
            <label for="range_ticker">Ticker:</label>
            <input id="range_ticker" name="ticker" type="text" required>
            <br>
            <label for="start">Start (timestamp):</label>
            <input id="start" name="start" type="number" required>
            <br>
            <label for="end">End (timestamp):</label>
            <input id="end" name="end" type="number" required>
            <button type="submit">Показать</button>
        </form>

        <h2>Результат</h2>
        <iframe name="result" width="100%" height="400"></iframe>
        </center>
    </body>
    </html>
    """


@router.get("/prices", response_model=list[PriceResponse])
def get_prices(ticker: str = Query(...)):
    with SessionLocal() as session:
        data = (
            session.query(Price)
            .filter(Price.ticker == ticker)
            .all()
        )
        return data


@router.get("/price/latest", response_model=PriceResponse | None)
def get_latest_price(ticker: str = Query(...)):
    with SessionLocal() as session:
        data = (
            session.query(Price)
            .filter(Price.ticker == ticker)
            .order_by(Price.timestamp.desc())
            .first()
        )
        return data


@router.get("/price/by-date", response_model=list[PriceResponse])
def get_price_by_date(
    ticker: str = Query(...),
    start: int = Query(...),
    end: int = Query(...)
):
    with SessionLocal() as session:
        data = (
            session.query(Price)
            .filter(
                Price.ticker == ticker,
                Price.timestamp >= start,
                Price.timestamp <= end
            )
            .all()
        )
        return data


@router.get("/ui/prices", response_class=HTMLResponse)
def ui_prices(ticker: str = Query(...)):
    with SessionLocal() as session:
        data = (
            session.query(Price)
            .filter(Price.ticker == ticker)
            .all()
        )

    rows = "".join(
        f"<tr><td>{item.id}</td><td>{item.ticker}</td><td>{item.price}</td><td>{item.timestamp}</td></tr>"
        for item in data
    )

    if not rows:
        rows = "<tr><td colspan='4'>Нет данных</td></tr>"

    return f"""
    <html>
    <body>
        <center>
            <table border="1">
                <tr>
                    <th>id</th>
                    <th>ticker</th>
                    <th>price</th>
                    <th>timestamp</th>
                </tr>
                {rows}
            </table>
        </center>
    </body>
    </html>
    """


@router.get("/ui/price/latest", response_class=HTMLResponse)
def ui_latest_price(ticker: str = Query(...)):
    with SessionLocal() as session:
        item = (
            session.query(Price)
            .filter(Price.ticker == ticker)
            .order_by(Price.timestamp.desc())
            .first()
        )

    if not item:
        rows = "<tr><td colspan='4'>Нет данных</td></tr>"
    else:
        rows = f"<tr><td>{item.id}</td><td>{item.ticker}</td><td>{item.price}</td><td>{item.timestamp}</td></tr>"

    return f"""
    <html>
    <body>
        <center>
            <table border="1">
                <tr>
                    <th>id</th>
                    <th>ticker</th>
                    <th>price</th>
                    <th>timestamp</th>
                </tr>
                {rows}
            </table>
        </center>
    </body>
    </html>
    """


@router.get("/ui/price/by-date", response_class=HTMLResponse)
def ui_price_by_date(
    ticker: str = Query(...),
    start: int = Query(...),
    end: int = Query(...)
):
    with SessionLocal() as session:
        data = (
            session.query(Price)
            .filter(
                Price.ticker == ticker,
                Price.timestamp >= start,
                Price.timestamp <= end
            )
            .all()
        )

    rows = "".join(
        f"<tr><td>{item.id}</td><td>{item.ticker}</td><td>{item.price}</td><td>{item.timestamp}</td></tr>"
        for item in data
    )

    if not rows:
        rows = "<tr><td colspan='4'>Нет данных</td></tr>"

    return f"""
    <html>
    <body>
        <center>
            <table border="1">
                <tr>
                    <th>id</th>
                    <th>ticker</th>
                    <th>price</th>
                    <th>timestamp</th>
                </tr>
                {rows}
            </table>
        </center>
    </body>
    </html>
    """