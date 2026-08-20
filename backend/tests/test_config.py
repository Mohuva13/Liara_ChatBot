import pytest
from pydantic import ValidationError

from app.core.config import Settings


def test_production_fails_closed_when_secrets_are_missing() -> None:
    with pytest.raises(ValidationError, match="API_INTERNAL_TOKEN"):
        Settings(_env_file=None, app_env="production")
