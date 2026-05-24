from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    APP_NAME: str = "AI Agent Orchestration Platform"
    DEBUG: bool = False
    DATABASE_URL: str = "sqlite+aiosqlite:///./agents.db"

    # LLM
    OPENAI_API_KEY: str = ""
    DEFAULT_MODEL: str = "gpt-4o-mini"

    # Telegram
    TELEGRAM_BOT_TOKEN: Optional[str] = None

    # Slack
    SLACK_BOT_TOKEN: Optional[str] = None
    SLACK_APP_TOKEN: Optional[str] = None

    # Security
    SECRET_KEY: str = "changeme-in-production"

    class Config:
        env_file = ".env"


settings = Settings()
