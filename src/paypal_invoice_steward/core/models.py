"""Plain data types shared by every layer."""

from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass
from datetime import date
from typing import Any

JSON = dict[str, Any]
"""A JSON-like object, as sent to the browser or stored in the database."""


BALANCE_UNVERIFIED_MESSAGE = (
    "PayPal remaining invoice balances are unavailable or inconsistent; "
    "financial figures and reminders are blocked."
)


class BalanceUnverified(ValueError):
    """The provider has not established a usable outstanding balance."""


REFUND_REVIEW_MESSAGE = (
    "PayPal refund activity needs manual reconciliation; financial totals and reminders "
    "are unavailable."
)


class RefundReconciliationRequired(BalanceUnverified):
    """Refunded invoices cannot be classified as cancellations or collectible balances."""


def require_refund_reconciliation_clear(invoices: list[Invoice]) -> None:
    """Do not compute apparently complete merchant figures while refunds are unresolved."""
    if any(inv.status == "refund_review" for inv in invoices):
        raise RefundReconciliationRequired(REFUND_REVIEW_MESSAGE)


@dataclass
class Invoice:
    """An invoice as Invoice Steward sees it, whatever the PayPal backend."""

    id: str
    number: str
    customer_name: str
    customer_email: str
    amount: float
    currency: str
    status: str  # draft | open | paid | cancelled | refund_review | unknown
    issued: date
    due: date
    paid: date | None = None
    remaining_amount: float | None = None
    balance_source: str = "synthetic"  # unit tests/demo only; PayPal must set this explicitly
    payment_origin: str = "unknown"  # PayPal-reported, not independently settled
    provider_status: str | None = None
    content_digest: str | None = None  # normalized lines/note; never exposed to the UI or LLM
    provider_payment_ids: tuple[str, ...] = ()  # adapter-only correlation hints; never public

    def receivable_amount(self) -> float:
        """Return source-backed residual, never an invoice face-value fallback for PayPal."""
        if self.status == "refund_review":
            raise RefundReconciliationRequired(REFUND_REVIEW_MESSAGE)
        if self.balance_source == "synthetic":
            return self.amount
        if self.balance_source == "paypal_due_amount" and self.remaining_amount is not None:
            return self.remaining_amount
        raise BalanceUnverified(BALANCE_UNVERIFIED_MESSAGE)

    def days_overdue(self, today: date) -> int:
        """Days past the due date; 0 unless the invoice is open."""
        if self.status != "open":
            return 0
        return max((today - self.due).days, 0)

    def to_dict(self, today: date | None = None) -> JSON:
        """Serialise with ISO dates, adding `days_overdue` when `today` is given."""
        data: JSON = {
            key: (value.isoformat() if isinstance(value, date) else value)
            for key, value in asdict(self).items()
            if key not in {"content_digest", "provider_payment_ids"}
        }
        if today is not None:
            data["days_overdue"] = self.days_overdue(today)
        return data


def invoice_total(spec: JSON) -> float:
    """Total of an invoice request: sum of quantity times unit price over its items."""
    return round(sum(float(i["quantity"]) * float(i["unit_price"]) for i in spec["items"]), 2)


def invoice_content_digest(spec: JSON) -> str:
    """Digest approved line content without retaining it in public invoice views."""
    content = {
        "note": spec.get("note", ""),
        "items": [
            {
                "description": item["description"],
                "quantity": int(item["quantity"]),
                "unit_price": f"{float(item['unit_price']):.2f}",
            }
            for item in spec["items"]
        ],
    }
    encoded = json.dumps(content, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return hashlib.sha256(encoded.encode()).hexdigest()
