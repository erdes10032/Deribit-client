import asyncio
import time

import aiohttp
from celery import Celery

from app.clients.deribit_client import DeribitClient
from app.db.database import SessionLocal
from app.db.models import Price
from app.core.config import settings


celery = Celery(
    "deribit_tasks",
    broker=settings.redis_url,
    backend=settings.redis_url,
)


celery.conf.beat_schedule = {
    "fetch-prices-every-minute": {
        "task": "app.tasks.celery_tasks.fetch_prices",
        "schedule": 60.0,
    }
}

celery.conf.timezone = "UTC"


@celery.task(name="app.tasks.celery_tasks.fetch_prices")
def fetch_prices():
    async def fetch():
        # Одна сессия aiohttp на выполнение задачи, переиспользуется для обоих запросов.
        async with aiohttp.ClientSession() as session:
            client = DeribitClient(session=session)

            btc_price = await client.get_index_price("btc_usd")
            eth_price = await client.get_index_price("eth_usd")

        timestamp = int(time.time())

        db_session = SessionLocal()

        try:
            btc = Price(
                ticker="btc_usd",
                price=btc_price,
                timestamp=timestamp,
            )

            eth = Price(
                ticker="eth_usd",
                price=eth_price,
                timestamp=timestamp,
            )

            db_session.add(btc)
            db_session.add(eth)

            db_session.commit()

        finally:
            db_session.close()

    asyncio.run(fetch())