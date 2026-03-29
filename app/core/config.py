from dotenv import load_dotenv
import os

load_dotenv()


class Settings:

    IN_DOCKER = os.environ.get('IN_DOCKER') == 'true' or os.path.exists('/.dockerenv')
    if IN_DOCKER:
        POSTGRES_HOST = 'db'
    else:
        POSTGRES_HOST = os.getenv('POSTGRES_HOST')

    REDIS_HOST: str = os.getenv("REDIS_HOST")
    REDIS_PORT: int = int(os.getenv("REDIS_PORT"))
    REDIS_USERNAME: str = os.getenv("REDIS_USERNAME")
    REDIS_PASSWORD: str = os.getenv("REDIS_PASSWORD")

    POSTGRES_DB: str = os.getenv("POSTGRES_DB")
    POSTGRES_USER: str = os.getenv("POSTGRES_USER")
    POSTGRES_PASSWORD: str = os.getenv("POSTGRES_PASSWORD")
    POSTGRES_HOST: str = POSTGRES_HOST
    POSTGRES_PORT: str = os.getenv("POSTGRES_PORT")

    TELEGRAM_BOT_TOKEN: str = os.getenv("TELEGRAM_BOT_TOKEN")
    TELEGRAM_CHAT_ID: str = os.getenv("TELEGRAM_CHAT_ID")

    OPENROUTER_API_KEY: str = os.getenv("OPENROUTER_API_KEY")

    @property
    def redis_url(self) -> str:
        return (
            f"redis://{self.REDIS_USERNAME}:{self.REDIS_PASSWORD}"
            f"@{self.REDIS_HOST}:{self.REDIS_PORT}/0"
        )

    @property
    def database_url(self) -> str:
        return (
            f"postgresql://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}"
            f"@{self.POSTGRES_HOST}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"
        )


settings = Settings()