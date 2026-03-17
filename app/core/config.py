from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "CaiBao"
    app_version: str = "0.1.0"
    app_env: str = "dev"
    api_prefix: str = "/api/v1"
    database_url: str = "sqlite:///./CaiBao.db"

    llm_provider: str = "mock"
    llm_base_url: str = "https://api.openai.com/v1"
    llm_api_key: str | None = None
    llm_model: str = "gpt-4.1-mini"
    llm_temperature: float = 0.2
    llm_max_tokens: int = 512
    llm_timeout_seconds: float = 30.0

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


@lru_cache
def get_settings() -> Settings:
    return Settings()