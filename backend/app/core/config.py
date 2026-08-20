from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import AnyHttpUrl, Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=("../.env", ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    app_env: Literal["development", "test", "staging", "production"] = "development"
    log_level: str = "INFO"
    web_origin: AnyHttpUrl = AnyHttpUrl("http://localhost:3000")
    docs_repo_path: Path = Path("/workspace/docs")
    docs_public_base_url: AnyHttpUrl = AnyHttpUrl("https://docs.liara.ir")

    database_url: SecretStr | None = None
    redis_url: SecretStr | None = None
    session_ttl_seconds: int = Field(default=7200, ge=300, le=86400)
    session_max_turns: int = Field(default=24, ge=2, le=100)

    llm_provider: str | None = None
    llm_base_url: AnyHttpUrl | None = None
    llm_api_key: SecretStr | None = None
    llm_small_model: str | None = None
    llm_large_model: str | None = None
    llm_request_timeout_seconds: float = Field(default=60, gt=0, le=300)

    embedding_provider: str | None = None
    embedding_base_url: AnyHttpUrl | None = None
    embedding_api_key: SecretStr | None = None
    embedding_model: str | None = None
    embedding_dimensions: int | None = Field(default=None, gt=0)

    max_user_input_chars: int = Field(default=4000, ge=100, le=20000)
    max_request_bytes: int = Field(default=65536, ge=1024, le=1048576)
    readiness_timeout_seconds: float = Field(default=2.0, gt=0, le=10)

    @property
    def allowed_origins(self) -> list[str]:
        return [str(self.web_origin).rstrip("/")]


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
