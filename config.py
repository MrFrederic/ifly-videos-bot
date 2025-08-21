import os
import logging
from pathlib import Path
from typing import Any

class Config:
    """Configuration management for the bot using environment variables.

    Environment Variables:
      TELEGRAM_BOT_TOKEN        (required)
      TELEGRAM_IFLY_CHAT_ID     (required, int)
      DATABASE_PATH             (default: ./data/videos.db)
      SESSION_LENGTH_MINUTES    (default: 30)
      LOG_LEVEL                 (default: INFO)
    """

    def __init__(self):
        self._validate_required()

    def _validate_required(self):
        missing = []
        if not os.getenv("TELEGRAM_BOT_TOKEN"):
            missing.append("TELEGRAM_BOT_TOKEN")
        if not os.getenv("TELEGRAM_IFLY_CHAT_ID"):
            missing.append("TELEGRAM_IFLY_CHAT_ID")
        if missing:
            raise RuntimeError(f"Missing required environment variables: {', '.join(missing)}")

    @property
    def bot_token(self) -> str:
        return os.environ["TELEGRAM_BOT_TOKEN"]

    @property
    def ifly_chat_id(self) -> int:
        return int(os.environ["TELEGRAM_IFLY_CHAT_ID"])

    @property
    def database_path(self) -> str:
        return os.getenv("DATABASE_PATH", "./data/videos.db")

    @property
    def session_length_minutes(self) -> int:
        try:
            return int(os.getenv("SESSION_LENGTH_MINUTES", "30"))
        except ValueError:
            return 30

    @property
    def log_level(self) -> str:
        return os.getenv("LOG_LEVEL", "INFO").upper()
