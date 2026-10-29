import pytest

from paypal_invoice_steward.ui.config import load_settings


@pytest.fixture(autouse=True)
def clean_env(monkeypatch: pytest.MonkeyPatch, tmp_path: pytest.TempPathFactory) -> None:
    for name in (
        "PAYPAL_CLIENT_ID",
        "PAYPAL_CLIENT_SECRET",
        "STEWARD_MODE",
        "ANTHROPIC_API_KEY",
        "STEWARD_MAX_INVOICE",
        "STEWARD_REMINDER_COOLDOWN_DAYS",
    ):
        monkeypatch.delenv(name, raising=False)
    monkeypatch.chdir(tmp_path)  # no stray .env file


def test_demo_mode_without_credentials() -> None:
    settings = load_settings()
    assert settings.mode == "demo" and not settings.llm_enabled


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
