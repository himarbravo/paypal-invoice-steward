from collections.abc import Callable
from datetime import date

import httpx
import pytest

from paypal_invoice_steward.core.models import JSON
from paypal_invoice_steward.core.ports import (
    InvoiceInventoryIncomplete,
    PayPalError,
    PayPalPort,
    PayPalUncertain,
)
from paypal_invoice_steward.persistence.paypal_sandbox import (
    INVOICING_SCOPE,
    INVOICE_PAGE_SIZE,
    MAX_INVOICE_PAGES,
    SandboxPayPal,
    normalize_invoice,
)

TODAY = date(2026, 10, 29)
Handler = Callable[[httpx.Request], httpx.Response]

OAUTH_TOKEN: JSON = {
    "access_token": "t",
    "token_type": "Bearer",
    "scope": "openid https://uri.paypal.com/services/invoicing",
    "app_id": "APP-SANDBOX-TEST",
    "expires_in": 300,
}

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
            return httpx.Response(200, json=OAUTH_TOKEN)
        return handler(request)

    return wrapper


def test_refuses_non_sandbox_url() -> None:
    with pytest.raises(ValueError):
        SandboxPayPal("i", "s", base_url="https://api-m.paypal.com")


@pytest.mark.parametrize(
    "url",
    [
        "https://sandbox.example.com",
        "https://api-m.sandbox.paypal.com.evil.example",
        "https://api-m.sandbox.paypal.com@evil.example",
        "http://api-m.sandbox.paypal.com",
        "https://api-m.sandbox.paypal.com:444",
        "https://api-m.sandbox.paypal.com?redirect=evil.example",
        "https://api-m.paypal.com",
    ],
)
def test_refuses_untrusted_or_insecure_sandbox_lookalikes(url: str) -> None:
    with pytest.raises(ValueError, match="official PayPal sandbox"):
        SandboxPayPal("i", "s", base_url=url)


def test_accepts_canonical_sandbox_with_trailing_slash() -> None:
    port = SandboxPayPal("i", "s", base_url="https://api-m.sandbox.paypal.com/")
    assert port.mode == "sandbox"


@pytest.mark.parametrize(
    ("client_id", "client_secret"),
    [("", "secret"), ("id", ""), (" ", "secret"), ("id", " ")],
)
def test_refuses_blank_credentials(client_id: str, client_secret: str) -> None:
    with pytest.raises(ValueError, match="credentials"):
        SandboxPayPal(client_id, client_secret)


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
        return httpx.Response(401) if calls["n"] == 1 else httpx.Response(200, json={"items": [], "total_pages": 0, "total_items": 0})

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


@pytest.mark.parametrize(
    "override",
    [
        {"scope": ""},
        {"scope": "https://uri.paypal.com/services/invoicing-extra"},
        {"scope": "https://uri.paypal.com/services"},
        {"scope": None},
        {"token_type": "Basic"},
        {"token_type": None},
        {"app_id": ""},
        {"app_id": None},
        {"access_token": ""},
        {"access_token": "with newline\n"},
        {"expires_in": 0},
        {"expires_in": -5},
        {"expires_in": "nan"},
        {"expires_in": None},
    ],
)
def test_invalid_oauth_metadata_blocks_invoicing_before_request(
    override: JSON,
) -> None:
    calls: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        calls.append(request.url.path)
        if request.url.path == "/v1/oauth2/token":
            return httpx.Response(200, json={**OAUTH_TOKEN, **override})
        raise AssertionError("Invoice API must not be called with invalid OAuth authority.")

    with pytest.raises(PayPalError):
        make(handler).list_invoices()
    assert calls == ["/v1/oauth2/token"]


def test_paypal_app_pin_rejects_another_app_before_invoice_call() -> None:
    calls: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        calls.append(request.url.path)
        if request.url.path == "/v1/oauth2/token":
            return httpx.Response(200, json=OAUTH_TOKEN)
        raise AssertionError("Must reject wrong PayPal app before requesting invoices.")

    port = SandboxPayPal(
        "id",
        "secret",
        transport=httpx.MockTransport(handler),
        expected_app_id="APP-DIFFERENT",
    )
    with pytest.raises(PayPalError, match="app ID"):
        port.list_invoices()
    assert calls == ["/v1/oauth2/token"]


def test_matching_app_pin_and_scope_allow_sandbox_read() -> None:
    paths: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        paths.append(request.url.path)
        if request.url.path == "/v1/oauth2/token":
            return httpx.Response(200, json=OAUTH_TOKEN)
        return httpx.Response(200, json={"items": [], "total_pages": 0, "total_items": 0})

    port = SandboxPayPal(
        "id",
        "secret",
        transport=httpx.MockTransport(handler),
        expected_app_id="APP-SANDBOX-TEST",
    )
    assert port.list_invoices() == []
    assert paths == ["/v1/oauth2/token", "/v2/invoicing/invoices"]


def test_401_on_post_does_not_automatically_replay_sandbox_send() -> None:
    paths: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        paths.append(request.url.path)
        if request.url.path == "/v1/oauth2/token":
            return httpx.Response(200, json=OAUTH_TOKEN)
        return httpx.Response(401, json={"message": "Unauthorized"})

    with pytest.raises(PayPalError):
        make(handler).send_reminder("INV2-AAAA", "Test")
    assert paths == ["/v1/oauth2/token", "/v2/invoicing/invoices/INV2-AAAA/remind"]


def test_missing_oauth_response_body_is_rejected_safely() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, content=b"not json")

    with pytest.raises(PayPalError, match="malformed OAuth"):
        make(handler).list_invoices()


def test_scope_contract_in_test_fixtures_matches_provider_documentation() -> None:
    assert INVOICING_SCOPE in OAUTH_TOKEN["scope"].split()


# The tests below use real v2 pagination field names over httpx.MockTransport.
# No responses are fabricated by the production adapter and no network is used.
def listed_invoice(n: int) -> JSON:
    return {
        **RAW,
        "id": f"INV2-{n:06d}",
        "detail": {**RAW["detail"], "invoice_number": f"STW-{n:06d}"},
    }


def inventory_handler(
    pages: dict[int, list[JSON]],
    total_items: int,
    *,
    total_pages: int | None = None,
    overrides: dict[int, JSON] | None = None,
    seen_pages: list[int] | None = None,
) -> Handler:
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/v2/invoicing/invoices"
        assert request.url.params["page_size"] == str(INVOICE_PAGE_SIZE)
        assert request.url.params["total_required"] == "true"
        page = int(request.url.params["page"])
        if seen_pages is not None:
            seen_pages.append(page)
        payload: JSON = {
            "items": pages.get(page, []),
            "total_items": total_items,
            "total_pages": len(pages) if total_pages is None else total_pages,
        }
        payload.update((overrides or {}).get(page, {}))
        return httpx.Response(200, json=payload)

    return handler


def test_invoice_pages_are_all_read_even_when_first_page_is_short() -> None:
    seen: list[int] = []
    handler = inventory_handler(
        {1: [listed_invoice(1)], 2: [listed_invoice(2)]},
        total_items=2,
        seen_pages=seen,
    )
    results = make(token_then(handler)).list_invoices()
    assert [i.id for i in results] == ["INV2-000001", "INV2-000002"]
    assert seen == [1, 2]


@pytest.mark.parametrize("total_pages", [0, 1])
def test_empty_inventory_requires_consistent_count_metadata(total_pages: int) -> None:
    handler = inventory_handler({1: []}, 0, total_pages=total_pages)
    assert make(token_then(handler)).list_invoices() == []


def test_full_20_page_limit_is_returned_without_truncation() -> None:
    seen: list[int] = []
    pages = {
        page: [
            listed_invoice((page - 1) * INVOICE_PAGE_SIZE + i)
            for i in range(INVOICE_PAGE_SIZE)
        ]
        for page in range(1, MAX_INVOICE_PAGES + 1)
    }
    data = make(token_then(inventory_handler(
        pages, MAX_INVOICE_PAGES * INVOICE_PAGE_SIZE, seen_pages=seen
    ))).list_invoices()
    assert len(data) == MAX_INVOICE_PAGES * INVOICE_PAGE_SIZE
    assert len({i.id for i in data}) == len(data)
    assert seen == list(range(1, MAX_INVOICE_PAGES + 1))


def test_inventory_above_page_cap_fails_before_truncation() -> None:
    seen: list[int] = []
    handler = inventory_handler(
        {1: [listed_invoice(1)]},
        total_items=(MAX_INVOICE_PAGES + 1) * INVOICE_PAGE_SIZE,
        total_pages=MAX_INVOICE_PAGES + 1,
        seen_pages=seen,
    )
    with pytest.raises(InvoiceInventoryIncomplete, match="page limit"):
        make(token_then(handler)).list_invoices()
    assert seen == [1]


@pytest.mark.parametrize(
    "bad",
    [
        {"total_items": None},
        {"total_pages": None},
        {"total_items": True},
        {"total_pages": "1"},
        {"total_items": -1},
        {"total_pages": -1},
        {"items": None},
        {"items": {}},
        {"total_pages": 0, "total_items": 3},
    ],
)
def test_missing_or_invalid_pagination_metadata_fails_closed(bad: JSON) -> None:
    handler = inventory_handler({1: []}, 0, overrides={1: bad})
    with pytest.raises(InvoiceInventoryIncomplete):
        make(token_then(handler)).list_invoices()


def test_second_page_missing_item_fails_instead_of_returning_partial_total() -> None:
    pages = {1: [listed_invoice(1)], 2: []}
    with pytest.raises(InvoiceInventoryIncomplete, match="count differs"):
        make(token_then(inventory_handler(pages, 2))).list_invoices()


def test_totals_changing_between_pages_are_not_treated_as_complete() -> None:
    pages = {1: [listed_invoice(1)], 2: [listed_invoice(2)]}
    handler = inventory_handler(pages, 2, overrides={2: {"total_items": 3}})
    with pytest.raises(InvoiceInventoryIncomplete, match="totals changed"):
        make(token_then(handler)).list_invoices()


def test_duplicate_invoice_id_between_pages_fails_closed() -> None:
    pages = {1: [listed_invoice(1)], 2: [listed_invoice(1)]}
    with pytest.raises(InvoiceInventoryIncomplete, match="repeated"):
        make(token_then(inventory_handler(pages, 2))).list_invoices()


@pytest.mark.parametrize("bad_row", [None, {"id": ""}, {"id": 23}])
def test_invalid_invoice_record_fails_closed(bad_row: object) -> None:
    handler = inventory_handler({1: [bad_row]}, 1)
    with pytest.raises(InvoiceInventoryIncomplete):
        make(token_then(handler)).list_invoices()


@pytest.mark.parametrize("failure", [429, 503])
def test_failed_second_page_never_returns_partial_financial_inventory(failure: int) -> None:
    seen: list[int] = []

    def handler(request: httpx.Request) -> httpx.Response:
        page = int(request.url.params["page"])
        seen.append(page)
        if page == 2:
            return httpx.Response(failure, json={"message": "not available"})
        return httpx.Response(
            200, json={"items": [listed_invoice(1)], "total_pages": 2, "total_items": 2}
        )

    error = PayPalError if failure == 429 else PayPalUncertain
    with pytest.raises(error):
        make(token_then(handler)).list_invoices()
    assert seen == [1, 2]


def test_network_timeout_on_second_page_never_returns_partial_inventory() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.params["page"] == "2":
            raise httpx.ReadTimeout("timed out")
        return httpx.Response(
            200, json={"items": [listed_invoice(1)], "total_pages": 2, "total_items": 2}
        )

    with pytest.raises(PayPalUncertain):
        make(token_then(handler)).list_invoices()
