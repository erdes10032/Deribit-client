import aiohttp
import hashlib
import json
from app.core.config import settings
from redis.asyncio import Redis


class AIService:
    BASE_URL = "https://openrouter.ai/api/v1/chat/completions"

    CACHE_TTL_SECONDS = 600

    def __init__(self):
        # Кеш храним в Redis, чтобы ответы ИИ не генерировались повторно.
        try:
            self._redis = Redis.from_url(settings.redis_url, decode_responses=True)
        except Exception:
            self._redis = None

    async def predict(self, ticker: str, prices: list[float]) -> str:
        if not prices:
            return "Нет данных для прогноза"

        # Ключ кеша: тикер + последние цены (округляем для стабильности).
        normalized = [round(float(p), 8) for p in prices]
        payload = json.dumps(normalized, separators=(",", ":"), ensure_ascii=False)
        digest = hashlib.sha256(payload.encode("utf-8")).hexdigest()
        cache_key = f"ai:prediction:{ticker}:{digest}"

        if self._redis is not None:
            try:
                cached = await self._redis.get(cache_key)
                if cached:
                    return cached
            except Exception:
                # Если Redis временно недоступен — просто делаем запрос к ИИ.
                pass

        prompt = f"""
Ты аналитик крипторынка.

Вот последние цены для {ticker}:
{prices}

Сделай краткий прогноз (1-2 предложения):
- будет рост или падение
- краткое объяснение
"""

        headers = {
            "Authorization": f"Bearer {settings.OPENROUTER_API_KEY}",
            "Content-Type": "application/json"
        }

        payload = {
            "model": "openai/gpt-4o-mini",
            "messages": [
                {"role": "user", "content": prompt}
            ]
        }

        async with aiohttp.ClientSession() as session:
            async with session.post(self.BASE_URL, json=payload, headers=headers) as resp:
                data = await resp.json()
                result = data["choices"][0]["message"]["content"]

                if self._redis is not None:
                    try:
                        await self._redis.set(
                            cache_key,
                            result,
                            ex=self.CACHE_TTL_SECONDS,
                        )
                    except Exception:
                        pass

                return result