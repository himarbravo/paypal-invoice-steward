from collections.abc import Callable
from datetime import date

import httpx
import pytest

from paypal_invoice_steward.core.models import JSON
from paypal_invoice_steward.core.ports import PayPalError, PayPalPort, PayPalUncertain
from paypal_invoice_steward.persistence.paypal_sandbox import SandboxPayPal, normalize_invoice

TODAY = date(2026, 10, 29)
Handler = Callable[[httpx.Request], httpx.Response]

RAW: JSON = {
    "id": "INV2-AAAA",
    "status": "SENT",
    "detail": {
        "invoice_number": "STW-1",
        "invoice_date": "2026-10-01",
        "payment_term": {"due_date": "2026-10-15"},
    },
    "amount": {"currency_code": "EUR", "value": "450.00"},
    "primary_recipients": [{"billing_info": {"business_name": "Alba", "email_address": "a@b.co"}}],
}


def make(handler: Handler) -> SandboxPayPal:
    return SandboxPayPal(
        "id", "secret", transport=httpx.MockTransport(handler), today=lambda: TODAY
    )


def token_then(handler: Handler) -> Handler:
    def wrapper(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/v1/oauth2/token":
            return httpx.Response(200, json={"access_token": "t", "expires_in": 300})
        return handler(request)

    return wrapper


def test_refuses_non_sandbox_url() -> None:
    with pytest.raises(ValueError):
        SandboxPayPal("i", "s", base_url="https://api-m.paypal.com")


def test_normalize() -> None:
    inv = normalize_invoice(RAW)
    assert (inv.status, inv.amount, inv.currency, inv.customer_name) == (
        "open",
        450.0,
        "EUR",
        "Alba",
    )
    assert normalize_invoice({**RAW, "status": "PAID"}).status == "paid"
    assert normalize_invoice({**RAW, "status": "CANCELLED"}).status == "cancelled"
    assert normalize_invoice({**RAW, "status": "DRAFT"}).status == "draft"


def test_create_sends_idempotency_header_and_reads_back() -> None:
    seen: dict[str, str | None] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        if request.method == "POST" and request.url.path == "/v2/invoicing/invoices":
            seen["rid"] = request.headers.get("PayPal-Request-Id")
            return httpx.Response(201, json={"href": "https://x/v2/invoicing/invoices/INV2-AAAA"})
        return httpx.Response(200, json=RAW)

    spec = {
        "customer_name": "Alba",
        "customer_email": "a@b.co",
        "currency": "EUR",
        "due_days": 14,
        "items": [{"description": "Logo", "quantity": 1, "unit_price": 450}],
    }
    inv = make(token_then(handler)).create_invoice_draft(spec, "STW-1")
    assert seen["rid"] == "STW-1" and inv.id == "INV2-AAAA"


def test_5xx_and_network_errors_are_uncertain() -> None:
    port = make(token_then(lambda r: httpx.Response(503)))
    with pytest.raises(PayPalUncertain):
        port.send_reminder("X", "hi")

    def boom(request: httpx.Request) -> httpx.Response:
        raise httpx.ReadTimeout("slow")

    with pytest.raises(PayPalUncertain):
        make(token_then(boom)).send_reminder("X", "hi")


def test_4xx_is_definitive_error() -> None:
    port = make(
        token_then(
            lambda r: httpx.Response(422, json={"message": "bad", "details": [{"issue": "WHY"}]})
        )
    )
    with pytest.raises(PayPalError, match="WHY"):
        port.send_reminder("X", "hi")


def test_bad_credentials() -> None:
    port = make(lambda r: httpx.Response(401))
    with pytest.raises(PayPalError, match="credentials"):
        port.list_invoices()


def test_get_invoice_404_returns_none() -> None:
    port = make(token_then(lambda r: httpx.Response(404, json={"message": "nf"})))
    assert port.get_invoice("nope") is None


def test_find_by_reference_matches_exact_number() -> None:
    port = make(token_then(lambda r: httpx.Response(200, json={"items": [RAW]})))
    assert port.find_by_reference("STW-1").id == "INV2-AAAA"
    assert port.find_by_reference("STW-2") is None


def test_expired_token_is_refreshed_once() -> None:
    calls = {"n": 0}

    def handler(request: httpx.Request) -> httpx.Response:
        calls["n"] += 1
        return httpx.Response(401) if calls["n"] == 1 else httpx.Response(200, json={"items": []})

    assert make(token_then(handler)).list_invoices() == []


def test_satisfies_the_port() -> None:
    port: PayPalPort = make(lambda r: httpx.Response(200, json={}))
    assert port.mode == "sandbox"


@pytest.mark.parametrize(
    ("paypal_status", "expected"),
    [
        ("DRAFT", "draft"),
        ("SENT", "open"),
        ("SCHEDULED", "open"),
        ("UNPAID", "open"),
        ("PARTIALLY_PAID", "open"),
        ("PAYMENT_PENDING", "open"),
        ("SHARED", "open"),
        ("PAID", "paid"),
        ("MARKED_AS_PAID", "paid"),
        ("PAID_EXTERNAL", "paid"),
        ("CANCELLED", "cancelled"),
        ("AUTO_CANCELLED", "cancelled"),
        ("REFUNDED", "cancelled"),
        ("PARTIALLY_REFUNDED", "cancelled"),
        ("MARKED_AS_REFUNDED", "cancelled"),
        ("REFUNDED_EXTERNAL", "cancelled"),
        ("SOMETHING_NEW", "unknown"),
        ("", "unknown"),
    ],
)
def test_every_paypal_status_is_mapped(paypal_status: str, expected: str) -> None:
    assert normalize_invoice({**RAW, "status": paypal_status}).status == expected
