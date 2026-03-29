import aiohttp
from app.core.config import settings


class TelegramService:
    BASE_URL = "https://api.telegram.org"

    def __init__(self):
        self.token = settings.TELEGRAM_BOT_TOKEN

    async def send_message(self, telegram_user_id: int | str, text: str):
        url = f"{self.BASE_URL}/bot{self.token}/sendMessage"

        async with aiohttp.ClientSession() as session:
            await session.post(
                url,
                json={
                    "chat_id": str(telegram_user_id),
                    "text": text,
                },
            )

    async def send_photo(
        self,
        telegram_user_id: int | str,
        file_path: str,
        caption: str = "",
    ):
        url = f"{self.BASE_URL}/bot{self.token}/sendPhoto"

        async with aiohttp.ClientSession() as session:
            with open(file_path, "rb") as photo:
                data = aiohttp.FormData()
                data.add_field("chat_id", str(telegram_user_id))
                data.add_field("caption", caption)
                data.add_field("photo", photo, filename="chart.png")

                await session.post(url, data=data)