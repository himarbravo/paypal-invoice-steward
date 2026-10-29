"""Interfaces that `core` needs from the outside world, and PayPal's two error types.

The distinction between the two errors is the heart of the safety model:

* `PayPalError` means PayPal definitively refused the request. Nothing happened.
* `PayPalUncertain` means we do not know what happened (timeout, dropped
  connection, 5xx). The action may or may not have gone through.

Nothing in the app ever reports "failed" for an uncertain outcome.
"""

from __future__ import annotations

import builtins
from collections.abc import Iterable
from typing import Any, Protocol

from .models import JSON, Invoice


class PayPalError(Exception):
    """PayPal refused the request. The action did not happen."""

    def __init__(self, message: str, status_code: int | None = None) -> None:
        super().__init__(message)
        self.status_code = status_code


class PayPalUncertain(Exception):
    """We do not know whether the action happened."""


class PayPalPort(Protocol):
    """The small slice of PayPal Invoicing that Invoice Steward uses."""

    mode: str

    def list_invoices(self) -> list[Invoice]: ...

    def get_invoice(self, invoice_id: str) -> Invoice | None: ...

    def find_by_reference(self, reference: str) -> Invoice | None:
        """Find an invoice we created, by the stable reference we gave it."""
        ...

    def create_invoice_draft(self, spec: JSON, reference: str) -> Invoice: ...

    def send_invoice(self, invoice_id: str) -> Invoice: ...

    def send_reminder(self, invoice_id: str, note: str) -> None: ...


class ProposalStore(Protocol):
    """Durable storage for proposals and their audit trail."""

    def insert(self, proposal: JSON) -> None: ...

    def get(self, proposal_id: str) -> JSON | None: ...

    def list(self, statuses: Iterable[str] | None = None) -> list[JSON]: ...

    def transition(
        self,
        proposal_id: str,
        from_statuses: Iterable[str],
        to_status: str,
        result: JSON | None = None,
        error: str | None = None,
    ) -> bool:
        """Move to `to_status` only from one of `from_statuses`.

        Returns True for exactly one of any concurrent callers (compare and swap).
        """
        ...

    def log(self, proposal_id: str, event: str, detail: str = "") -> None: ...

    def events(self, proposal_id: str) -> builtins.list[JSON]: ...


class LLMClient(Protocol):
    """A language model that supports tool use (Anthropic Messages API shape)."""

    def create_message(self, **kwargs: Any) -> Any:
        """Send one request; return a response with `content` blocks and `stop_reason`."""
        ...
