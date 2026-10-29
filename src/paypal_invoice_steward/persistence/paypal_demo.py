"""An in-memory stand-in for PayPal, seeded with a realistic small business.

It exists so anyone can run and judge the app without credentials, and so
failure modes can be triggered on demand: a response lost after PayPal already
sent the invoice, or PayPal refusing a request outright.
"""

from __future__ import annotations

import threading
from collections.abc import Callable
from datetime import date, timedelta

from ..core.models import JSON, Invoice
from ..core.ports import PayPalError, PayPalUncertain

# name -> (email, typical days paid after the due date, spread in days)
CUSTOMERS: dict[str, tuple[str, int, int]] = {
    "Alba Design Studio": ("billing@albadesign.example", 2, 3),
    "Café Teide": ("accounts@cafeteide.example", -1, 2),
    "Nordic Freight GmbH": ("ap@nordicfreight.example", 14, 5),
    "Mosaic Labs": ("finance@mosaiclabs.example", 32, 9),
    "Hotel Las Cañadas": ("pagos@hotelcanadas.example", 8, 4),
}

# (customer, amount, issued days ago, days until due; negative means overdue)
OPEN_INVOICES: list[tuple[str, float, int, int]] = [
    ("Mosaic Labs", 4200.00, 75, -61),
    ("Nordic Freight GmbH", 2850.00, 45, -31),
    ("Hotel Las Cañadas", 1750.00, 28, -14),
    ("Alba Design Studio", 1200.00, 20, -6),
    ("Café Teide", 380.00, 12, 2),
    ("Nordic Freight GmbH", 1900.00, 10, 4),
    ("Alba Design Studio", 640.00, 5, 9),
    ("Hotel Las Cañadas", 920.00, 3, 11),
]

_PAID_HISTORY_AMOUNTS = [(150, 480.0), (110, 1250.0), (70, 890.0)]


class DemoPayPal:
    mode = "demo"

    def __init__(self, today: Callable[[], date] = date.today, seed: bool = True) -> None:
        self._today = today
        self._lock = threading.RLock()
        self._invoices: dict[str, Invoice] = {}
        self._seq = 0
        # Everything that actually went out: ("invoice" | "reminder", invoice_id).
        self.sent_log: list[tuple[str, str]] = []
        # One-shot failure injection: "timeout_after_send" or "reject".
        self.fail_next: str | None = None
        if seed:
            self._seed()

    # -- seeding ----------------------------------------------------------------

    def _new_id(self) -> str:
        self._seq += 1
        return f"INV2-DEMO-{self._seq:04d}"

    def _seed(self) -> None:
        today = self._today()
        rows: list[Invoice] = []
        for name, (email, mean, spread) in CUSTOMERS.items():
            for k, (days_ago, amount) in enumerate(_PAID_HISTORY_AMOUNTS):
                issued = today - timedelta(days=days_ago)
                due = issued + timedelta(days=14)
                delay = mean + (k - 1) * max(spread // 2, 1)
                rows.append(
                    Invoice(
                        id="",
                        number="",
                        customer_name=name,
                        customer_email=email,
                        amount=amount + 37 * k,
                        currency="EUR",
                        status="paid",
                        issued=issued,
                        due=due,
                        paid=due + timedelta(days=delay),
                    )
                )
        for name, amount, issued_ago, due_in in OPEN_INVOICES:
            email = CUSTOMERS[name][0]
            issued = today - timedelta(days=issued_ago)
            rows.append(
                Invoice(
                    id="",
                    number="",
                    customer_name=name,
                    customer_email=email,
                    amount=amount,
                    currency="EUR",
                    status="open",
                    issued=issued,
                    due=today + timedelta(days=due_in),
                )
            )
        rows.sort(key=lambda inv: inv.issued)
        for n, inv in enumerate(rows, start=1):
            inv.id = self._new_id()
            inv.number = f"INV-2026-{n:03d}"
            self._invoices[inv.id] = inv

    # -- failure injection ------------------------------------------------------

    def _take_failure(self, *modes: str) -> str | None:
        if self.fail_next in modes:
            mode, self.fail_next = self.fail_next, None
            return mode
        return None

    # -- PayPalPort -------------------------------------------------------------

    def list_invoices(self) -> list[Invoice]:
        with self._lock:
            return sorted(self._invoices.values(), key=lambda i: (i.issued, i.id))

    def get_invoice(self, invoice_id: str) -> Invoice | None:
        with self._lock:
            return self._invoices.get(invoice_id)

    def find_by_reference(self, reference: str) -> Invoice | None:
        with self._lock:
            for invoice in self._invoices.values():
                if invoice.number == reference:
                    return invoice
        return None

    def create_invoice_draft(self, spec: JSON, reference: str) -> Invoice:
        with self._lock:
            if self._take_failure("reject"):
                raise PayPalError(
                    "UNPROCESSABLE_ENTITY: the recipient email address was rejected (simulated).",
                    422,
                )
            if self.find_by_reference(reference):
                raise PayPalError("DUPLICATE_INVOICE_NUMBER: invoice number already used.", 422)
            today = self._today()
            total = round(sum(i["quantity"] * i["unit_price"] for i in spec["items"]), 2)
            invoice = Invoice(
                id=self._new_id(),
                number=reference,
                customer_name=spec["customer_name"],
                customer_email=spec["customer_email"],
                amount=total,
                currency=spec["currency"],
                status="draft",
                issued=today,
                due=today + timedelta(days=int(spec["due_days"])),
            )
            self._invoices[invoice.id] = invoice
            return invoice

    def send_invoice(self, invoice_id: str) -> Invoice:
        with self._lock:
            invoice = self._invoices.get(invoice_id)
            if invoice is None:
                raise PayPalError("RESOURCE_NOT_FOUND: invoice does not exist.", 404)
            if invoice.status != "draft":
                raise PayPalError("INVALID_INVOICE_STATUS: only drafts can be sent.", 422)
            invoice.status = "open"
            self.sent_log.append(("invoice", invoice_id))
            if self._take_failure("timeout_after_send"):
                # PayPal did its job; the answer never reached us.
                raise PayPalUncertain("No response from PayPal (simulated timeout).")
            return invoice

    def send_reminder(self, invoice_id: str, note: str) -> None:
        with self._lock:
            invoice = self._invoices.get(invoice_id)
            if invoice is None:
                raise PayPalError("RESOURCE_NOT_FOUND: invoice does not exist.", 404)
            if self._take_failure("reject"):
                raise PayPalError("UNPROCESSABLE_ENTITY: reminder rejected (simulated).", 422)
            if invoice.status != "open":
                raise PayPalError("INVALID_INVOICE_STATUS: only open invoices get reminders.", 422)
            self.sent_log.append(("reminder", invoice_id))
            if self._take_failure("timeout_after_send"):
                raise PayPalUncertain("No response from PayPal (simulated timeout).")
