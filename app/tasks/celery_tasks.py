import asyncio
import time
from collections import defaultdict

import aiohttp
from celery import Celery

from app.clients.deribit_client import DeribitClient
from app.db.database import SessionLocal
from app.db.models import NotificationSubscription, Price
from app.core.config import settings
from app.core.tickers import SUPPORTED_TICKERS
from app.core.chart_intervals import DEFAULT_INTERVAL_SECONDS, format_interval
from app.agents.market_agent import MarketAgent
from app.services.chart_service import ChartService
from app.services.telegram_service import TelegramService


celery = Celery(
    "deribit_tasks",
    broker=settings.redis_url,
    backend=settings.redis_url,
)


celery.conf.beat_schedule = {
    "fetch-prices-every-minute": {
        "task": "app.tasks.celery_tasks.fetch_prices",
        "schedule": 60.0,
    },
    "build-charts-every-minute": {
        "task": "app.tasks.celery_tasks.build_charts",
        "schedule": 60.0,
    },
    "notify-strong-changes-every-minute": {
        "task": "app.tasks.celery_tasks.notify_strong_changes",
        "schedule": 61.0,
    },
}

celery.conf.timezone = "UTC"


@celery.task(name="app.tasks.celery_tasks.fetch_prices")
def fetch_prices():
    async def fetch():
        async with aiohttp.ClientSession() as session:
            client = DeribitClient(session=session)

            results = {}

            for ticker in SUPPORTED_TICKERS:
                try:
                    price = await client.get_index_price(ticker)
                    results[ticker] = price
                except Exception as e:
                    print(f"[ERROR] {ticker}: {e}")

        timestamp = int(time.time())

        db_session = SessionLocal()

        try:
            for ticker, price in results.items():
                row = Price(
                    ticker=ticker,
                    price=price,
                    timestamp=timestamp,
                )
                db_session.add(row)

            db_session.commit()

        finally:
            db_session.close()

    asyncio.run(fetch())


@celery.task(name="app.tasks.celery_tasks.build_charts")
def build_charts():
    async def run():
        now = int(time.time())
        db_session = SessionLocal()
        chart_service = ChartService()
        telegram = TelegramService()

        try:
            subscriptions = db_session.query(NotificationSubscription).all()
            due_groups: dict[tuple[str, int], list[NotificationSubscription]] = defaultdict(list)

            for subscription in subscriptions:
                interval = subscription.chart_interval_seconds or DEFAULT_INTERVAL_SECONDS
                last_sent = subscription.last_chart_sent_at
                if last_sent is None or (now - last_sent) >= interval:
                    due_groups[(subscription.ticker, interval)].append(subscription)

            for (ticker, interval), subscribers in due_groups.items():
                window_end_ts = now
                window_start_ts = window_end_ts - interval

                prices = (
                    db_session.query(Price)
                    .filter(
                        Price.ticker == ticker,
                        Price.timestamp >= window_start_ts,
                        Price.timestamp <= window_end_ts,
                    )
                    .order_by(Price.timestamp.asc())
                    .all()
                )

                if len(prices) < 2:
                    print(f"[INFO] Not enough data for {ticker} ({format_interval(interval)})")
                    continue

                chart_path = chart_service.build_window_chart(
                    ticker=ticker,
                    prices=prices,
                    window_start_ts=window_start_ts,
                    window_end_ts=window_end_ts,
                )

                if not chart_path:
                    continue

                print(f"[INFO] Chart built: {chart_path}")
                interval_label = format_interval(interval)

                for subscription in subscribers:
                    await telegram.send_photo(
                        subscription.telegram_user_id,
                        chart_path,
                        caption=f"{ticker} chart ({interval_label})",
                    )
                    subscription.last_chart_sent_at = now

                db_session.commit()

        finally:
            db_session.close()

    asyncio.run(run())


@celery.task(name="app.tasks.celery_tasks.notify_strong_changes")
def notify_strong_changes():
    """
    Проверяет последние данные и отправляет текстовые сигналы
    только тем пользователям, которые подписаны на тикер.
    """

    ANALYSIS_POINTS = 10

    async def run():
        db_session = SessionLocal()
        telegram = TelegramService()
        agent = MarketAgent()

        try:
            subscribed_raw = (
                db_session.query(NotificationSubscription.ticker)
                .distinct()
                .all()
            )
            subscribed_tickers = [t[0] for t in subscribed_raw]

            if not subscribed_tickers:
                return

            for ticker in subscribed_tickers:
                prices = (
                    db_session.query(Price)
                    .filter(Price.ticker == ticker)
                    .order_by(Price.timestamp.desc())
                    .limit(ANALYSIS_POINTS)
                    .all()
                )

                if len(prices) < 2:
                    continue

                analysis = agent.analyze(prices)
                decision = agent.decide(analysis)
                if not decision:
                    continue

                subscribers_raw = (
                    db_session.query(NotificationSubscription.telegram_user_id)
                    .filter(NotificationSubscription.ticker == ticker)
                    .all()
                )
                subscribers = [u[0] for u in subscribers_raw]

                for telegram_user_id in subscribers:
                    await telegram.send_message(telegram_user_id, decision)
        finally:
            db_session.close()

    asyncio.run(run())
