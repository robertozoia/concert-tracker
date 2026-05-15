from __future__ import annotations

from datetime import date
from pathlib import Path

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_password_hash: str = Field(..., description="Bcrypt hash of the shared password")
    secret_key: str = Field(..., description="URLSafeTimedSerializer secret")

    db_path: str = "./data/concerts.db"

    end_date: date | None = None
    scrape_hour: int = 4
    timezone: str = "America/Mexico_City"

    @field_validator("end_date", mode="before")
    @classmethod
    def _empty_str_to_none(cls, value):
        if isinstance(value, str) and not value.strip():
            return None
        return value

    session_max_age: int = 60 * 60 * 24 * 30
    session_cookie_name: str = "concert_session"

    listen_port: int = 8090

    songkick_base_url: str = "https://www.songkick.com"
    songkick_metro_path: str = "/es/metro-areas/34385-mexico-mexico-city"
    user_agent: str = (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36"
    )

    def resolved_end_date(self) -> date | None:
        """Upper bound for scraping/filtering. None means "no upper limit"."""
        return self.end_date

    def sqlite_url(self) -> str:
        path = Path(self.db_path).expanduser()
        path.parent.mkdir(parents=True, exist_ok=True)
        return f"sqlite:///{path}"


settings = Settings()  # type: ignore[call-arg]
