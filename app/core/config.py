from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

PROJECT_ROOT = Path(__file__).resolve().parents[2]
ROOT_ENV_FILE = PROJECT_ROOT / ".env"


class Settings(BaseSettings):
    app_name: str = "CaiBao"
    app_version: str = "0.12.1"
    app_env: str = "dev"
    api_prefix: str = "/api/v1"
    database_url: str = "sqlite:///./CaiBao.db"
    dev_admin_enabled: bool = True
    dev_admin_account_id: str = "dev_admin"
    dev_admin_display_name: str = "Developer Admin"
    dev_admin_token: str = "dev-admin-token"

    llm_provider: str = "mock"
    llm_base_url: str = "https://api.openai.com/v1"
    llm_api_key: str | None = None
    llm_model: str = "gpt-4.1-mini"
    llm_temperature: float = 0.2
    llm_max_tokens: int = 2048
    llm_timeout_seconds: float = 30.0

    embedding_provider: str = "mock"
    embedding_base_url: str = "https://api.openai.com/v1"
    embedding_api_key: str | None = None
    embedding_model: str = "text-embedding-3-small"
    embedding_mock_dim: int = 256
    embedding_batch_size: int = 32
    embedding_timeout_seconds: float = 30.0
    upload_root_dir: str = "data/uploads"
    upload_max_file_size_mb: int = 20

    model_config = SettingsConfigDict(
        env_file=str(ROOT_ENV_FILE),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    @classmethod
    def settings_customise_sources(
        cls,
        settings_cls,
        init_settings,
        env_settings,
        dotenv_settings,
        file_secret_settings,
    ):
        # Keep standard priority: init args > env vars > .env > file secrets.
        # Root .env path is fixed via model_config.env_file above.
        return init_settings, env_settings, dotenv_settings, file_secret_settings


@lru_cache
def get_settings() -> Settings:
    return Settings()


def reload_settings() -> Settings:
    get_settings.cache_clear()
    return get_settings()
