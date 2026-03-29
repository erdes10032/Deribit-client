import aiohttp
from app.core.config import settings


class TelegramService:
    BASE_URL = "https://api.telegram.org"

    def __init__(self):
        self.token = settings.TELEGRAM_BOT_TOKEN

    async def send_message(self, telegram_user_id: int | str, text: str):
        url = f"{self.BASE_URL}/bot{self.token}/sendMessage"

        try:
            timeout = aiohttp.ClientTimeout(total=15)
            async with aiohttp.ClientSession(timeout=timeout) as session:
                async with session.post(
                    url,
                    json={
                        "chat_id": str(telegram_user_id),
                        "text": text,
                    },
                ) as resp:
                    data = await resp.json(content_type=None)
                    if not data.get("ok", False):
                        print(f"[TELEGRAM][ERROR] sendMessage failed: {data}")
        except Exception as e:
            # Сетевые ошибки не сломают бота.
            print(f"[TELEGRAM][ERROR] sendMessage exception: {e}")

    async def send_photo(
        self,
        telegram_user_id: int | str,
        file_path: str,
        caption: str = "",
    ):
        url = f"{self.BASE_URL}/bot{self.token}/sendPhoto"

        try:
            timeout = aiohttp.ClientTimeout(total=30)
            async with aiohttp.ClientSession(timeout=timeout) as session:
                with open(file_path, "rb") as photo:
                    data = aiohttp.FormData()
                    data.add_field("chat_id", str(telegram_user_id))
                    data.add_field("caption", caption)
                    data.add_field("photo", photo, filename="chart.png")

                    async with session.post(url, data=data) as resp:
                        response_data = await resp.json(content_type=None)
                        if not response_data.get("ok", False):
                            print(f"[TELEGRAM][ERROR] sendPhoto failed: {response_data}")
        except Exception as e:
            print(f"[TELEGRAM][ERROR] sendPhoto exception: {e}")