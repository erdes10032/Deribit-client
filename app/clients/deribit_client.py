import aiohttp


class DeribitClient:
    BASE_URL = "https://www.deribit.com/api/v2"

    def __init__(self, session: aiohttp.ClientSession | None = None):
        # Если сессию передали снаружи — используем её.
        # Если нет — создадим временную внутри вызова get_index_price.
        self.session = session

    async def get_index_price(self, ticker: str):
        endpoint = f"{self.BASE_URL}/public/get_index_price"
        params = {"index_name": ticker}

        # Если есть "длинная" сессия (например, созданная в Celery‑таске) — используем её.
        if self.session is not None:
            async with self.session.get(endpoint, params=params) as resp:
                data = await resp.json()
                return data["result"]["index_price"]

        # Иначе создаём краткоживущую сессию только для этого вызова.
        async with aiohttp.ClientSession() as session:
            async with session.get(endpoint, params=params) as resp:
                data = await resp.json()
                return data["result"]["index_price"]