from app.db.models import Price
from app.services.telegram_service import TelegramService


class MarketAgent:
    def __init__(self):
        self.telegram = TelegramService()

    def analyze(self, prices: list[Price]):
        if len(prices) < 2:
            return None

        prices = sorted(prices, key=lambda x: x.timestamp)

        first = prices[0].price
        last = prices[-1].price

        change_percent = ((last - first) / first) * 100

        return {
            "ticker": prices[-1].ticker,
            "first": first,
            "last": last,
            "change_percent": change_percent,
        }

    def decide(self, analysis: dict):
        if not analysis:
            return None

        change = analysis["change_percent"]

        if change > 2:
            return f"{analysis['ticker']} UP {change:.2f}%"

        if change < -2:
            return f"{analysis['ticker']} DOWN {change:.2f}%"

        return None

    async def act(self, decision: str, telegram_user_id: int | None = None):
        if not decision or telegram_user_id is None:
            return

        await self.telegram.send_message(telegram_user_id, decision)