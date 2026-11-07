"""Settings, read from environment variables (and a local `.env` file)."""

from __future__ import annotations

import os
import re
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

from ..core.proposals import Policy
from ..persistence.paypal_sandbox import SANDBOX_URL

_OPERATOR_ID = re.compile(r"[A-Za-z0-9][A-Za-z0-9._-]{2,63}")


def validate_operator_id(value: str | None) -> str | None:
    """Validate a local audit label; this deliberately is not authentication."""
    if value is None:
        return None
    if not _OPERATOR_ID.fullmatch(value):
        raise RuntimeError(
            "STEWARD_OPERATOR_ID must be 3-64 letters, numbers, dots, underscores or hyphens."
        )
    return value


@dataclass(frozen=True)
class Settings:
    paypal_client_id: str | None = None
    paypal_client_secret: str | None = None
    paypal_app_id: str | None = None
    paypal_base_url: str = SANDBOX_URL
    anthropic_api_key: str | None = None
    anthropic_model: str = "claude-sonnet-5-5"
    db_path: str = "data/steward.db"
    # Mode: "demo" (built-in fake PayPal with seeded data) or "sandbox" (real PayPal sandbox).
    mode: str = "demo"
    # Policy limits enforced by the server, never by the model.
    max_invoice_amount: float = 10_000.0
    reminder_cooldown_days: int = 3
    sandbox_writes_enabled: bool = False
    sandbox_llm_enabled: bool = False
    operator_id: str | None = None

    @property
    def llm_enabled(self) -> bool:
        return bool(self.anthropic_api_key)

    @property
    def policy(self) -> Policy:
        return Policy(
            max_invoice_amount=self.max_invoice_amount,
            reminder_cooldown_days=self.reminder_cooldown_days,
            sandbox_writes_enabled=self.sandbox_writes_enabled,
            operator_id=self.operator_id,
        )


def load_settings() -> Settings:
    load_dotenv(dotenv_path=Path.cwd() / ".env")
    client_id = os.getenv("PAYPAL_CLIENT_ID") or None
    client_secret = os.getenv("PAYPAL_CLIENT_SECRET") or None
    requested = (os.getenv("STEWARD_MODE") or "").strip().lower()
    if requested and requested not in ("demo", "sandbox"):
        raise RuntimeError("STEWARD_MODE must be 'demo' or 'sandbox'.")
    if bool(client_id) != bool(client_secret):
        raise RuntimeError("PAYPAL_CLIENT_ID and PAYPAL_CLIENT_SECRET must be set together.")
    mode = requested or ("sandbox" if client_id and client_secret else "demo")
    writes_setting = (os.getenv("STEWARD_SANDBOX_WRITES") or "").strip()
    if writes_setting not in ("", "enabled", "disabled"):
        raise RuntimeError("STEWARD_SANDBOX_WRITES must be 'enabled' or 'disabled'.")
    if writes_setting == "enabled" and mode != "sandbox":
        raise RuntimeError("STEWARD_SANDBOX_WRITES=enabled requires sandbox mode.")
    operator_id = validate_operator_id(os.getenv("STEWARD_OPERATOR_ID") or None)
    if writes_setting == "enabled" and not operator_id:
        raise RuntimeError("STEWARD_SANDBOX_WRITES=enabled requires STEWARD_OPERATOR_ID.")
    llm_key = os.getenv("ANTHROPIC_API_KEY") or None
    llm_setting = (os.getenv("STEWARD_SANDBOX_LLM") or "").strip()
    if llm_setting not in ("", "enabled", "disabled"):
        raise RuntimeError("STEWARD_SANDBOX_LLM must be 'enabled' or 'disabled'.")
    if llm_setting == "enabled" and mode != "sandbox":
        raise RuntimeError("STEWARD_SANDBOX_LLM=enabled requires sandbox mode.")
    if mode == "sandbox" and llm_key and llm_setting != "enabled":
        raise RuntimeError(
            "Sandbox external AI requires STEWARD_SANDBOX_LLM=enabled. "
            "The model receives raw operator chat, which may include personal data."
        )
    if mode == "sandbox" and llm_setting == "enabled" and not llm_key:
        raise RuntimeError("STEWARD_SANDBOX_LLM=enabled requires ANTHROPIC_API_KEY.")
    if mode == "sandbox" and not (client_id and client_secret):
        raise RuntimeError(
            "STEWARD_MODE=sandbox needs PAYPAL_CLIENT_ID and PAYPAL_CLIENT_SECRET "
            "(create a Sandbox app in the PayPal Developer Dashboard)."
        )
    return Settings(
        paypal_client_id=client_id,
        paypal_client_secret=client_secret,
        paypal_app_id=os.getenv("PAYPAL_APP_ID") or None,
        paypal_base_url=os.getenv("PAYPAL_BASE_URL", SANDBOX_URL),
        anthropic_api_key=llm_key,
        anthropic_model=os.getenv("ANTHROPIC_MODEL", "claude-sonnet-5-5"),
        db_path=os.getenv("STEWARD_DB", "data/steward.db"),
        mode=mode,
        max_invoice_amount=float(os.getenv("STEWARD_MAX_INVOICE", "10000")),
        reminder_cooldown_days=int(os.getenv("STEWARD_REMINDER_COOLDOWN_DAYS", "3")),
        sandbox_writes_enabled=writes_setting == "enabled",
        sandbox_llm_enabled=llm_setting == "enabled",
        operator_id=operator_id,
    )
