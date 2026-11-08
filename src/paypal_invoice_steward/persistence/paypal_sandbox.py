"""Client for the PayPal Invoicing v2 API, sandbox only.

The client refuses to talk to anything that is not a sandbox URL, so a
misconfiguration can never touch real money.
"""

from __future__ import annotations

import logging
import math
import re
import time
from collections.abc import Callable
from datetime import date, timedelta
from decimal import Decimal, InvalidOperation
from typing import Any

import httpx

from ..core.models import JSON, Invoice, invoice_content_digest
from ..core.ports import InvoiceInventoryIncomplete, PayPalError, PayPalUncertain

SANDBOX_URL = "https://api-m.sandbox.paypal.com"
INVOICING_SCOPE = "https://uri.paypal.com/services/invoicing"
INVOICE_PAGE_SIZE = 50
MAX_INVOICE_PAGES = 20  # refuse larger inventories, never truncate them
_INVOICE_ID = re.compile(r"[A-Za-z0-9][A-Za-z0-9_-]{0,79}\Z")


def _validate_invoice_id(invoice_id: str) -> None:
    """Accept one opaque path component, never URL syntax supplied by a tool."""
    if not isinstance(invoice_id, str) or _INVOICE_ID.fullmatch(invoice_id) is None:
        raise ValueError("Invalid invoice identifier.")


log = logging.getLogger(__name__)

# Every invoice status in PayPal Invoicing v2, as listed by the official PayPal Agent
# Toolkit (python/paypal_agent_toolkit/shared/invoices/parameters.py).
_OPEN = {"SENT", "UNPAID", "PARTIALLY_PAID", "PAYMENT_PENDING", "SCHEDULED", "SHARED"}
_PAID = {"PAID", "MARKED_AS_PAID", "PAID_EXTERNAL"}
_CANCELLED = {"CANCELLED", "AUTO_CANCELLED"}
_REFUND_REVIEW = {
    "REFUNDED",
    "PARTIALLY_REFUNDED",
    "MARKED_AS_REFUNDED",
    "REFUNDED_EXTERNAL",
}
_DRAFT = {"DRAFT"}


def _day(value: str | None) -> date | None:
    if not isinstance(value, str) or not value:
        return None
    try:
        return date.fromisoformat(value[:10])
    except ValueError:
        return None


def _required_invoice_day(value: Any) -> date:
    if not isinstance(value, str) or re.fullmatch(r"[0-9]{4}-[0-9]{2}-[0-9]{2}", value) is None:
        raise PayPalUncertain("PayPal invoice dates are missing or invalid.")
    result = _day(value)
    if result is None:
        raise PayPalUncertain("PayPal invoice dates are missing or invalid.")
    return result


_DECIMAL_2 = re.compile(r"(?:0|[1-9][0-9]*)(?:\.[0-9]{1,2})?\Z")


def _remaining_due(raw: JSON, currency: str) -> float | None:
    """Use the provider's due_amount, never an inferred face-minus-payments sum."""
    due = raw.get("due_amount")
    if not isinstance(due, dict) or due.get("currency_code") != currency:
        return None
    value = due.get("value")
    if currency not in {"EUR", "USD", "GBP"} or not isinstance(value, str):
        return None
    if len(value) > 32 or _DECIMAL_2.fullmatch(value) is None:
        return None
    result = float(value)
    return result if math.isfinite(result) else None


def _provider_content_digest(raw: JSON, currency: str) -> str | None:
    """Hash only a strict, normalized provider representation for action read-back."""
    detail = raw.get("detail")
    items = raw.get("items")
    if not isinstance(detail, dict) or not isinstance(items, list) or not items:
        return None
    note = detail.get("note", "")
    if not isinstance(note, str):
        return None
    normalized: list[JSON] = []
    for item in items:
        if not isinstance(item, dict) or not isinstance(item.get("name"), str):
            return None
        amount = item.get("unit_amount")
        quantity = item.get("quantity")
        if (
            not isinstance(amount, dict)
            or amount.get("currency_code") != currency
            or not isinstance(amount.get("value"), str)
            or _DECIMAL_2.fullmatch(amount["value"]) is None
            or not isinstance(quantity, str)
        ):
            return None
        try:
            units = Decimal(quantity)
        except InvalidOperation:
            return None
        if not units.is_finite() or units != units.to_integral_value() or units < 1:
            return None
        normalized.append(
            {
                "description": item["name"],
                "quantity": int(units),
                "unit_price": float(amount["value"]),
            }
        )
    return invoice_content_digest({"note": note, "items": normalized})


def _payment_provenance(raw: JSON, status: str) -> tuple[str, date | None]:
    """Identify PayPal-reported origin; missing or duplicated details stay uncertain."""
    payments = raw.get("payments")
    if payments is None:
        transactions: list[Any] = []
    elif isinstance(payments, dict) and isinstance(payments.get("transactions", []), list):
        transactions = payments.get("transactions", [])
    else:
        return "unknown", None
    kinds: set[str] = set()
    ids: set[str] = set()
    dates: list[date] = []
    complete_dates = bool(transactions)
    for row in transactions:
        if not isinstance(row, dict) or row.get("type") not in {"PAYPAL", "EXTERNAL"}:
            return "unknown", None
        kind = row["type"]
        kinds.add(kind)
        payment_id = row.get("payment_id")
        if kind == "PAYPAL" and not isinstance(payment_id, str):
            return "ambiguous", None
        if payment_id is not None:
            if not isinstance(payment_id, str) or not payment_id or payment_id in ids:
                return "ambiguous", None
            ids.add(payment_id)
        payment_date = _day(row.get("payment_date"))
        if payment_date is None:
            complete_dates = False
        else:
            dates.append(payment_date)
    if kinds == {"PAYPAL", "EXTERNAL"}:
        origin = "mixed"
    elif kinds == {"PAYPAL"}:
        origin = "paypal"
    elif kinds == {"EXTERNAL"}:
        origin = "external"
    elif status in {"PAID", "REFUNDED"}:
        origin = "paypal"
    elif status in {"MARKED_AS_PAID", "PAID_EXTERNAL", "MARKED_AS_REFUNDED"}:
        origin = "external"
    else:
        origin = "unknown"
    if status == "PAID" and "EXTERNAL" in kinds:
        return "ambiguous", None
    if status in {"MARKED_AS_PAID", "PAID_EXTERNAL"} and "PAYPAL" in kinds:
        return "ambiguous", None
    fully_paid = status in {"PAID", "MARKED_AS_PAID", "PAID_EXTERNAL"}
    paid_on = max(dates) if fully_paid and complete_dates and dates else None
    return origin, paid_on


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
    elif raw_status in _REFUND_REVIEW:
        # PayPal refunds can re-open receivables; never call them cancellations.
        status = "refund_review"
    elif raw_status in _DRAFT:
        status = "draft"
    else:
        # A status PayPal added after this code was written. Never guess: an
        # unknown invoice is left out of the forecast and gets no reminders.
        log.warning("Unknown PayPal invoice status %r on invoice %s", raw_status, raw.get("id"))
        status = "unknown"

    issued = _required_invoice_day(detail.get("invoice_date"))
    due = _required_invoice_day((detail.get("payment_term") or {}).get("due_date"))
    if due < issued:
        raise PayPalUncertain("PayPal invoice dates are inconsistent.")

    amount_obj = raw.get("amount")
    if not isinstance(amount_obj, dict) or not isinstance(amount_obj.get("currency_code"), str):
        raise PayPalUncertain("PayPal invoice face amount or currency is unavailable.")
    currency = amount_obj["currency_code"]
    amount = _remaining_due({"due_amount": amount_obj}, currency)
    if amount is None:
        raise PayPalUncertain("PayPal invoice face amount is invalid or unsupported.")
    if detail.get("currency_code") not in (None, currency):
        raise PayPalUncertain("PayPal invoice currencies are inconsistent.")

    recipients = raw.get("primary_recipients") or []
    billing = (recipients[0].get("billing_info") if recipients else None) or {}
    name_obj = billing.get("name") or {}
    full_name = " ".join(
        part for part in (name_obj.get("given_name"), name_obj.get("surname")) if part
    )
    customer_name = billing.get("business_name") or full_name or "Unknown customer"

    origin, paid = _payment_provenance(raw, raw_status)
    remaining = _remaining_due(raw, currency)

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
        remaining_amount=remaining,
        balance_source=(
            "paypal_due_amount"
            if remaining is not None and status != "refund_review"
            else "unverified"
        ),
        payment_origin=origin,
        provider_status=raw_status,
        content_digest=_provider_content_digest(raw, currency),
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
        expected_app_id: str | None = None,
    ) -> None:
        if base_url.rstrip("/") != SANDBOX_URL:
            raise ValueError("Invoice Steward only connects to the official PayPal sandbox.")
        if not client_id.strip() or not client_secret.strip():
            raise ValueError("PayPal sandbox credentials must not be empty.")
        self._client_id = client_id
        self._client_secret = client_secret
        self._expected_app_id = expected_app_id
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
        try:
            body = resp.json()
        except ValueError:
            raise PayPalError("PayPal returned malformed OAuth token metadata.") from None
        if not isinstance(body, dict):
            raise PayPalError("PayPal returned malformed OAuth token metadata.")
        token = body.get("access_token")
        scope = body.get("scope")
        app_id = body.get("app_id")
        token_type = body.get("token_type")
        expiry = body.get("expires_in")
        if (
            not isinstance(token, str)
            or not token
            or any(c.isspace() for c in token)
            or not isinstance(token_type, str)
            or token_type.lower() != "bearer"
            or not isinstance(scope, str)
            or INVOICING_SCOPE not in scope.split()
            or not isinstance(app_id, str)
            or not app_id.strip()
        ):
            raise PayPalError("PayPal token lacks verified invoicing authorization.")
        if self._expected_app_id and app_id != self._expected_app_id:
            raise PayPalError("PayPal sandbox app ID does not match the configured app.")
        if expiry is None or isinstance(expiry, bool):
            raise PayPalError("PayPal returned an invalid OAuth token lifetime.")
        try:
            lifetime = float(expiry)
        except (TypeError, ValueError):
            raise PayPalError("PayPal returned an invalid OAuth token lifetime.") from None
        if not math.isfinite(lifetime) or lifetime <= 0:
            raise PayPalError("PayPal returned an invalid OAuth token lifetime.")
        self._token = token
        self._token_expires = time.time() + min(lifetime, 86_400.0)
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
            raise PayPalUncertain(
                f"No response from PayPal ({type(exc).__name__}).",
                reason_code="provider_transport_failure",
            ) from exc

        # Only replay safe GET requests after a token refresh. Invoicing POST
        # operations (including send/remind) must not be automatically replayed.
        if resp.status_code == 401 and _retry and method.upper() == "GET":
            self._token = None
            return self._request(
                method, path, json=json, params=params, headers=headers, _retry=False
            )
        if resp.status_code >= 500:
            raise PayPalUncertain(
                f"PayPal answered with an error (HTTP {resp.status_code}).",
                reason_code="provider_server_error",
            )
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
        """Return a complete, count-verified page walk or raise; never return partial data.

        A successful read proves pagination consistency for this API/app request,
        not a stable cross-page snapshot or all invoices owned by a merchant.
        """
        invoices: list[Invoice] = []
        seen_ids: set[str] = set()
        expected_pages: int | None = None
        expected_items: int | None = None
        page = 1
        while True:
            data = self._request(
                "GET",
                "/v2/invoicing/invoices",
                params={
                    "page": page,
                    "page_size": INVOICE_PAGE_SIZE,
                    "total_required": "true",
                },
            )
            if not isinstance(data, dict):
                raise InvoiceInventoryIncomplete("Invoice list has no valid JSON object.")
            pages = data.get("total_pages")
            count = data.get("total_items")
            items = data.get("items")
            if items is None and "items" not in data and pages == 0 and count == 0:
                items = []
            if (
                type(pages) is not int
                or type(count) is not int
                or pages < 0
                or count < 0
                or not isinstance(items, list)
                or len(items) > INVOICE_PAGE_SIZE
            ):
                raise InvoiceInventoryIncomplete("Invoice list pagination metadata is invalid.")
            if expected_pages is None:
                if pages > MAX_INVOICE_PAGES or count > MAX_INVOICE_PAGES * INVOICE_PAGE_SIZE:
                    raise InvoiceInventoryIncomplete(
                        "Invoice inventory exceeds the supported page limit."
                    )
                if (pages == 0 and count != 0) or (count == 0 and pages > 1):
                    raise InvoiceInventoryIncomplete(
                        "Invoice list has inconsistent empty-page metadata."
                    )
                if pages > 0 and count > pages * INVOICE_PAGE_SIZE:
                    raise InvoiceInventoryIncomplete("Invoice count cannot fit reported pages.")
                expected_pages, expected_items = pages, count
            elif pages != expected_pages or count != expected_items:
                raise InvoiceInventoryIncomplete("Invoice list totals changed during pagination.")
            if pages == 0 and items:
                raise InvoiceInventoryIncomplete("Invoice list returned items with zero pages.")
            for raw in items:
                if not isinstance(raw, dict):
                    raise InvoiceInventoryIncomplete("Invoice list contains an invalid record.")
                invoice_id = raw.get("id")
                if not isinstance(invoice_id, str) or not invoice_id.strip():
                    raise InvoiceInventoryIncomplete("Invoice list record has no valid ID.")
                if invoice_id in seen_ids:
                    raise InvoiceInventoryIncomplete("Invoice ID repeated across inventory pages.")
                seen_ids.add(invoice_id)
                try:
                    invoices.append(normalize_invoice(raw))
                except (TypeError, ValueError, KeyError, AttributeError):
                    raise InvoiceInventoryIncomplete(
                        "Invoice list record cannot be parsed."
                    ) from None
            if pages == 0 or page == pages:
                if len(invoices) != count:
                    raise InvoiceInventoryIncomplete(
                        "Invoice count differs from the declared total."
                    )
                return invoices
            page += 1

    def get_invoice(self, invoice_id: str) -> Invoice | None:
        _validate_invoice_id(invoice_id)
        try:
            data = self._request("GET", f"/v2/invoicing/invoices/{invoice_id}")
        except PayPalError as exc:
            if exc.status_code == 404:
                return None
            raise
        if not data or data.get("id") != invoice_id:
            raise PayPalUncertain(
                "PayPal invoice read-back identity could not be verified.",
                reason_code="provider_identity_mismatch",
            )
        try:
            return normalize_invoice(data)
        except PayPalUncertain as exc:
            raise PayPalUncertain(
                "PayPal invoice read-back cannot be verified.",
                reason_code="provider_readback_invalid",
            ) from exc

    def find_by_reference(self, reference: str) -> Invoice | None:
        data = self._request(
            "POST",
            "/v2/invoicing/search-invoices",
            params={"page": 1, "page_size": 10, "total_required": "true"},
            json={"invoice_number": reference},
        )
        if data is None:
            raise PayPalUncertain(
                "Invoice reference search returned no usable response.",
                reason_code="provider_reference_search_invalid",
            )
        items, total, pages = data.get("items"), data.get("total_items"), data.get("total_pages")
        if (
            not isinstance(items, list)
            or type(total) is not int
            or type(pages) is not int
            or total != len(items)
            or not 0 <= total <= 10
            or pages not in ({0, 1} if total == 0 else {1})
        ):
            raise PayPalUncertain(
                "Invoice reference search is incomplete or inconsistent.",
                reason_code="provider_reference_search_invalid",
            )
        matches: list[str] = []
        seen: set[str] = set()
        for item in items:
            if not isinstance(item, dict) or not isinstance(item.get("detail"), dict):
                raise PayPalUncertain(
                    "Invoice reference search contains invalid records.",
                    reason_code="provider_reference_search_invalid",
                )
            invoice_id = item.get("id")
            if not isinstance(invoice_id, str):
                raise PayPalUncertain(
                    "Invoice reference search has no usable identity.",
                    reason_code="provider_reference_search_invalid",
                )
            try:
                _validate_invoice_id(invoice_id)
            except ValueError:
                raise PayPalUncertain(
                    "Invoice reference search has an invalid identity.",
                    reason_code="provider_reference_search_invalid",
                ) from None
            if invoice_id in seen or not isinstance(item["detail"].get("invoice_number"), str):
                raise PayPalUncertain(
                    "Invoice reference search contains ambiguous records.",
                    reason_code="provider_reference_search_invalid",
                )
            seen.add(invoice_id)
            if item["detail"]["invoice_number"] == reference:
                matches.append(invoice_id)
        if len(matches) > 1:
            raise PayPalUncertain(
                "More than one invoice matches the approved reference.",
                reason_code="provider_reference_search_invalid",
            )
        if not matches:
            return None
        invoice = self.get_invoice(matches[0])
        if invoice is None or invoice.number != reference:
            raise PayPalUncertain(
                "Invoice reference changed or disappeared during read-back.",
                reason_code="provider_reference_changed",
            )
        return invoice

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
            raise PayPalUncertain(
                "PayPal accepted the draft but did not return its id.",
                reason_code="provider_create_response_invalid",
            )
        invoice = self.get_invoice(invoice_id)
        if invoice is None:
            raise PayPalUncertain(
                "The new draft could not be read back from PayPal.",
                reason_code="provider_readback_missing",
            )
        return invoice

    def send_invoice(self, invoice_id: str) -> Invoice:
        _validate_invoice_id(invoice_id)
        self._request(
            "POST",
            f"/v2/invoicing/invoices/{invoice_id}/send",
            json={
                "send_to_recipient": True,
                "send_to_invoicer": False,
                "additional_recipients": [],
            },
        )
        invoice = self.get_invoice(invoice_id)
        if invoice is None:
            raise PayPalUncertain(
                "The invoice could not be read back after sending.",
                reason_code="provider_readback_missing",
            )
        return invoice

    def send_reminder(self, invoice_id: str, note: str) -> None:
        _validate_invoice_id(invoice_id)
        self._request(
            "POST",
            f"/v2/invoicing/invoices/{invoice_id}/remind",
            # PayPal ignores custom subject/note; explicit empty CC avoids inherited copies.
            json={
                "send_to_recipient": True,
                "send_to_invoicer": False,
                "additional_recipients": [],
            },
        )
