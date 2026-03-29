from fastapi import APIRouter, Query, HTTPException
from fastapi.responses import HTMLResponse, FileResponse
from app.db.database import SessionLocal
from app.db.models import Price
from app.schemas.price import PriceResponse
from app.core.tickers import SUPPORTED_TICKERS
from app.services.ai_service import AIService
from app.services.chart_service import ChartService

import os

router = APIRouter()


@router.get("/", response_class=HTMLResponse)
def index():
    tickers_options = "".join(
        f'<option value="{t}">{t}</option>' for t in SUPPORTED_TICKERS
    )
    tickers_js = "[" + ", ".join(f"'{t}'" for t in SUPPORTED_TICKERS) + "]"
    html = """
    <!doctype html>
    <html lang="ru">
    <head>
        <meta charset="utf-8">
        <title>Deribit Prices</title>
    </head>
    <body>
        <center>
        <h1>Deribit Price Viewer</h1>

        <p>Работа с API</p>

        <h2>История цен</h2>
        <form method="get" action="/ui/prices" target="result">
            <label>Ticker:</label>
            <select name="ticker" required>
                __TICKERS_OPTIONS__
            </select>
            <button type="submit">Показать</button>
        </form>

        <h2>Последняя цена</h2>
        <form method="get" action="/ui/price/latest" target="result">
            <label>Ticker:</label>
            <select name="ticker" required>
                __TICKERS_OPTIONS__
            </select>
            <button type="submit">Показать</button>
        </form>

        <h2>Цена по диапазону времени</h2>
        <form method="get" action="/ui/price/by-date" target="result">
            <label>Ticker:</label>
            <select name="ticker" required>
                __TICKERS_OPTIONS__
            </select><br>

            <label>Start (timestamp):</label>
            <input name="start" type="number" required><br>

            <label>End (timestamp):</label>
            <input name="end" type="number" required><br>

            <button type="submit">Показать</button>
        </form>

        <h2>Графики</h2>

        <select id="chartSelect">
            <option>Загрузка...</option>
        </select>
        <select id="fullChartTickerSelect">
            __TICKERS_OPTIONS__
        </select>
        <button type="button" onclick="loadFullChart()">Полный график</button>

        <br><br>

        <img id="chartImage" width="800"/>

        <h2>Прогноз ИИ</h2>
        <label>Тикер:</label>
        <select id="forecastSelect">
            __TICKERS_OPTIONS__
        </select>
        <button type="button" onclick="loadPrediction()">прогноз</button>
        <br><br>
        <pre id="predictionResult"></pre>

        <h2>Последние цены</h2>
        <table border="1" style="border-collapse:collapse;">
            <thead>
                <tr>
                    <th>ticker</th>
                    <th>price</th>
                    <th>timestamp</th>
                </tr>
            </thead>
            <tbody id="latestPricesBody"></tbody>
        </table>

        <h2>Результат</h2>
        <iframe name="result" width="100%" height="400"></iframe>

        <script>
        async function loadCharts() {
            const res = await fetch('/charts');
            const data = await res.json();

            const select = document.getElementById('chartSelect');
            select.innerHTML = "";

            data.charts.forEach(chart => {
                const option = document.createElement('option');
                option.value = chart.filename;
                option.text = chart.label;
                select.appendChild(option);
            });

            select.onchange = () => {
                const img = document.getElementById('chartImage');
                img.src = '/charts/' + select.value;
            };

            if (data.charts.length > 0) {
                select.dispatchEvent(new Event('change'));
            }
        }

        const tickers = __TICKERS_JS__;

        async function loadLatestPrices() {
            const body = document.getElementById('latestPricesBody');
            body.innerHTML = "";

            for (const ticker of tickers) {
                try {
                    const res = await fetch('/price/latest?ticker=' + encodeURIComponent(ticker));
                    const data = await res.json();
                    if (!data) continue;

                    const row = document.createElement('tr');
                    row.innerHTML =
                        '<td>' + data.ticker + '</td>' +
                        '<td>' + data.price + '</td>' +
                        '<td>' + data.timestamp + '</td>';
                    body.appendChild(row);
                } catch (e) {
                    // ignore
                }
            }
        }

        async function loadPrediction() {
            const ticker = document.getElementById('forecastSelect').value;
            const el = document.getElementById('predictionResult');
            el.textContent = "Загрузка...";

            try {
                const res = await fetch('/prediction?ticker=' + encodeURIComponent(ticker));
                const data = await res.json();
                el.textContent = data.prediction || "Нет ответа";
            } catch (e) {
                el.textContent = "Ошибка при загрузке прогноза";
            }
        }

        function loadFullChart() {
            const ticker = document.getElementById('fullChartTickerSelect').value;
            const img = document.getElementById('chartImage');
            img.src = '/charts/full?ticker=' + encodeURIComponent(ticker) + '&_ts=' + Date.now();
        }

        loadCharts();
        loadLatestPrices();
        </script>

        </center>
    </body>
    </html>
    """

    return (
        html.replace("__TICKERS_OPTIONS__", tickers_options).replace("__TICKERS_JS__", tickers_js)
    )


# API

@router.get("/prices", response_model=list[PriceResponse])
def get_prices(ticker: str = Query(...)):
    with SessionLocal() as session:
        return (
            session.query(Price)
            .filter(Price.ticker == ticker)
            .all()
        )


@router.get("/price/latest", response_model=PriceResponse | None)
def get_latest_price(ticker: str = Query(...)):
    with SessionLocal() as session:
        return (
            session.query(Price)
            .filter(Price.ticker == ticker)
            .order_by(Price.timestamp.desc())
            .first()
        )


@router.get("/price/by-date", response_model=list[PriceResponse])
def get_price_by_date(
    ticker: str = Query(...),
    start: int = Query(...),
    end: int = Query(...)
):
    with SessionLocal() as session:
        return (
            session.query(Price)
            .filter(
                Price.ticker == ticker,
                Price.timestamp >= start,
                Price.timestamp <= end
            )
            .all()
        )


#  UI

@router.get("/ui/prices", response_class=HTMLResponse)
def ui_prices(ticker: str = Query(...)):
    with SessionLocal() as session:
        data = (
            session.query(Price)
            .filter(Price.ticker == ticker)
            .all()
        )

    rows = "".join(
        f"<tr><td>{i.id}</td><td>{i.ticker}</td><td>{i.price}</td><td>{i.timestamp}</td></tr>"
        for i in data
    ) or "<tr><td colspan='4'>Нет данных</td></tr>"

    return table_html(rows)


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

    return table_html(rows)


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
        f"<tr><td>{i.id}</td><td>{i.ticker}</td><td>{i.price}</td><td>{i.timestamp}</td></tr>"
        for i in data
    ) or "<tr><td colspan='4'>Нет данных</td></tr>"

    return table_html(rows)


def table_html(rows: str) -> str:
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


# ГРАФИКИ

@router.get("/charts")
def list_charts():
    folder = "charts"

    if not os.path.exists(folder):
        return {"charts": []}

    files = sorted(os.listdir(folder), reverse=True)

    result = []

    for file in files:
        try:
            parts = file.replace(".png", "").split("__")

            ticker = parts[0]
            start = parts[1]
            end = parts[2]

            date, time = start.split("_")

            label = f"{ticker} | {date}: {time.replace('-', ':')}-{end.replace('-', ':')}"

            result.append({
                "filename": file,
                "label": label
            })

        except Exception:
            continue

    return {"charts": result}


@router.get("/charts/full")
def get_full_chart(ticker: str = Query(...)):
    ticker = ticker.lower()
    if ticker not in SUPPORTED_TICKERS:
        raise HTTPException(status_code=400, detail="Неверный тикер")

    with SessionLocal() as session:
        prices = (
            session.query(Price)
            .filter(Price.ticker == ticker)
            .order_by(Price.timestamp.asc())
            .all()
        )

    chart_path = ChartService().build_full_chart(ticker, prices)
    if not chart_path:
        raise HTTPException(status_code=404, detail="Недостаточно данных для построения графика")

    return FileResponse(chart_path)


@router.get("/charts/{filename}")
def get_chart(filename: str):
    return FileResponse(os.path.join("charts", filename))

@router.get("/prediction")
async def get_prediction(ticker: str = Query(...)):
    ticker = ticker.lower()
    if ticker not in SUPPORTED_TICKERS:
        raise HTTPException(
            status_code=400,
            detail="Неподдерживаемый тикер. Поддерживаются: " + ", ".join(SUPPORTED_TICKERS),
        )
    db = SessionLocal()

    try:
        prices = (
            db.query(Price)
            .filter(Price.ticker == ticker)
            .order_by(Price.timestamp.desc())
            .limit(10)
            .all()
        )
    finally:
        db.close()

    values = [p.price for p in prices]

    ai = AIService()
    result = await ai.predict(ticker, values)

    return {"prediction": result}