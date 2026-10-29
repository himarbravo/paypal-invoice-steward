"""Client for the PayPal Invoicing v2 API, sandbox only.

The client refuses to talk to anything that is not a sandbox URL, so a
misconfiguration can never touch real money.
"""

from __future__ import annotations

import logging
import time
from collections.abc import Callable
from datetime import date, timedelta
from typing import Any

import httpx

from ..core.models import JSON, Invoice
from ..core.ports import PayPalError, PayPalUncertain

SANDBOX_URL = "https://api-m.sandbox.paypal.com"

log = logging.getLogger(__name__)

# Every invoice status in PayPal Invoicing v2, as listed by the official PayPal Agent
# Toolkit (python/paypal_agent_toolkit/shared/invoices/parameters.py).
_OPEN = {"SENT", "UNPAID", "PARTIALLY_PAID", "PAYMENT_PENDING", "SCHEDULED", "SHARED"}
_PAID = {"PAID", "MARKED_AS_PAID", "PAID_EXTERNAL"}
_CANCELLED = {
    "CANCELLED",
    "AUTO_CANCELLED",
    "REFUNDED",
    "PARTIALLY_REFUNDED",
    "MARKED_AS_REFUNDED",
    "REFUNDED_EXTERNAL",
}
_DRAFT = {"DRAFT"}


def _day(value: str | None) -> date | None:
    if not value:
        return None
    try:
        return date.fromisoformat(value[:10])
    except ValueError:
        return None


def normalize_invoice(raw: JSON) -> Invoice:
    """Turn a PayPal v2 invoice object into our flat Invoice."""
    detail = raw.get("detail") or {}
    raw_status = str(raw.get("status", "")).upper()
    if raw_status in _PAID:
        status = "paid"
    elif raw_status in _OPEN:
        status = "open"
    elif raw_status in _CANCELLED:
        status = "cancelled"
    elif raw_status in _DRAFT:
        status = "draft"
    else:
        # A status PayPal added after this code was written. Never guess: an
        # unknown invoice is left out of the forecast and gets no reminders.
        log.warning("Unknown PayPal invoice status %r on invoice %s", raw_status, raw.get("id"))
        status = "unknown"

    issued = _day(detail.get("invoice_date")) or date.today()
    due = _day((detail.get("payment_term") or {}).get("due_date")) or issued

    amount_obj = raw.get("amount") or {}
    if amount_obj.get("value") is not None:
        amount = float(amount_obj["value"])
    else:
        amount = sum(
            float(i.get("quantity", 1)) * float((i.get("unit_amount") or {}).get("value", 0))
            for i in raw.get("items", [])
        )
    currency = amount_obj.get("currency_code") or detail.get("currency_code") or "USD"

    recipients = raw.get("primary_recipients") or []
    billing = (recipients[0].get("billing_info") if recipients else None) or {}
    name_obj = billing.get("name") or {}
    full_name = " ".join(
        part for part in (name_obj.get("given_name"), name_obj.get("surname")) if part
    )
    customer_name = billing.get("business_name") or full_name or "Unknown customer"

    paid = None
    transactions = (raw.get("payments") or {}).get("transactions") or []
    if status == "paid" and transactions:
        paid = _day(transactions[-1].get("payment_date"))
    if status == "paid" and paid is None:
        paid = due

    return Invoice(
        id=str(raw.get("id", "")),
        number=str(detail.get("invoice_number") or raw.get("id", "")),
        customer_name=customer_name,
        customer_email=str(billing.get("email_address", "")),
        amount=round(amount, 2),
        currency=currency,
        status=status,
        issued=issued,
        due=due,
        paid=paid,
    )


class SandboxPayPal:
    mode = "sandbox"

    def __init__(
        self,
        client_id: str,
        client_secret: str,
        base_url: str = SANDBOX_URL,
        transport: httpx.BaseTransport | None = None,
        today: Callable[[], date] = date.today,
        timeout: float = 15.0,
    ) -> None:
        if "sandbox" not in base_url:
            raise ValueError("Invoice Steward only talks to the PayPal sandbox.")
        self._client_id = client_id
        self._client_secret = client_secret
        self._today = today
        self._http = httpx.Client(base_url=base_url, timeout=timeout, transport=transport)
        self._token: str | None = None
        self._token_expires = 0.0

    # -- plumbing ---------------------------------------------------------------

    def _get_token(self) -> str:
        if self._token and time.time() < self._token_expires - 30:
            return self._token
        try:
            resp = self._http.post(
                "/v1/oauth2/token",
                auth=(self._client_id, self._client_secret),
                data={"grant_type": "client_credentials"},
            )
        except httpx.HTTPError as exc:
            # Nothing has been asked of PayPal yet, so this is a clean failure.
            raise PayPalError(
                f"Could not reach PayPal to authenticate ({type(exc).__name__})."
            ) from exc
        if resp.status_code != 200:
            raise PayPalError("PayPal rejected the sandbox credentials.", resp.status_code)
        body = resp.json()
        token = str(body["access_token"])
        self._token = token
        self._token_expires = time.time() + float(body.get("expires_in", 300))
        return token

    @staticmethod
    def _error_message(resp: httpx.Response) -> str:
        try:
            body = resp.json()
        except ValueError:
            return f"PayPal returned HTTP {resp.status_code}."
        message = body.get("message") or body.get("name") or f"HTTP {resp.status_code}"
        details = body.get("details") or []
        if details:
            first = details[0]
            extra = first.get("description") or first.get("issue")
            if extra:
                message = f"{message}: {extra}"
        return str(message)

    def _request(
        self,
        method: str,
        path: str,
        *,
        json: JSON | None = None,
        params: dict[str, Any] | None = None,
        headers: dict[str, str] | None = None,
        _retry: bool = True,
    ) -> JSON | None:
        token = self._get_token()
        request_headers = {"Authorization": f"Bearer {token}", **(headers or {})}
        try:
            resp = self._http.request(
                method, path, json=json, params=params, headers=request_headers
            )
        except httpx.HTTPError as exc:
            raise PayPalUncertain(f"No response from PayPal ({type(exc).__name__}).") from exc

        if resp.status_code == 401 and _retry:
            self._token = None
            return self._request(
                method, path, json=json, params=params, headers=headers, _retry=False
            )
        if resp.status_code >= 500:
            raise PayPalUncertain(f"PayPal answered with an error (HTTP {resp.status_code}).")
        if resp.status_code >= 400:
            raise PayPalError(self._error_message(resp), resp.status_code)
        if not resp.content:
            return None
        try:
            data = resp.json()
        except ValueError:
            return None
        return data if isinstance(data, dict) else None

    # -- PayPalPort -------------------------------------------------------------

    def list_invoices(self) -> list[Invoice]:
        invoices: list[Invoice] = []
        page, page_size = 1, 50
        while page <= 20:
            data = (
                self._request(
                    "GET",
                    "/v2/invoicing/invoices",
                    params={"page": page, "page_size": page_size, "total_required": "true"},
                )
                or {}
            )
            items = data.get("items", [])
            invoices.extend(normalize_invoice(item) for item in items)
            if len(items) < page_size:
                break
            page += 1
        return invoices

    def get_invoice(self, invoice_id: str) -> Invoice | None:
        try:
            data = self._request("GET", f"/v2/invoicing/invoices/{invoice_id}")
        except PayPalError as exc:
            if exc.status_code == 404:
                return None
            raise
        return normalize_invoice(data) if data else None

    def find_by_reference(self, reference: str) -> Invoice | None:
        data = (
            self._request(
                "POST",
                "/v2/invoicing/search-invoices",
                params={"page": 1, "page_size": 10},
                json={"invoice_number": reference},
            )
            or {}
        )
        for item in data.get("items", []):
            invoice = normalize_invoice(item)
            if invoice.number == reference:
                return invoice
        return None

    def create_invoice_draft(self, spec: JSON, reference: str) -> Invoice:
        today = self._today()
        currency = spec["currency"]
        body = {
            "detail": {
                "invoice_number": reference,
                "invoice_date": today.isoformat(),
                "currency_code": currency,
                "note": spec.get("note", ""),
                "payment_term": {
                    "term_type": "DUE_ON_DATE_SPECIFIED",
                    "due_date": (today + timedelta(days=int(spec["due_days"]))).isoformat(),
                },
            },
            "primary_recipients": [
                {
                    "billing_info": {
                        "business_name": spec["customer_name"],
                        "email_address": spec["customer_email"],
                    }
                }
            ],
            "items": [
                {
                    "name": item["description"],
                    "quantity": str(item["quantity"]),
                    "unit_amount": {
                        "currency_code": currency,
                        "value": f"{float(item['unit_price']):.2f}",
                    },
                }
                for item in spec["items"]
            ],
        }
        data = (
            self._request(
                "POST",
                "/v2/invoicing/invoices",
                json=body,
                headers={"PayPal-Request-Id": reference},
            )
            or {}
        )
        invoice_id = data.get("id") or str(data.get("href", "")).rstrip("/").split("/")[-1]
        if not invoice_id:
            raise PayPalUncertain("PayPal accepted the draft but did not return its id.")
        invoice = self.get_invoice(invoice_id)
        if invoice is None:
            raise PayPalUncertain("The new draft could not be read back from PayPal.")
        return invoice

    def send_invoice(self, invoice_id: str) -> Invoice:
        self._request(
            "POST",
            f"/v2/invoicing/invoices/{invoice_id}/send",
            json={"send_to_recipient": True, "send_to_invoicer": False},
        )
        invoice = self.get_invoice(invoice_id)
        if invoice is None:
            raise PayPalUncertain("The invoice could not be read back after sending.")
        return invoice

    def send_reminder(self, invoice_id: str, note: str) -> None:
        self._request(
            "POST",
            f"/v2/invoicing/invoices/{invoice_id}/remind",
            json={"subject": "Payment reminder", "note": note, "send_to_invoicer": False},
        )
