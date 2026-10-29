"""Plain data types shared by every layer."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import date
from typing import Any

JSON = dict[str, Any]
"""A JSON-like object, as sent to the browser or stored in the database."""


@dataclass
class Invoice:
    """An invoice as Invoice Steward sees it, whatever the PayPal backend."""

    id: str
    number: str
    customer_name: str
    customer_email: str
    amount: float
    currency: str
    status: str  # draft | open | paid | cancelled | unknown
    issued: date
    due: date
    paid: date | None = None

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
        }
        if today is not None:
            data["days_overdue"] = self.days_overdue(today)
        return data


def invoice_total(spec: JSON) -> float:
    """Total of an invoice request: sum of quantity times unit price over its items."""
    return round(sum(float(i["quantity"]) * float(i["unit_price"]) for i in spec["items"]), 2)
