from functools import lru_cache

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    database_url: str = ""
    openai_api_key: str = ""
    litellm_default_model: str = "gpt-4o-mini"
    # Optional: Brave Search API (https://brave.com/search/api). Works from cloud hosts where ddgs often returns nothing.
    brave_search_api_key: str = ""
    # Optional: Alpha Vantage (https://www.alphavantage.co/support/#api-key) for equity lookup and charts.
    alphavantage_api_key: str = ""

    @field_validator(
        "database_url",
        "openai_api_key",
        "litellm_default_model",
        "brave_search_api_key",
        "alphavantage_api_key",
        mode="before",
    )
    @classmethod
    def strip_whitespace(cls, value: object) -> object:
        if isinstance(value, str):
            return value.strip()
        return value


@lru_cache
def get_settings() -> Settings:
    return Settings()
