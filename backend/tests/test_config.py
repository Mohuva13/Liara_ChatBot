import pytest
from pydantic import ValidationError

from app.core.config import Settings


def test_embedding_transport_has_independent_conservative_defaults() -> None:
    settings = Settings(_env_file=None)

    assert settings.embedding_batch_size == 16
    assert settings.embedding_request_timeout_seconds == 120


def test_production_fails_closed_when_secrets_are_missing() -> None:
    with pytest.raises(ValidationError, match="API_INTERNAL_TOKEN"):
        Settings(_env_file=None, app_env="production")
