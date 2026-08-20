from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import AnyHttpUrl, Field, SecretStr, model_validator
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
    metrics_enabled: bool = True
    metrics_bearer_token: SecretStr | None = None
    otel_service_name: str = "liara-assistant-api"
    otel_exporter_otlp_endpoint: AnyHttpUrl | None = None
    web_origin: AnyHttpUrl = AnyHttpUrl("http://localhost:3000")
    api_internal_token: SecretStr | None = None
    docs_repo_path: Path = Path("/workspace/docs")
    docs_public_base_url: AnyHttpUrl = AnyHttpUrl("https://docs.liara.ir")

    database_url: SecretStr | None = None
    redis_url: SecretStr | None = None
    session_ttl_seconds: int = Field(default=7200, ge=300, le=86400)
    session_max_turns: int = Field(default=24, ge=2, le=100)
    session_summary_after_turns: int = Field(default=10, ge=4, le=80)

    llm_provider: str | None = None
    llm_base_url: AnyHttpUrl | None = None
    llm_api_key: SecretStr | None = None
    llm_backup_base_url: AnyHttpUrl | None = None
    llm_backup_api_key: SecretStr | None = None
    llm_small_model: str | None = None
    llm_large_model: str | None = None
    llm_request_timeout_seconds: float = Field(default=60, gt=0, le=300)
    llm_max_retries: int = Field(default=2, ge=0, le=5)
    provider_circuit_failure_threshold: int = Field(default=3, ge=1, le=20)
    provider_circuit_reset_seconds: float = Field(default=30, ge=1, le=600)
    provider_concurrency_limit: int = Field(default=8, ge=1, le=100)
    provider_queue_timeout_seconds: float = Field(default=2, gt=0, le=30)
    response_cache_ttl_seconds: int = Field(default=900, ge=0, le=86400)

    embedding_provider: str | None = None
    embedding_base_url: AnyHttpUrl | None = None
    embedding_api_key: SecretStr | None = None
    embedding_backup_base_url: AnyHttpUrl | None = None
    embedding_backup_api_key: SecretStr | None = None
    embedding_model: str | None = None
    embedding_dimensions: int | None = Field(default=None, gt=0)
    embedding_batch_size: int = Field(default=64, ge=1, le=256)

    max_user_input_chars: int = Field(default=4000, ge=100, le=20000)
    max_request_bytes: int = Field(default=65536, ge=1024, le=1048576)
    readiness_timeout_seconds: float = Field(default=2.0, gt=0, le=10)
    retrieval_candidate_limit: int = Field(default=30, ge=5, le=100)
    evidence_limit: int = Field(default=6, ge=1, le=12)
    rrf_k: int = Field(default=60, ge=1, le=200)
    evidence_min_score: float = Field(default=0.025, gt=0, le=1)
    evidence_min_query_coverage: float = Field(default=0.35, ge=0, le=1)
    max_evidence_tokens: int = Field(default=5000, ge=500, le=20000)
    max_context_tokens: int = Field(default=12000, ge=1000, le=50000)
    max_provider_input_tokens: int = Field(default=16000, ge=2000, le=100000)
    rate_limit_anonymous_per_minute: int = Field(default=10, ge=1, le=1000)
    rate_limit_anonymous_per_hour: int = Field(default=60, ge=1, le=10000)
    max_output_tokens_small: int = Field(default=700, ge=100, le=8000)
    max_output_tokens_large: int = Field(default=1200, ge=100, le=16000)
    llm_small_input_usd_per_million: float = Field(default=0, ge=0)
    llm_small_output_usd_per_million: float = Field(default=0, ge=0)
    llm_large_input_usd_per_million: float = Field(default=0, ge=0)
    llm_large_output_usd_per_million: float = Field(default=0, ge=0)
    support_ticket_url: AnyHttpUrl = AnyHttpUrl(
        "https://console.liara.ir/tickets/create"
    )

    @property
    def allowed_origins(self) -> list[str]:
        return [str(self.web_origin).rstrip("/")]

    @model_validator(mode="after")
    def validate_production_configuration(self) -> "Settings":
        if self.app_env != "production":
            return self
        required = {
            "API_INTERNAL_TOKEN": self.api_internal_token,
            "DATABASE_URL": self.database_url,
            "REDIS_URL": self.redis_url,
            "LLM_BASE_URL": self.llm_base_url,
            "LLM_API_KEY": self.llm_api_key,
            "LLM_SMALL_MODEL": self.llm_small_model,
            "LLM_LARGE_MODEL": self.llm_large_model,
            "EMBEDDING_BASE_URL": self.embedding_base_url,
            "EMBEDDING_API_KEY": self.embedding_api_key,
            "EMBEDDING_MODEL": self.embedding_model,
            "EMBEDDING_DIMENSIONS": self.embedding_dimensions,
        }
        if self.metrics_enabled:
            required["METRICS_BEARER_TOKEN"] = self.metrics_bearer_token
        missing = sorted(name for name, value in required.items() if value is None)
        if missing:
            raise ValueError(
                "production configuration is missing: " + ", ".join(missing)
            )
        if self.web_origin.scheme != "https":
            raise ValueError("WEB_ORIGIN must use https in production")
        prices = (
            self.llm_small_input_usd_per_million,
            self.llm_small_output_usd_per_million,
            self.llm_large_input_usd_per_million,
            self.llm_large_output_usd_per_million,
        )
        if any(price <= 0 for price in prices):
            raise ValueError("production model prices must be greater than zero")
        return self


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
