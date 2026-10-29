"""Settings, read from environment variables (and a local `.env` file)."""

from __future__ import annotations

import os
from dataclasses import dataclass

from dotenv import load_dotenv

from ..core.proposals import Policy
from ..persistence.paypal_sandbox import SANDBOX_URL


@dataclass(frozen=True)
class Settings:
    paypal_client_id: str | None = None
    paypal_client_secret: str | None = None
    paypal_base_url: str = SANDBOX_URL
    anthropic_api_key: str | None = None
    anthropic_model: str = "claude-sonnet-5-5"
    db_path: str = "data/steward.db"
    # Mode: "demo" (built-in fake PayPal with seeded data) or "sandbox" (real PayPal sandbox).
    mode: str = "demo"
    # Policy limits enforced by the server, never by the model.
    max_invoice_amount: float = 10_000.0
    reminder_cooldown_days: int = 3

    @property
    def llm_enabled(self) -> bool:
        return bool(self.anthropic_api_key)

    @property
    def policy(self) -> Policy:
        return Policy(
            max_invoice_amount=self.max_invoice_amount,
            reminder_cooldown_days=self.reminder_cooldown_days,
        )


def load_settings() -> Settings:
    load_dotenv()
    client_id = os.getenv("PAYPAL_CLIENT_ID") or None
    client_secret = os.getenv("PAYPAL_CLIENT_SECRET") or None
    requested = (os.getenv("STEWARD_MODE") or "").strip().lower()
    if requested in ("demo", "sandbox"):
        mode = requested
    else:
        mode = "sandbox" if client_id and client_secret else "demo"
    if mode == "sandbox" and not (client_id and client_secret):
        raise RuntimeError(
            "STEWARD_MODE=sandbox needs PAYPAL_CLIENT_ID and PAYPAL_CLIENT_SECRET "
            "(create a Sandbox app in the PayPal Developer Dashboard)."
        )
    return Settings(
        paypal_client_id=client_id,
        paypal_client_secret=client_secret,
        paypal_base_url=os.getenv("PAYPAL_BASE_URL", SANDBOX_URL),
        anthropic_api_key=os.getenv("ANTHROPIC_API_KEY") or None,
        anthropic_model=os.getenv("ANTHROPIC_MODEL", "claude-sonnet-5-5"),
        db_path=os.getenv("STEWARD_DB", "data/steward.db"),
        mode=mode,
        max_invoice_amount=float(os.getenv("STEWARD_MAX_INVOICE", "10000")),
        reminder_cooldown_days=int(os.getenv("STEWARD_REMINDER_COOLDOWN_DAYS", "3")),
    )
