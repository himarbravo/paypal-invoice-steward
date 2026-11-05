"""Deterministic invoice aging; no FX conversion or inferred payment allocation."""

from __future__ import annotations

from collections import defaultdict
from datetime import date
from decimal import ROUND_HALF_UP, Decimal

from .models import JSON, Invoice

BUCKETS = ("not_due", "1_30", "31_60", "61_90", "91_plus")


def _cents(value: float) -> int:
    if not Decimal(str(value)).is_finite() or value < 0:
        raise ValueError("Invoice amount must be finite and nonnegative")
    return int((Decimal(str(value)) * 100).quantize(Decimal("1"), rounding=ROUND_HALF_UP))


def receivables_aging(invoices: list[Invoice], as_of: date) -> JSON:
    """Age currently open invoices by due date, separately for each currency.

    This is a *current snapshot*, not a historical as-of ledger reconstruction.
    The Invoice model has no payment allocations or remaining-balance field;
    'amount' is therefore the source-provided amount, NOT a verified residual.
    """
    totals: dict[str, dict[str, int]] = defaultdict(lambda: {b: 0 for b in BUCKETS})
    rows: list[JSON] = []
    excluded: dict[str, int] = defaultdict(int)
    for inv in invoices:
        if inv.status != "open":
            excluded[inv.status] += 1
            continue
        days = (as_of - inv.due).days
        if days <= 0:
            bucket = "not_due"
        elif days <= 30:
            bucket = "1_30"
        elif days <= 60:
            bucket = "31_60"
        elif days <= 90:
            bucket = "61_90"
        else:
            bucket = "91_plus"
        cents = _cents(inv.amount)
        totals[inv.currency][bucket] += cents
        rows.append(
            {
                "invoice_id": inv.id,
                "number": inv.number,
                "customer": inv.customer_name,
                "currency": inv.currency,
                "amount": cents / 100,
                "due": inv.due.isoformat(),
                "days_overdue": max(days, 0),
                "bucket": bucket,
            }
        )
    rows.sort(key=lambda r: (-r["days_overdue"], r["number"]))
    return {
        "as_of": as_of.isoformat(),
        "basis": "current open invoice face amounts",
        "limitations": [
            "Not a historical as-of reconstruction",
            "Partial payments and remaining balances cannot be verified from the current Invoice model",
            "No FX conversion; currencies are never combined",
        ],
        "by_currency": {
            currency: {
                "buckets": {b: value / 100 for b, value in buckets.items()},
                "total": sum(buckets.values()) / 100,
            }
            for currency, buckets in sorted(totals.items())
        },
        "excluded_status_counts": dict(sorted(excluded.items())),
        "invoices": rows,
    }
