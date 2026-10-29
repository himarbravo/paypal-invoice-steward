"""Fixtures for `core` tests: an in-memory PayPal that records what it sends."""

from __future__ import annotations

from datetime import date, timedelta

import pytest

from paypal_invoice_steward.core.models import JSON, Invoice, invoice_total
from paypal_invoice_steward.core.ports import PayPalError, PayPalUncertain
from paypal_invoice_steward.core.proposals import ProposalService
from paypal_invoice_steward.persistence.store import SqliteProposalStore

TODAY = date(2026, 10, 29)

INVOICE: JSON = {
    "customer_name": "Alba Design Studio",
    "customer_email": "billing@albadesign.example",
    "items": [{"description": "Logo refresh", "quantity": 1, "unit_price": 450}],
    "currency": "EUR",
    "due_days": 14,
}


class FakePayPal:
    """Minimal `PayPalPort` with one-shot failure injection."""

    mode = "fake"

    def __init__(self) -> None:
        self.invoices: dict[str, Invoice] = {}
        self.sent_log: list[tuple[str, str]] = []
        self.fail_next: str | None = None
        for i, (status, due_offset) in enumerate(
            [("open", -20), ("open", -5), ("open", 10), ("paid", -40)], start=1
        ):
            self.invoices[f"INV{i}"] = Invoice(
                id=f"INV{i}",
                number=f"N-{i}",
                customer_name=f"Customer {i}",
                customer_email=f"c{i}@example.com",
                amount=100.0 * i,
                currency="EUR",
                status=status,
                issued=TODAY - timedelta(days=60),
                due=TODAY + timedelta(days=due_offset),
                paid=TODAY - timedelta(days=30) if status == "paid" else None,
            )

    def _take(self, mode: str) -> bool:
        if self.fail_next == mode:
            self.fail_next = None
            return True
        return False

    def list_invoices(self) -> list[Invoice]:
        return list(self.invoices.values())

    def get_invoice(self, invoice_id: str) -> Invoice | None:
        return self.invoices.get(invoice_id)

    def find_by_reference(self, reference: str) -> Invoice | None:
        return next((i for i in self.invoices.values() if i.number == reference), None)

    def create_invoice_draft(self, spec: JSON, reference: str) -> Invoice:
        if self._take("reject"):
            raise PayPalError("UNPROCESSABLE_ENTITY: recipient rejected.", 422)
        invoice = Invoice(
            id=f"NEW{len(self.invoices) + 1}",
            number=reference,
            customer_name=spec["customer_name"],
            customer_email=spec["customer_email"],
            amount=invoice_total(spec),
            currency=spec["currency"],
            status="draft",
            issued=TODAY,
            due=TODAY + timedelta(days=int(spec["due_days"])),
        )
        self.invoices[invoice.id] = invoice
        return invoice

    def send_invoice(self, invoice_id: str) -> Invoice:
        invoice = self.invoices[invoice_id]
        invoice.status = "open"
        self.sent_log.append(("invoice", invoice_id))
        if self._take("timeout_after_send"):
            raise PayPalUncertain("No response from PayPal (simulated timeout).")
        return invoice

    def send_reminder(self, invoice_id: str, note: str) -> None:
        if self._take("timeout_after_send"):
            raise PayPalUncertain("No response from PayPal (simulated timeout).")
        self.sent_log.append(("reminder", invoice_id))


@pytest.fixture
def port() -> FakePayPal:
    return FakePayPal()


@pytest.fixture
def service(port: FakePayPal) -> ProposalService:
    return ProposalService(port, SqliteProposalStore(":memory:"), today=lambda: TODAY)
