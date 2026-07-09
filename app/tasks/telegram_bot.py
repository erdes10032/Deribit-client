import asyncio
import time

import aiohttp

from app.agents.market_agent import MarketAgent
from app.core.config import settings
from app.core.chart_intervals import (
    ALLOWED_INTERVALS_MINUTES,
    DEFAULT_INTERVAL_SECONDS,
    format_interval,
    is_valid_interval_minutes,
    minutes_to_seconds,
)
from app.core.tickers import SUPPORTED_TICKERS
from app.db.database import SessionLocal
from app.db.models import NotificationSubscription, Price
from app.services.ai_service import AIService
from app.services.chart_service import ChartService
from app.services.telegram_service import TelegramService


BOT_TOKEN = settings.TELEGRAM_BOT_TOKEN
BASE_URL = f"https://api.telegram.org/bot{BOT_TOKEN}"

HELP_TEXT = (
    "Доступные команды:\n"
    "/subscribe <тикер> [минуты] - подписаться на валюту (5/10/15/30/60)\n"
    "/tickers - все доступные тикеры\n"
    "/full_graph <тикер> - построить полный график\n"
    "/subscriptions - все подписки на валюты\n"
    "/chart_interval [тикер] <минуты> - периодичность графиков (5/10/15/30/60)\n"
    "/prediction <тикер> - AI анализ цен\n"
    "/help — помощь"
)


def _extract_telegram_user_id(message: dict) -> int | None:
    from_ = message.get("from") or {}
    user_id = from_.get("id")
    return int(user_id) if user_id is not None else None


def _normalize_ticker(ticker: str) -> str:
    return ticker.strip().lower()


def _format_subscription(subscription: NotificationSubscription) -> str:
    interval = subscription.chart_interval_seconds or DEFAULT_INTERVAL_SECONDS
    return f"{subscription.ticker} (графики каждые {format_interval(interval)})"


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

    if command in ("/start", "/help"):
        greeting = "Привет! Я бот для уведомлений по криптовалютам.\n\n" if command == "/start" else ""
        await tg.send_message(telegram_user_id, greeting + HELP_TEXT)
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
            subscriptions = (
                db.query(NotificationSubscription)
                .filter(NotificationSubscription.telegram_user_id == telegram_user_id)
                .order_by(NotificationSubscription.ticker.asc())
                .all()
            )
        finally:
            db.close()

        if not subscriptions:
            await tg.send_message(telegram_user_id, "Пока вы ни на какие тикеры не подписаны.")
        else:
            lines = "\n".join(f"• {_format_subscription(sub)}" for sub in subscriptions)
            await tg.send_message(telegram_user_id, "Ваши подписки:\n" + lines)
        return

    if command == "/chart_interval":
        allowed = ", ".join(str(m) for m in ALLOWED_INTERVALS_MINUTES)

        if len(parts) == 1:
            db = SessionLocal()
            try:
                subscriptions = (
                    db.query(NotificationSubscription)
                    .filter(NotificationSubscription.telegram_user_id == telegram_user_id)
                    .order_by(NotificationSubscription.ticker.asc())
                    .all()
                )
            finally:
                db.close()

            if not subscriptions:
                await tg.send_message(
                    telegram_user_id,
                    f"Сначала подпишитесь на тикер: /subscribe eth_usd\n"
                    f"Доступные интервалы (мин): {allowed}",
                )
                return

            lines = "\n".join(f"• {_format_subscription(sub)}" for sub in subscriptions)
            await tg.send_message(
                telegram_user_id,
                "Текущая периодичность графиков:\n" + lines + f"\n\nДоступные интервалы (мин): {allowed}",
            )
            return

        if len(parts) == 2:
            try:
                minutes = int(parts[1])
            except ValueError:
                await tg.send_message(
                    telegram_user_id,
                    f"Укажите минуты: /chart_interval 10\nДоступные интервалы: {allowed}",
                )
                return

            if not is_valid_interval_minutes(minutes):
                await tg.send_message(
                    telegram_user_id,
                    f"Недопустимый интервал. Доступные значения (мин): {allowed}",
                )
                return

            interval_seconds = minutes_to_seconds(minutes)
            db = SessionLocal()
            try:
                subscriptions = (
                    db.query(NotificationSubscription)
                    .filter(NotificationSubscription.telegram_user_id == telegram_user_id)
                    .all()
                )
                if not subscriptions:
                    await tg.send_message(telegram_user_id, "Сначала подпишитесь на тикер: /subscribe eth_usd")
                    return

                for subscription in subscriptions:
                    subscription.chart_interval_seconds = interval_seconds
                    subscription.last_chart_sent_at = int(time.time())
                db.commit()
            finally:
                db.close()

            await tg.send_message(
                telegram_user_id,
                f"Периодичность графиков для всех подписок: каждые {minutes} мин.",
            )
            return

        ticker = _normalize_ticker(parts[1])
        if ticker not in SUPPORTED_TICKERS:
            await tg.send_message(telegram_user_id, "Неверный тикер")
            return

        try:
            minutes = int(parts[2])
        except (IndexError, ValueError):
            await tg.send_message(
                telegram_user_id,
                f"Укажите минуты: /chart_interval {ticker} 15\nДоступные интервалы: {allowed}",
            )
            return

        if not is_valid_interval_minutes(minutes):
            await tg.send_message(
                telegram_user_id,
                f"Недопустимый интервал. Доступные значения (мин): {allowed}",
            )
            return

        interval_seconds = minutes_to_seconds(minutes)
        db = SessionLocal()
        try:
            subscription = (
                db.query(NotificationSubscription)
                .filter(
                    NotificationSubscription.telegram_user_id == telegram_user_id,
                    NotificationSubscription.ticker == ticker,
                )
                .first()
            )
            if not subscription:
                await tg.send_message(telegram_user_id, f"Вы не подписаны на {ticker}. Используйте /subscribe {ticker}")
                return

            subscription.chart_interval_seconds = interval_seconds
            subscription.last_chart_sent_at = int(time.time())
            db.commit()
        finally:
            db.close()

        await tg.send_message(
            telegram_user_id,
            f"Периодичность графиков для {ticker}: каждые {minutes} мин.",
        )
        return

    if command == "/subscribe":
        if not arg:
            await tg.send_message(telegram_user_id, "Укажите тикер: /subscribe eth_usd [15]")
            return

        ticker = _normalize_ticker(arg)
        if ticker not in SUPPORTED_TICKERS:
            await tg.send_message(telegram_user_id, "Неверный тикер")
            return

        interval_seconds = DEFAULT_INTERVAL_SECONDS
        if len(parts) >= 3:
            allowed = ", ".join(str(m) for m in ALLOWED_INTERVALS_MINUTES)
            try:
                minutes = int(parts[2])
            except ValueError:
                await tg.send_message(
                    telegram_user_id,
                    f"Укажите минуты числом. Доступные интервалы: {allowed}",
                )
                return

            if not is_valid_interval_minutes(minutes):
                await tg.send_message(
                    telegram_user_id,
                    f"Недопустимый интервал. Доступные значения (мин): {allowed}",
                )
                return

            interval_seconds = minutes_to_seconds(minutes)

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
                    chart_interval_seconds=interval_seconds,
                    last_chart_sent_at=int(time.time()),
                )
            )
            db.commit()
        finally:
            db.close()

        await tg.send_message(
            telegram_user_id,
            f"Оповещения для {ticker} включены. Графики каждые {format_interval(interval_seconds)}. "
            f"Изменить: /chart_interval {ticker} {interval_seconds // 60}",
        )

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
    if not BOT_TOKEN:
        raise RuntimeError("TELEGRAM_BOT_TOKEN is empty")

    print("[BOT] Telegram bot polling started")
    offset = 0

    async with aiohttp.ClientSession() as session:
        while True:
            url = f"{BASE_URL}/getUpdates?timeout=10&offset={offset}"

            try:
                async with session.get(url) as resp:
                    data = await resp.json()
            except Exception as e:
                print(f"[BOT][ERROR] getUpdates failed: {e}")
                await asyncio.sleep(2)
                continue

            if not data.get("ok", False):
                print(f"[BOT][ERROR] Telegram API error: {data}")
                await asyncio.sleep(2)
                continue

            for update in data["result"]:
                offset = update["update_id"] + 1

                if "message" in update:
                    try:
                        await handle_message(update["message"])
                    except Exception as e:
                        print(f"[BOT][ERROR] handle_message failed: {e}")


if __name__ == "__main__":
    asyncio.run(run_bot())
