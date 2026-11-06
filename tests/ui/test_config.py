from datetime import date
from pathlib import Path

import pytest

from paypal_invoice_steward.ui.config import Settings, load_settings
from paypal_invoice_steward.ui.web import build_port


@pytest.fixture(autouse=True)
def clean_env(monkeypatch: pytest.MonkeyPatch, tmp_path: pytest.TempPathFactory) -> None:
    for name in (
        "PAYPAL_CLIENT_ID",
        "PAYPAL_CLIENT_SECRET",
        "PAYPAL_APP_ID",
        "STEWARD_MODE",
        "ANTHROPIC_API_KEY",
        "STEWARD_MAX_INVOICE",
        "STEWARD_REMINDER_COOLDOWN_DAYS",
        "STEWARD_SANDBOX_WRITES",
        "STEWARD_SANDBOX_LLM",
    ):
        monkeypatch.delenv(name, raising=False)
    monkeypatch.chdir(tmp_path)  # no stray .env file


def test_demo_mode_without_credentials() -> None:
    settings = load_settings()
    assert settings.mode == "demo" and not settings.llm_enabled


def test_loads_dotenv_from_current_working_directory(tmp_path: Path) -> None:
    (tmp_path / ".env").write_text(
        "PAYPAL_CLIENT_ID=id-from-dotenv\nPAYPAL_CLIENT_SECRET=secret-from-dotenv\n",
        encoding="utf-8",
    )

    settings = load_settings()

    assert settings.mode == "sandbox"
    assert settings.paypal_client_id == "id-from-dotenv"
    assert settings.paypal_client_secret == "secret-from-dotenv"


def test_sandbox_mode_with_credentials(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("PAYPAL_CLIENT_ID", "id")
    monkeypatch.setenv("PAYPAL_CLIENT_SECRET", "secret")
    assert load_settings().mode == "sandbox"


def test_sandbox_mode_requires_credentials(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("STEWARD_MODE", "sandbox")
    with pytest.raises(RuntimeError, match="PAYPAL_CLIENT_ID"):
        load_settings()


def test_policy_comes_from_the_environment(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("STEWARD_MAX_INVOICE", "500")
    monkeypatch.setenv("STEWARD_REMINDER_COOLDOWN_DAYS", "7")
    policy = load_settings().policy
    assert policy.max_invoice_amount == 500 and policy.reminder_cooldown_days == 7


@pytest.mark.parametrize("key", ["PAYPAL_CLIENT_ID", "PAYPAL_CLIENT_SECRET"])
def test_partial_paypal_credentials_fail_closed(key: str, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv(key, "only-one-half")
    with pytest.raises(RuntimeError, match="must be set together"):
        load_settings()


def test_invalid_mode_does_not_silently_use_demo(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("STEWARD_MODE", "production")
    with pytest.raises(RuntimeError, match="STEWARD_MODE"):
        load_settings()


def test_explicit_demo_is_allowed_with_complete_credentials(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("PAYPAL_CLIENT_ID", "id")
    monkeypatch.setenv("PAYPAL_CLIENT_SECRET", "secret")
    monkeypatch.setenv("STEWARD_MODE", "demo")
    assert load_settings().mode == "demo"


def test_manual_sandbox_configuration_requires_credentials() -> None:
    with pytest.raises(ValueError, match="requires both PayPal credentials"):
        build_port(Settings(mode="sandbox"), date.today)


def test_manual_invalid_runtime_mode_is_rejected() -> None:
    with pytest.raises(ValueError, match="Only demo and sandbox"):
        build_port(Settings(mode="production"), date.today)


def test_sandbox_is_read_only_even_when_credentials_exist(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("PAYPAL_CLIENT_ID", "id")
    monkeypatch.setenv("PAYPAL_CLIENT_SECRET", "secret")
    settings = load_settings()
    assert settings.mode == "sandbox"
    assert settings.sandbox_writes_enabled is False
    assert settings.policy.sandbox_writes_enabled is False


def test_sandbox_writes_require_explicit_opt_in(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("PAYPAL_CLIENT_ID", "id")
    monkeypatch.setenv("PAYPAL_CLIENT_SECRET", "secret")
    monkeypatch.setenv("STEWARD_SANDBOX_WRITES", "enabled")
    settings = load_settings()
    assert settings.sandbox_writes_enabled
    assert settings.policy.sandbox_writes_enabled


@pytest.mark.parametrize("setting", ["true", "1", "yes", "ENABLED", "disable"])
def test_ambiguous_sandbox_write_settings_fail_closed(
    monkeypatch: pytest.MonkeyPatch, setting: str
) -> None:
    monkeypatch.setenv("STEWARD_SANDBOX_WRITES", setting)
    with pytest.raises(RuntimeError, match="STEWARD_SANDBOX_WRITES"):
        load_settings()


def test_sandbox_write_opt_in_is_invalid_in_demo_mode(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("STEWARD_SANDBOX_WRITES", "enabled")
    with pytest.raises(RuntimeError, match="requires sandbox mode"):
        load_settings()


def test_optional_paypal_sandbox_app_pin_from_environment(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("PAYPAL_CLIENT_ID", "id")
    monkeypatch.setenv("PAYPAL_CLIENT_SECRET", "secret")
    monkeypatch.setenv("PAYPAL_APP_ID", "APP-SANDBOX-TEST")
    settings = load_settings()
    assert settings.paypal_app_id == "APP-SANDBOX-TEST"
    assert settings.sandbox_writes_enabled is False


def test_sandbox_llm_requires_explicit_operator_opt_in(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("PAYPAL_CLIENT_ID", "id")
    monkeypatch.setenv("PAYPAL_CLIENT_SECRET", "secret")
    monkeypatch.setenv("ANTHROPIC_API_KEY", "synthetic-key")
    with pytest.raises(RuntimeError, match="STEWARD_SANDBOX_LLM=enabled"):
        load_settings()


def test_sandbox_llm_opt_in_preserves_read_only_paypal_default(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("PAYPAL_CLIENT_ID", "id")
    monkeypatch.setenv("PAYPAL_CLIENT_SECRET", "secret")
    monkeypatch.setenv("ANTHROPIC_API_KEY", "synthetic-key")
    monkeypatch.setenv("STEWARD_SANDBOX_LLM", "enabled")
    settings = load_settings()
    assert settings.llm_enabled
    assert settings.sandbox_llm_enabled
    assert settings.mode == "sandbox"
    assert settings.sandbox_writes_enabled is False


@pytest.mark.parametrize("invalid", ["yes", "true", "1", "ENABLED", "on"])
def test_invalid_sandbox_llm_opt_in_fails_closed(
    monkeypatch: pytest.MonkeyPatch, invalid: str
) -> None:
    monkeypatch.setenv("STEWARD_SANDBOX_LLM", invalid)
    with pytest.raises(RuntimeError, match="STEWARD_SANDBOX_LLM"):
        load_settings()


def test_sandbox_llm_opt_in_without_external_model_key_is_rejected(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("PAYPAL_CLIENT_ID", "id")
    monkeypatch.setenv("PAYPAL_CLIENT_SECRET", "secret")
    monkeypatch.setenv("STEWARD_SANDBOX_LLM", "enabled")
    with pytest.raises(RuntimeError, match="requires ANTHROPIC_API_KEY"):
        load_settings()


def test_sandbox_llm_opt_in_not_valid_in_demo_mode(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("STEWARD_SANDBOX_LLM", "enabled")
    with pytest.raises(RuntimeError, match="requires sandbox mode"):
        load_settings()


def test_sandbox_with_no_external_model_stays_offline(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("PAYPAL_CLIENT_ID", "id")
    monkeypatch.setenv("PAYPAL_CLIENT_SECRET", "secret")
    settings = load_settings()
    assert settings.mode == "sandbox"
    assert not settings.llm_enabled
    assert not settings.sandbox_llm_enabled
