from datetime import date

from paypal_invoice_steward.core.models import Invoice, invoice_total


def _invoice(status: str) -> Invoice:
    return Invoice(
        id="1",
        number="N1",
        customer_name="A",
        customer_email="a@b.co",
        amount=10.0,
        currency="EUR",
        status=status,
        issued=date(2026, 10, 1),
        due=date(2026, 10, 15),
    )


def test_days_overdue_only_counts_open_invoices() -> None:
    today = date(2026, 10, 29)
    assert _invoice("open").days_overdue(today) == 14
    assert _invoice("paid").days_overdue(today) == 0
    assert _invoice("open").days_overdue(date(2026, 10, 1)) == 0


def test_to_dict_uses_iso_dates() -> None:
    data = _invoice("open").to_dict(date(2026, 10, 29))
    assert data["due"] == "2026-10-15"
    assert data["days_overdue"] == 14


def test_invoice_total() -> None:
    spec = {"items": [{"quantity": 2, "unit_price": 10.5}, {"quantity": 1, "unit_price": 0.25}]}
    assert invoice_total(spec) == 21.25
