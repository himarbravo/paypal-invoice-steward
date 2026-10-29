"""Proposals: the only way anything ever leaves the system.

The agent creates proposals. A person confirms them. This module enforces the
rules around that handoff:

* Policy is checked here, in code, not by the model's good behaviour.
* Confirming sends exactly what was reviewed: the confirm call carries the
  proposal's hash, and any mismatch is refused.
* Confirming twice, or from two tabs at once, executes once.
* "Failed" is only ever reported when PayPal definitively refused. A timeout is
  "unverified", and before retrying we look PayPal up by a stable reference so a
  retry can never create or send a second invoice.
"""

from __future__ import annotations

import builtins
import hashlib
import json
import re
import uuid
from collections.abc import Callable
from dataclasses import dataclass
from datetime import date, datetime

from .models import JSON, invoice_total
from .ports import PayPalError, PayPalPort, PayPalUncertain, ProposalStore

EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
CURRENCIES = {"EUR", "USD", "GBP"}

PENDING, EXECUTING, DONE, UNVERIFIED, FAILED, DISMISSED = (
    "pending",
    "executing",
    "done",
    "unverified",
    "failed",
    "dismissed",
)


@dataclass(frozen=True)
class Policy:
    """Limits enforced by the server, never left to the model."""

    max_invoice_amount: float = 10_000.0
    reminder_cooldown_days: int = 3


class ProposalError(Exception):
    status_code = 400


class NotFound(ProposalError):
    status_code = 404


class PolicyError(ProposalError):
    status_code = 422


class Conflict(ProposalError):
    status_code = 409


class HashMismatch(Conflict):
    pass


def payload_hash(kind: str, payload: JSON) -> str:
    canonical = json.dumps(
        {"kind": kind, "payload": payload},
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    )
    return hashlib.sha256(canonical.encode()).hexdigest()[:16]


def _money(value: float) -> str:
    return f"{value:,.2f}"


class ProposalService:
    def __init__(
        self,
        port: PayPalPort,
        store: ProposalStore,
        policy: Policy | None = None,
        today: Callable[[], date] = date.today,
    ) -> None:
        self.port = port
        self.store = store
        self.policy = policy or Policy()
        self.today = today

    # -- creating proposals (what the agent may do) -----------------------------

    def _validate_invoice(self, raw: JSON) -> JSON:
        name = str(raw.get("customer_name", "")).strip()
        if not 1 <= len(name) <= 80:
            raise PolicyError("Customer name is required (up to 80 characters).")
        email = str(raw.get("customer_email", "")).strip().lower()
        if not EMAIL_RE.match(email):
            raise PolicyError(f"'{email}' is not a valid email address.")
        currency = str(raw.get("currency", "EUR")).strip().upper()
        if currency not in CURRENCIES:
            raise PolicyError(f"Currency must be one of {', '.join(sorted(CURRENCIES))}.")
        try:
            due_days = int(raw.get("due_days", 14))
        except (TypeError, ValueError):
            raise PolicyError("Payment term must be a whole number of days.") from None
        if not 1 <= due_days <= 90:
            raise PolicyError("Payment term must be between 1 and 90 days.")
        note = str(raw.get("note", "") or "").strip()[:200]

        raw_items = raw.get("items")
        if not isinstance(raw_items, list) or not 1 <= len(raw_items) <= 20:
            raise PolicyError("An invoice needs between 1 and 20 line items.")
        items = []
        for entry in raw_items:
            try:
                description = str(entry["description"]).strip()
                quantity = float(entry.get("quantity", 1))
                unit_price = round(float(entry["unit_price"]), 2)
            except (KeyError, TypeError, ValueError, AttributeError):
                raise PolicyError(
                    "Each line item needs a description, quantity and unit price."
                ) from None
            if not 1 <= len(description) <= 120:
                raise PolicyError("Line item descriptions must be 1 to 120 characters.")
            if quantity != int(quantity) or not 1 <= quantity <= 1000:
                raise PolicyError("Quantities must be whole numbers between 1 and 1000.")
            if unit_price <= 0:
                raise PolicyError("Unit prices must be greater than zero.")
            items.append(
                {"description": description, "quantity": int(quantity), "unit_price": unit_price}
            )

        spec = {
            "customer_name": name,
            "customer_email": email,
            "items": items,
            "currency": currency,
            "due_days": due_days,
            "note": note,
        }
        total = invoice_total(spec)
        if total > self.policy.max_invoice_amount:
            raise PolicyError(
                f"Invoices above {_money(self.policy.max_invoice_amount)} {currency} "
                "must be created directly in PayPal."
            )
        return spec

    def _new_proposal(self, kind: str, payload: JSON, summary: str) -> JSON:
        digest = payload_hash(kind, payload)
        for existing in self.store.list([PENDING]):
            if existing["kind"] == kind and existing["payload_hash"] == digest:
                return self._public(existing)  # same request again: reuse it
        proposal_id = uuid.uuid4().hex[:12]
        proposal = {
            "id": proposal_id,
            "kind": kind,
            "payload": payload,
            "payload_hash": digest,
            "summary": summary,
            "reference": f"STW-{proposal_id[:8].upper()}",
            "status": PENDING,
        }
        self.store.insert(proposal)
        self.store.log(proposal_id, "proposed", summary)
        return self._public(self._load(proposal_id))

    def propose_invoice(self, raw: JSON) -> JSON:
        spec = self._validate_invoice(raw)
        total = invoice_total(spec)
        summary = (
            f"Create and send an invoice for {_money(total)} {spec['currency']} to "
            f"{spec['customer_name']} <{spec['customer_email']}>, due in {spec['due_days']} days"
        )
        return self._new_proposal("invoice", spec, summary)

    def propose_reminder(self, invoice_id: str, note: str | None = None) -> JSON:
        invoice = self.port.get_invoice(str(invoice_id))
        if invoice is None:
            raise PolicyError(f"Invoice '{invoice_id}' does not exist.")
        if invoice.status != "open":
            raise PolicyError(
                f"Invoice {invoice.number} is {invoice.status}; "
                "reminders only apply to open invoices."
            )
        today = self.today()
        if (invoice.due - today).days > 3:
            raise PolicyError(
                f"Invoice {invoice.number} is not due until {invoice.due.isoformat()}; "
                "reminders start 3 days before the due date."
            )
        text = (note or "").strip()[:300] or (
            f"Hi {invoice.customer_name}, a friendly reminder that invoice {invoice.number} "
            f"({_money(invoice.amount)} {invoice.currency}) was due on {invoice.due.isoformat()}. "
            "If you have already paid, please ignore this message."
        )
        for other in self.store.list([PENDING, UNVERIFIED, DONE]):
            if other["kind"] != "reminder" or other["payload"]["invoice_id"] != invoice.id:
                continue
            if other["status"] == PENDING:
                if other["payload"]["note"] == text:
                    return self._public(other)  # the same reminder is already waiting
                raise PolicyError(
                    f"A different reminder for {invoice.number} is already waiting for approval. "
                    "Confirm or dismiss it first."
                )
            if other["status"] == UNVERIFIED:
                raise PolicyError(
                    f"A previous reminder for {invoice.number} has an unknown outcome. "
                    "Check PayPal before sending another."
                )
            sent_on = datetime.fromisoformat(other["updated_at"]).date()
            if (today - sent_on).days < self.policy.reminder_cooldown_days:
                raise PolicyError(
                    f"{invoice.number} was reminded on {sent_on.isoformat()}; "
                    f"wait {self.policy.reminder_cooldown_days} days between reminders."
                )

        payload = {"invoice_id": invoice.id, "invoice_number": invoice.number, "note": text}
        late = invoice.days_overdue(today)
        when = f"{late} days overdue" if late else f"due {invoice.due.isoformat()}"
        summary = (
            f"Send a payment reminder for {invoice.number} to {invoice.customer_name} "
            f"({_money(invoice.amount)} {invoice.currency}, {when})"
        )
        return self._new_proposal("reminder", payload, summary)

    # -- the human side ---------------------------------------------------------

    def confirm(self, proposal_id: str, reviewed_hash: str) -> JSON:
        proposal = self.store.get(proposal_id)
        if proposal is None:
            raise NotFound("Proposal not found.")
        if reviewed_hash != proposal["payload_hash"]:
            self.store.log(proposal_id, "refused", "hash mismatch")
            raise HashMismatch(
                "This proposal is not what you reviewed. Reload it and review it again."
            )
        status = proposal["status"]
        if status == DONE:
            return self._public(proposal)  # confirming again changes nothing
        if status == EXECUTING:
            raise Conflict("This proposal is already being executed.")
        if status in (FAILED, DISMISSED):
            raise Conflict(f"This proposal is {status}. Ask for a new one.")
        if status == UNVERIFIED and proposal["kind"] == "reminder":
            raise Conflict(
                "The outcome of this reminder is unknown. Check PayPal, then create a new "
                "reminder if the customer did not get it."
            )
        if not self.store.transition(proposal_id, [PENDING, UNVERIFIED], EXECUTING):
            current = self.store.get(proposal_id)
            if current and current["status"] == DONE:
                return self._public(current)
            raise Conflict("This proposal is already being executed.")

        self.store.log(proposal_id, "confirmed", f"from {status}")
        try:
            result = self._execute(proposal)
        except PayPalError as exc:
            self.store.transition(proposal_id, [EXECUTING], FAILED, error=str(exc))
            self.store.log(proposal_id, "failed", str(exc))
        except PayPalUncertain as exc:
            message = f"{exc} Outcome unknown; verify before retrying."
            self.store.transition(proposal_id, [EXECUTING], UNVERIFIED, error=message)
            self.store.log(proposal_id, "unverified", str(exc))
        except Exception as exc:  # any surprise means "we don't know"
            message = (
                f"Unexpected error ({type(exc).__name__}). Outcome unknown; verify before retrying."
            )
            self.store.transition(proposal_id, [EXECUTING], UNVERIFIED, error=message)
            self.store.log(proposal_id, "unverified", message)
        else:
            self.store.transition(proposal_id, [EXECUTING], DONE, result=result)
            self.store.log(proposal_id, "done", "")
        return self._public(self._load(proposal_id))

    def _execute(self, proposal: JSON) -> JSON:
        today = self.today()
        if proposal["kind"] == "invoice":
            # Look first: if an earlier attempt got through, reuse it, never duplicate it.
            invoice = self.port.find_by_reference(proposal["reference"])
            if invoice is None:
                invoice = self.port.create_invoice_draft(proposal["payload"], proposal["reference"])
            if invoice.status == "cancelled":
                raise PayPalError("This invoice already exists in PayPal but was cancelled.")
            if invoice.status == "draft":
                invoice = self.port.send_invoice(invoice.id)
            return {"invoice": invoice.to_dict(today)}
        payload = proposal["payload"]
        self.port.send_reminder(payload["invoice_id"], payload["note"])
        return {"invoice_id": payload["invoice_id"], "reminded_on": today.isoformat()}

    def verify(self, proposal_id: str) -> JSON:
        """Ask PayPal what really happened to an unverified invoice proposal."""
        proposal = self.store.get(proposal_id)
        if proposal is None:
            raise NotFound("Proposal not found.")
        if proposal["status"] != UNVERIFIED:
            return self._public(proposal)
        if proposal["kind"] != "invoice":
            raise Conflict("Reminders cannot be verified automatically. Check PayPal directly.")
        try:
            invoice = self.port.find_by_reference(proposal["reference"])
        except (PayPalError, PayPalUncertain) as exc:
            raise Conflict(f"Could not check PayPal right now: {exc}") from exc
        if invoice is not None and invoice.status in ("open", "paid"):
            self.store.transition(
                proposal_id, [UNVERIFIED], DONE, result={"invoice": invoice.to_dict(self.today())}
            )
            self.store.log(proposal_id, "verified", f"found {invoice.number} as {invoice.status}")
        elif invoice is not None:
            self.store.log(proposal_id, "verify", f"invoice exists as {invoice.status}, not sent")
        else:
            self.store.log(proposal_id, "verify", "no invoice with this reference yet")
        return self._public(self._load(proposal_id))

    def dismiss(self, proposal_id: str) -> JSON:
        proposal = self.store.get(proposal_id)
        if proposal is None:
            raise NotFound("Proposal not found.")
        if not self.store.transition(proposal_id, [PENDING], DISMISSED):
            raise Conflict(
                f"Only pending proposals can be dismissed (this one is {proposal['status']})."
            )
        self.store.log(proposal_id, "dismissed", "")
        return self._public(self._load(proposal_id))

    # -- reading ----------------------------------------------------------------

    def get(self, proposal_id: str) -> JSON:
        proposal = self.store.get(proposal_id)
        if proposal is None:
            raise NotFound("Proposal not found.")
        data = self._public(proposal)
        data["events"] = self.store.events(proposal_id)
        return data

    def list(self, statuses: builtins.list[str] | None = None) -> builtins.list[JSON]:
        return [self._public(p) for p in self.store.list(statuses)]

    def _load(self, proposal_id: str) -> JSON:
        proposal = self.store.get(proposal_id)
        if proposal is None:
            raise NotFound("Proposal not found.")
        return proposal

    @staticmethod
    def _public(proposal: JSON) -> JSON:
        keys = (
            "id",
            "kind",
            "summary",
            "payload",
            "payload_hash",
            "reference",
            "status",
            "result",
            "error",
            "created_at",
            "updated_at",
        )
        return {key: proposal[key] for key in keys}
