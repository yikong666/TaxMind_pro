from __future__ import annotations

from pathlib import Path

import pytest
from pydantic import SecretStr, ValidationError

from taxmind.bootstrap.settings import Settings, validate_runtime_settings
from taxmind.shared.domain.errors import DomainError


def test_settings_resolve_repository_log_directory() -> None:
    settings = Settings(app_env="test", log_dir=Path("var/log/taxmind"))

    assert settings.log_dir.is_absolute()
    assert settings.log_dir.as_posix().endswith("TaxMind_pro/var/log/taxmind")


def test_settings_normalize_log_level() -> None:
    assert Settings(log_level="warning").log_level == "WARNING"


def test_settings_reject_unknown_log_level() -> None:
    with pytest.raises(ValidationError):
        Settings(log_level="verbose")


def test_dashscope_model_is_restricted_to_approved_models() -> None:
    assert Settings(dashscope_llm_model="qwen3-max").dashscope_llm_model == "qwen3-max"

    with pytest.raises(ValidationError):
        Settings(dashscope_llm_model="unapproved-model")


def test_production_rejects_placeholder_secret() -> None:
    settings = Settings(
        app_env="production",
        app_debug=False,
        web_origin="https://taxmind.example",
    )

    with pytest.raises(DomainError) as error:
        validate_runtime_settings(settings)

    assert error.value.code == "CONFIGURATION_INVALID"


def test_production_accepts_safe_bootstrap_settings() -> None:
    settings = Settings(
        app_env="production",
        app_debug=False,
        web_origin="https://taxmind.example",
        jwt_secret=SecretStr("a-secure-random-value-with-more-than-32-bytes"),
    )

    validate_runtime_settings(settings)
