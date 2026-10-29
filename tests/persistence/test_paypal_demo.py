from datetime import date

import pytest

from paypal_invoice_steward.core.ports import PayPalError, PayPalPort, PayPalUncertain
from paypal_invoice_steward.persistence.paypal_demo import DemoPayPal

TODAY = date(2026, 10, 29)
SPEC = {
    "customer_name": "Alba Design Studio",
    "customer_email": "billing@albadesign.example",
    "items": [{"description": "Logo refresh", "quantity": 1, "unit_price": 450}],
    "currency": "EUR",
    "due_days": 14,
}


@pytest.fixture
def demo() -> DemoPayPal:
    return DemoPayPal(today=lambda: TODAY)


def test_seeded_book_has_history_and_late_invoices(demo: DemoPayPal) -> None:
    invoices = demo.list_invoices()
    assert sum(i.status == "paid" for i in invoices) == 15
    open_ = [i for i in invoices if i.status == "open"]
    assert len(open_) == 8
    assert sum(i.amount for i in open_) == 13840
    assert any(i.days_overdue(TODAY) > 60 for i in open_)


def test_create_send_and_find_by_reference(demo: DemoPayPal) -> None:
    draft = demo.create_invoice_draft(SPEC, "STW-TEST0001")
    assert draft.status == "draft" and draft.amount == 450
    sent = demo.send_invoice(draft.id)
    assert sent.status == "open"
    found = demo.find_by_reference("STW-TEST0001")
    assert found is not None and found.id == draft.id
    assert demo.sent_log == [("invoice", draft.id)]


def test_duplicate_reference_is_refused(demo: DemoPayPal) -> None:
    demo.create_invoice_draft(SPEC, "STW-TEST0001")
    with pytest.raises(PayPalError):
        demo.create_invoice_draft(SPEC, "STW-TEST0001")


def test_timeout_after_send_still_sends(demo: DemoPayPal) -> None:
    draft = demo.create_invoice_draft(SPEC, "STW-TEST0002")
    demo.fail_next = "timeout_after_send"
    with pytest.raises(PayPalUncertain):
        demo.send_invoice(draft.id)
    assert demo.get_invoice(draft.id) is not None
    assert demo.sent_log == [("invoice", draft.id)]
    assert demo.fail_next is None


def test_reject_is_one_shot(demo: DemoPayPal) -> None:
    demo.fail_next = "reject"
    with pytest.raises(PayPalError):
        demo.create_invoice_draft(SPEC, "STW-TEST0003")
    assert demo.create_invoice_draft(SPEC, "STW-TEST0003").status == "draft"


def test_reminders_only_for_open_invoices(demo: DemoPayPal) -> None:
    open_one = next(i for i in demo.list_invoices() if i.status == "open")
    paid_one = next(i for i in demo.list_invoices() if i.status == "paid")
    demo.send_reminder(open_one.id, "hi")
    with pytest.raises(PayPalError):
        demo.send_reminder(paid_one.id, "hi")
    assert demo.sent_log == [("reminder", open_one.id)]


def test_satisfies_the_port(demo: DemoPayPal) -> None:
    port: PayPalPort = demo
    assert port.mode == "demo"
