"""On-demand inventory observations; never cache financial responses or infer settlement."""

from __future__ import annotations

import hashlib
import json
import threading
import uuid
from datetime import UTC, datetime

from ..core.models import JSON, Invoice
from ..core.ports import InvoiceInventoryIncomplete, PayPalPort
from .store import SqliteProposalStore


def _inventory_fingerprint(invoices: list[Invoice]) -> bytes:
    """Hash one normalized inventory only for a transient consistency comparison.

    This contains customer and invoice fields solely in process memory.  It is
    deliberately neither returned nor written to the observation journal.
    """
    records = [
        {
            "id": invoice.id,
            "number": invoice.number,
            "customer_name": invoice.customer_name,
            "customer_email": invoice.customer_email,
            "amount": invoice.amount,
            "currency": invoice.currency,
            "status": invoice.status,
            "issued": invoice.issued.isoformat(),
            "due": invoice.due.isoformat(),
            "paid": invoice.paid.isoformat() if invoice.paid else None,
            "remaining_amount": invoice.remaining_amount,
            "balance_source": invoice.balance_source,
            "payment_origin": invoice.payment_origin,
            "provider_status": invoice.provider_status,
            "content_digest": invoice.content_digest,
            "provider_payment_ids": sorted(invoice.provider_payment_ids),
        }
        for invoice in sorted(invoices, key=lambda invoice: invoice.id)
    ]
    encoded = json.dumps(records, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return hashlib.sha256(encoded.encode()).digest()


class ObservedPayPal:
    def __init__(self, port: PayPalPort, store: SqliteProposalStore, app_key: str) -> None:
        self.port, self.store, self.mode = port, store, port.mode
        self.source = f"{self.mode}:{hashlib.sha256(app_key.encode()).hexdigest()}"
        self._read_lock = threading.RLock()

    def inventory_status(self) -> JSON:
        state = self.store.inventory(self.source)
        last = state.get("last_success_at")
        age = (datetime.now(UTC) - datetime.fromisoformat(last)).total_seconds() if last else None
        return {
            **{k: v for k, v in state.items() if k not in {"attempt", "observed_ids"}},
            "stale": state["status"] != "observed"
            or bool(state["missing_ids"])
            or age is None
            or not 0 <= age <= 300,
            "scope": "synthetic demo" if self.mode == "demo" else "configured app-visible invoices",
            "atomic_snapshot": False,
            "polling": "on demand only; no webhook ingestion",
        }

    def list_invoices(self) -> list[Invoice]:
        with self._read_lock:
            return self._read_inventory()

    def _read_inventory(self) -> list[Invoice]:
        attempt = uuid.uuid4().hex
        self.store.observe_inventory(self.source, attempt, start=True)
        try:
            invoices = self.port.list_invoices()
            ids = [invoice.id for invoice in invoices]
            if len(set(ids)) != len(ids):
                raise InvoiceInventoryIncomplete("Duplicate invoice identities.")
            fingerprint = _inventory_fingerprint(invoices)
            verified = self.port.list_invoices()
            verified_ids = [invoice.id for invoice in verified]
            if len(set(verified_ids)) != len(verified_ids):
                raise InvoiceInventoryIncomplete("Duplicate invoice identities.")
            if fingerprint != _inventory_fingerprint(verified):
                raise InvoiceInventoryIncomplete("Invoice inventory changed during verification.")
            invoices, ids = verified, verified_ids
        except Exception:
            self.store.observe_inventory(self.source, attempt)
            raise
        state = self.store.observe_inventory(self.source, attempt, ids)
        if state is None:
            raise InvoiceInventoryIncomplete("Inventory read superseded by a newer attempt.")
        if state["missing_ids"]:
            raise InvoiceInventoryIncomplete("Previously observed invoices are missing.")
        return invoices

    def get_invoice(self, invoice_id: str) -> Invoice | None:
        return self.port.get_invoice(invoice_id)

    def find_by_reference(self, reference: str) -> Invoice | None:
        return self.port.find_by_reference(reference)

    def create_invoice_draft(self, spec: JSON, reference: str) -> Invoice:
        return self.port.create_invoice_draft(spec, reference)

    def send_invoice(self, invoice_id: str) -> Invoice:
        return self.port.send_invoice(invoice_id)

    def send_reminder(self, invoice_id: str, note: str) -> None:
        self.port.send_reminder(invoice_id, note)
