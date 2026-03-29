import asyncio
import aiohttp

from app.agents.market_agent import MarketAgent
from app.core.config import settings
from app.core.tickers import SUPPORTED_TICKERS
from app.db.database import SessionLocal
from app.db.models import NotificationSubscription, Price
from app.services.ai_service import AIService
from app.services.chart_service import ChartService
from app.services.telegram_service import TelegramService


BOT_TOKEN = settings.TELEGRAM_BOT_TOKEN
BASE_URL = f"https://api.telegram.org/bot{BOT_TOKEN}"


def _extract_telegram_user_id(message: dict) -> int | None:
    from_ = message.get("from") or {}
    user_id = from_.get("id")
    return int(user_id) if user_id is not None else None


def _normalize_ticker(ticker: str) -> str:
    return ticker.strip().lower()


async def handle_message(message):
    telegram_user_id = _extract_telegram_user_id(message)
    if telegram_user_id is None:
        return

    text = (message.get("text") or "").strip()
    if not text:
        return

    parts = text.split()
    command = parts[0].lower()
    arg = parts[1].lower() if len(parts) > 1 else None

    tg = TelegramService()

    if command == "/start":
        await tg.send_message(
            telegram_user_id,
            "Привет! Я бот для уведомлений по криптовалютам.\n\n"
            "Команды:\n"
            "Доступные команды:\n"
            "/subscribe <тикер> - подписаться на валюту\n"
            "/tickers - все доступные тикеры\n "
            "/full_graph <тикер> - построить полный график\n"
            "/subscriptions - все подписки на валюты"
            "/prediction - AI анализ цен"
            "/help — помощь",
        )
        return

    if command == "/help":
        await tg.send_message(
            telegram_user_id,
            "Доступные команды:\n"
            "/subscribe <тикер> - подписаться на валюту\n"
            "/tickers - все доступные тикеры\n "
            "/full_graph <тикер> - построить полный график\n"
            "/subscriptions - все подписки на валюты"
            "/prediction - AI анализ цен",
        )
        return

    if command == "/tickers":
        await tg.send_message(
            telegram_user_id,
            "Доступные тикеры: " + ", ".join(SUPPORTED_TICKERS),
        )
        return

    if command == "/subscriptions":
        db = SessionLocal()
        try:
            tickers = (
                db.query(NotificationSubscription.ticker)
                .filter(NotificationSubscription.telegram_user_id == telegram_user_id)
                .all()
            )
            subscribed = sorted({t[0] for t in tickers})
        finally:
            db.close()

        if not subscribed:
            await tg.send_message(telegram_user_id, "Пока вы ни на какие тикеры не подписаны.")
        else:
            await tg.send_message(telegram_user_id, "Ваши подписки: " + ", ".join(subscribed))
        return

    if command == "/subscribe":
        if not arg:
            await tg.send_message(telegram_user_id, "Укажите тикер: /subscribe eth_usd")
            return

        ticker = _normalize_ticker(arg)
        if ticker not in SUPPORTED_TICKERS:
            await tg.send_message(telegram_user_id, "Неверный тикер")
            return

        db = SessionLocal()
        try:
            existing = (
                db.query(NotificationSubscription)
                .filter(
                    NotificationSubscription.telegram_user_id == telegram_user_id,
                    NotificationSubscription.ticker == ticker,
                )
                .first()
            )

            if existing:
                db.delete(existing)
                db.commit()
                await tg.send_message(telegram_user_id, f"Оповещения для {ticker} выключены.")
                return

            db.add(
                NotificationSubscription(
                    telegram_user_id=telegram_user_id,
                    ticker=ticker,
                )
            )
            db.commit()
        finally:
            db.close()

        await tg.send_message(telegram_user_id, f"Оповещения для {ticker} включены.")

        # Если прямо сейчас есть сильное изменение — отправим один раз сразу.
        prices = []
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

        if len(prices) >= 2:
            agent = MarketAgent()
            decision = agent.decide(agent.analyze(prices))
            if decision:
                await tg.send_message(telegram_user_id, decision)

        return

    if command == "/prediction":
        if not arg:
            await tg.send_message(telegram_user_id, "Укажите тикер: /prediction eth_usd")
            return

        ticker = _normalize_ticker(arg)
        if ticker not in SUPPORTED_TICKERS:
            await tg.send_message(telegram_user_id, "Неверный тикер")
            return

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
        prediction = await ai.predict(ticker, values)
        await tg.send_message(telegram_user_id, prediction)
        return

    if command == "/full_graph":
        if not arg:
            await tg.send_message(telegram_user_id, "Укажите тикер: /full_graph eth_usd")
            return

        ticker = _normalize_ticker(arg)
        if ticker not in SUPPORTED_TICKERS:
            await tg.send_message(telegram_user_id, "Неверный тикер")
            return

        db = SessionLocal()
        try:
            prices = (
                db.query(Price)
                .filter(Price.ticker == ticker)
                .order_by(Price.timestamp.asc())
                .all()
            )
        finally:
            db.close()

        chart_path = ChartService().build_full_chart(ticker, prices)
        if not chart_path:
            await tg.send_message(telegram_user_id, "Недостаточно данных для построения графика")
            return

        await tg.send_photo(
            telegram_user_id,
            chart_path,
            caption=f"{ticker} full chart",
        )
        return


async def run_bot():
    offset = 0

    async with aiohttp.ClientSession() as session:
        while True:
            url = f"{BASE_URL}/getUpdates?timeout=10&offset={offset}"

            async with session.get(url) as resp:
                data = await resp.json()

            for update in data["result"]:
                offset = update["update_id"] + 1

                if "message" in update:
                    await handle_message(update["message"])


if __name__ == "__main__":
    asyncio.run(run_bot())