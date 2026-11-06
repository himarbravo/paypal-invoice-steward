"""Golden tests for aging boundaries, exclusion, and currency isolation."""

from datetime import date, timedelta

import pytest

from paypal_invoice_steward.core.aging import receivables_aging
from paypal_invoice_steward.core.models import (
    BalanceUnverified,
    Invoice,
    RefundReconciliationRequired,
)

TODAY = date(2026, 11, 5)


def invoice(
    number: str,
    days_late: int,
    *,
    status: str = "open",
    amount: float = 10.01,
    currency: str = "EUR",
) -> Invoice:
    return Invoice(
        id=number,
        number=number,
        customer_name="Example",
        customer_email="a@example.com",
        amount=amount,
        currency=currency,
        status=status,
        issued=TODAY - timedelta(days=120),
        due=TODAY - timedelta(days=days_late),
    )


@pytest.mark.parametrize(
    "days,bucket",
    [
        (-5, "not_due"),
        (0, "not_due"),
        (1, "1_30"),
        (30, "1_30"),
        (31, "31_60"),
        (60, "31_60"),
        (61, "61_90"),
        (90, "61_90"),
        (91, "91_plus"),
    ],
)
def test_aging_boundaries(days: int, bucket: str) -> None:
    result = receivables_aging([invoice("INV", days)], TODAY)
    assert result["invoices"][0]["bucket"] == bucket
    assert result["by_currency"]["EUR"]["buckets"][bucket] == 10.01


def test_currencies_and_excluded_states() -> None:
    result = receivables_aging(
        [
            invoice("A", 1, amount=0.1),
            invoice("B", 1, amount=0.2),
            invoice("C", 40, currency="USD"),
            invoice("D", 20, status="paid"),
            invoice("E", 20, status="unknown"),
        ],
        TODAY,
    )
    assert result["by_currency"]["EUR"]["total"] == 0.3
    assert result["by_currency"]["USD"]["total"] == 10.01
    assert result["excluded_status_counts"] == {"paid": 1, "unknown": 1}
    assert len(result["invoices"]) == 3


def test_reject_nonfinite_amount() -> None:
    with pytest.raises(ValueError):
        receivables_aging([invoice("A", 1, amount=float("nan"))], TODAY)


def test_aging_uses_paypal_remaining_balance_not_nominal_invoice() -> None:
    inv = invoice("PARTIAL", 31, amount=450.0)
    inv.remaining_amount = 250.75
    inv.balance_source = "paypal_due_amount"
    result = receivables_aging([inv], TODAY)
    assert result["basis"] == "PayPal due_amount residuals"
    assert result["by_currency"]["EUR"]["total"] == 250.75
    assert result["invoices"][0]["amount"] == 250.75
    assert inv.amount == 450.0


def test_aging_rejects_unverified_or_mixed_balance_sources() -> None:
    inv = invoice("PARTIAL", 31, amount=450.0)
    inv.balance_source = "unverified"
    with pytest.raises(BalanceUnverified):
        receivables_aging([inv], TODAY)
    inv.balance_source = "paypal_due_amount"
    inv.remaining_amount = 250.0
    with pytest.raises(BalanceUnverified):
        receivables_aging([inv, invoice("SYNTH", 31)], TODAY)


@pytest.mark.parametrize("provider_status", ["REFUNDED", "PARTIALLY_REFUNDED", "MARKED_AS_REFUNDED"])
def test_aging_never_excludes_refunds_silently_from_receivables(
    provider_status: str,
) -> None:
    open_invoice = invoice("OPEN", 14, amount=100.0)
    refund = invoice("REFUND", 14, status="refund_review", amount=450.0)
    refund.provider_status = provider_status
    refund.balance_source = "paypal_due_amount"
    refund.remaining_amount = 175.0
    with pytest.raises(RefundReconciliationRequired):
        receivables_aging([open_invoice, refund], TODAY)
