"""Golden tests for aging boundaries, exclusion, and currency isolation."""
from datetime import date, timedelta

import pytest

from paypal_invoice_steward.core.aging import receivables_aging
from paypal_invoice_steward.core.models import Invoice


TODAY = date(2026, 11, 5)


def invoice(number: str, days_late: int, *, status: str = "open",
            amount: float = 10.01, currency: str = "EUR") -> Invoice:
    return Invoice(id=number, number=number, customer_name="Example",
                   customer_email="a@example.com", amount=amount,
                   currency=currency, status=status, issued=TODAY - timedelta(days=120),
                   due=TODAY - timedelta(days=days_late))


@pytest.mark.parametrize("days,bucket", [
    (-5, "not_due"), (0, "not_due"), (1, "1_30"), (30, "1_30"),
    (31, "31_60"), (60, "31_60"), (61, "61_90"), (90, "61_90"),
    (91, "91_plus"),
])
def test_aging_boundaries(days: int, bucket: str) -> None:
    result = receivables_aging([invoice("INV", days)], TODAY)
    assert result["invoices"][0]["bucket"] == bucket
    assert result["by_currency"]["EUR"]["buckets"][bucket] == 10.01


def test_currencies_and_excluded_states() -> None:
    result = receivables_aging([
        invoice("A", 1, amount=0.1), invoice("B", 1, amount=0.2),
        invoice("C", 40, currency="USD"),
        invoice("D", 20, status="paid"),
        invoice("E", 20, status="unknown"),
    ], TODAY)
    assert result["by_currency"]["EUR"]["total"] == 0.3
    assert result["by_currency"]["USD"]["total"] == 10.01
    assert result["excluded_status_counts"] == {"paid": 1, "unknown": 1}
    assert len(result["invoices"]) == 3


def test_reject_nonfinite_amount() -> None:
    with pytest.raises(ValueError):
        receivables_aging([invoice("A", 1, amount=float("nan"))], TODAY)
