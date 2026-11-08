import json
from collections.abc import Callable
from datetime import date

import httpx
import pytest

from paypal_invoice_steward.core.models import (
    JSON,
    BalanceUnverified,
    RefundReconciliationRequired,
    invoice_content_digest,
)
from paypal_invoice_steward.core.ports import (
    InvoiceInventoryIncomplete,
    PayPalError,
    PayPalPort,
    PayPalUncertain,
)
from paypal_invoice_steward.persistence.paypal_sandbox import (
    INVOICE_PAGE_SIZE,
    INVOICING_SCOPE,
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
        "note": "Approved note",
        "payment_term": {"due_date": "2026-10-15"},
    },
    "amount": {"currency_code": "EUR", "value": "450.00"},
    "primary_recipients": [{"billing_info": {"business_name": "Alba", "email_address": "a@b.co"}}],
    "items": [
        {
            "name": "Logo",
            "quantity": "1",
            "unit_amount": {"currency_code": "EUR", "value": "450.00"},
        }
    ],
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


def test_normalize_keeps_exact_approved_line_content_out_of_public_invoice() -> None:
    inv = normalize_invoice(RAW)
    assert inv.content_digest == invoice_content_digest(
        {
            "note": "Approved note",
            "items": [{"description": "Logo", "quantity": 1, "unit_price": 450}],
        }
    )
    assert "content_digest" not in inv.to_dict()


@pytest.mark.parametrize(
    "changed",
    [
        {"detail": {**RAW["detail"], "note": "Substituted"}},
        {
            "items": [
                {
                    "name": "Different work",
                    "quantity": "1",
                    "unit_amount": {"currency_code": "EUR", "value": "450.00"},
                }
            ]
        },
        {
            "items": [
                {
                    "name": "Logo",
                    "quantity": "2",
                    "unit_amount": {"currency_code": "EUR", "value": "225.00"},
                }
            ]
        },
        {"items": []},
        {"items": [{"name": "Logo", "quantity": "1", "unit_amount": {}}]},
    ],
)
def test_provider_content_mismatch_or_malformed_shape_has_no_approved_digest(changed: JSON) -> None:
    inv = normalize_invoice({**RAW, **changed})
    assert inv.content_digest != normalize_invoice(RAW).content_digest


@pytest.mark.parametrize("field", ["issued", "due"])
@pytest.mark.parametrize("value", [None, "", "invalid", "2026-02-30", "2026-10-01junk", "20261001"])
def test_provider_dates_are_never_invented(field: str, value: object) -> None:
    detail = {**RAW["detail"]}
    if field == "issued":
        detail["invoice_date"] = value
    else:
        detail["payment_term"] = {"due_date": value}
    with pytest.raises(PayPalUncertain, match="dates"):
        normalize_invoice({**RAW, "detail": detail})


def test_reversed_dates_are_not_used_for_aging() -> None:
    with pytest.raises(PayPalUncertain, match="dates"):
        normalize_invoice({**RAW, "detail": {**RAW["detail"], "invoice_date": "2026-10-20"}})


@pytest.mark.parametrize(
    "amount",
    [
        None,
        {},
        {"value": "20"},
        {"currency_code": "EUR"},
        *(
            {"currency_code": "EUR", "value": value}
            for value in ["NaN", "Infinity", "-1", "1.999", 10, ""]
        ),
        {"currency_code": "JPY", "value": "100"},
    ],
)
def test_missing_face_amount_never_falls_back_to_item_sum_or_usd(amount: object) -> None:
    raw = {
        **RAW,
        "amount": amount,
        "items": [{"quantity": "1", "unit_amount": {"currency_code": "USD", "value": "999"}}],
    }
    with pytest.raises(PayPalUncertain, match="amount"):
        normalize_invoice(raw)


def test_conflicting_currency_is_not_silently_resolved() -> None:
    with pytest.raises(PayPalUncertain, match="currencies"):
        normalize_invoice({**RAW, "detail": {**RAW["detail"], "currency_code": "USD"}})


def test_invalid_source_fact_blocks_inventory_and_reminder_without_writes() -> None:
    from paypal_invoice_steward.core.proposals import ProposalService
    from paypal_invoice_steward.persistence.store import SqliteProposalStore

    requests: list[str] = []
    bad = {**RAW, "detail": {**RAW["detail"], "payment_term": {}}}

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request.method)
        if request.url.path == "/v2/invoicing/invoices":
            return httpx.Response(
                200,
                json={
                    "items": [RAW, {**bad, "id": "INV2-BAD"}],
                    "total_items": 2,
                    "total_pages": 1,
                },
            )
        return httpx.Response(200, json=bad)

    port = make(token_then(handler))
    with pytest.raises(PayPalUncertain):
        port.list_invoices()
    service = ProposalService(port, SqliteProposalStore(":memory:"), today=lambda: TODAY)
    with pytest.raises(PayPalUncertain):
        service.propose_reminder("INV2-AAAA")
    assert service.list() == []
    assert requests == ["GET", "GET"]


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
    with pytest.raises(PayPalUncertain) as server_error:
        port.send_reminder("X", "hi")
    assert server_error.value.reason_code == "provider_server_error"

    def boom(request: httpx.Request) -> httpx.Response:
        raise httpx.ReadTimeout("slow")

    with pytest.raises(PayPalUncertain) as transport_error:
        make(token_then(boom)).send_reminder("X", "hi")
    assert transport_error.value.reason_code == "provider_transport_failure"


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


@pytest.mark.parametrize("operation", ["get_invoice", "send_invoice", "send_reminder"])
@pytest.mark.parametrize(
    "invoice_id",
    [
        "",
        "../invoices",
        "INV/send",
        "INV?x=1",
        "INV#fragment",
        "%2e%2e",
        "INV\\\\x",
        "INV\n",
        " INV",
        "A" * 81,
        "https://evil.example",
        "INVí",
    ],
)
def test_unsafe_invoice_ids_never_reach_network(operation: str, invoice_id: str) -> None:
    requests: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        return httpx.Response(200, json=RAW)

    port = make(handler)
    args = (invoice_id, "hello") if operation == "send_reminder" else (invoice_id,)
    with pytest.raises(ValueError, match="Invalid invoice identifier"):
        getattr(port, operation)(*args)
    assert requests == []


@pytest.mark.parametrize("body", [{}, {**RAW, "id": "OTHER"}, {**RAW, "id": None}])
def test_read_back_never_accepts_another_invoice(body: JSON) -> None:
    port = make(token_then(lambda r: httpx.Response(200, json=body)))
    with pytest.raises(PayPalUncertain, match="identity"):
        port.get_invoice("INV2-AAAA")


def test_malformed_read_back_gets_a_safe_reason_code() -> None:
    malformed = {**RAW, "detail": {**RAW["detail"], "payment_term": {}}}
    port = make(token_then(lambda r: httpx.Response(200, json=malformed)))

    with pytest.raises(PayPalUncertain) as exc_info:
        port.get_invoice("INV2-AAAA")

    assert exc_info.value.reason_code == "provider_readback_invalid"


def test_valid_invoice_id_targets_exact_resource() -> None:
    paths: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        paths.append(request.url.path)
        return httpx.Response(200, json=RAW)

    port = make(token_then(handler))
    assert port.get_invoice("INV2-AAAA").id == "INV2-AAAA"
    port.send_invoice("INV2-AAAA")
    port.send_reminder("INV2-AAAA", "hello")
    assert paths == [
        "/v2/invoicing/invoices/INV2-AAAA",
        "/v2/invoicing/invoices/INV2-AAAA/send",
        "/v2/invoicing/invoices/INV2-AAAA",
        "/v2/invoicing/invoices/INV2-AAAA/remind",
    ]


def test_notification_requests_explicitly_suppress_cc_and_ignored_text() -> None:
    bodies: list[JSON] = []

    def handler(request: httpx.Request) -> httpx.Response:
        if request.method == "POST":
            bodies.append(json.loads(request.content))
        return httpx.Response(200, json=RAW)

    port = make(token_then(handler))
    port.send_invoice("INV2-AAAA")
    port.send_reminder("INV2-AAAA", "Text PayPal would ignore")
    assert (
        bodies
        == [{"send_to_recipient": True, "send_to_invoicer": False, "additional_recipients": []}] * 2
    )


def test_find_by_reference_matches_exact_number() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        if request.method == "POST":
            assert request.url.params["total_required"] == "true"
            return httpx.Response(200, json={"items": [RAW], "total_items": 1, "total_pages": 1})
        return httpx.Response(200, json=RAW)

    port = make(token_then(handler))
    assert port.find_by_reference("STW-1").id == "INV2-AAAA"
    assert port.find_by_reference("STW-2") is None


@pytest.mark.parametrize(
    "body",
    [
        None,
        {},
        {"items": []},
        {"items": None, "total_items": 0, "total_pages": 0},
        {"items": [], "total_items": True, "total_pages": 1},
        {"items": [], "total_items": 1, "total_pages": 1},
        {"items": [RAW], "total_items": 1, "total_pages": 2},
        {"items": [RAW, RAW], "total_items": 2, "total_pages": 1},
        {"items": [RAW, {**RAW, "id": "INV2-OTHER"}], "total_items": 2, "total_pages": 1},
        *(
            {"items": [row], "total_items": 1, "total_pages": 1}
            for row in [None, {}, {**RAW, "id": "../other"}, {**RAW, "detail": {}}]
        ),
    ],
)
def test_uncertain_search_cannot_be_used_as_permission_to_create(body: object) -> None:
    from paypal_invoice_steward.core.proposals import Policy, ProposalService
    from paypal_invoice_steward.persistence.store import SqliteProposalStore

    paths: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        paths.append(request.url.path)
        response = json.loads(json.dumps(body))
        if isinstance(response, dict) and isinstance(response.get("items"), list):
            for row in response["items"]:
                if isinstance(row, dict) and row.get("detail", {}).get("invoice_number") == "STW-1":
                    row["detail"]["invoice_number"] = json.loads(request.content)["invoice_number"]
        return httpx.Response(200, json=response)

    service = ProposalService(
        make(token_then(handler)),
        SqliteProposalStore(":memory:"),
        Policy(sandbox_writes_enabled=True),
        today=lambda: TODAY,
    )
    p = service.propose_invoice(
        {
            "customer_name": "Synthetic",
            "customer_email": "a@example.com",
            "items": [{"description": "Work", "unit_price": 10}],
        }
    )
    for _ in range(2):
        assert service.confirm(p["id"], p["payload_hash"])["status"] == "unverified"
    assert paths == ["/v2/invoicing/search-invoices"] * 2


@pytest.mark.parametrize("pages", [0, 1])
def test_verified_empty_search_is_absence(pages: int) -> None:
    port = make(
        token_then(
            lambda r: httpx.Response(
                200, json={"items": [], "total_items": 0, "total_pages": pages}
            )
        )
    )
    assert port.find_by_reference("STW-1") is None


@pytest.mark.parametrize("changed", [True, False])
def test_reference_search_reads_current_details_and_rejects_drift(changed: bool) -> None:
    paths: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        paths.append(request.url.path)
        if request.method == "POST":
            return httpx.Response(200, json={"items": [RAW], "total_items": 1, "total_pages": 1})
        detail = {**RAW["detail"], "invoice_number": "CHANGED"} if changed else RAW["detail"]
        return httpx.Response(200, json={**RAW, "status": "PAID", "detail": detail})

    port = make(token_then(handler))
    if changed:
        with pytest.raises(PayPalUncertain, match="reference"):
            port.find_by_reference("STW-1")
    else:
        assert port.find_by_reference("STW-1").status == "paid"
    assert paths == ["/v2/invoicing/search-invoices", "/v2/invoicing/invoices/INV2-AAAA"]


def test_expired_token_is_refreshed_once() -> None:
    calls = {"n": 0}

    def handler(request: httpx.Request) -> httpx.Response:
        calls["n"] += 1
        if calls["n"] == 1:
            return httpx.Response(401)
        return httpx.Response(200, json={"items": [], "total_pages": 0, "total_items": 0})

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
        ("REFUNDED", "refund_review"),
        ("PARTIALLY_REFUNDED", "refund_review"),
        ("MARKED_AS_REFUNDED", "refund_review"),
        ("REFUNDED_EXTERNAL", "refund_review"),
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


@pytest.mark.parametrize(
    "provider_status",
    ["REFUNDED", "PARTIALLY_REFUNDED", "MARKED_AS_REFUNDED", "REFUNDED_EXTERNAL"],
)
def test_refunds_do_not_become_cancelled_even_with_due_amount(
    provider_status: str,
) -> None:
    inv = normalize_invoice(
        {
            **RAW,
            "status": provider_status,
            "due_amount": {"currency_code": "EUR", "value": "75.00"},
        }
    )
    assert inv.status == "refund_review"
    assert inv.provider_status == provider_status
    assert inv.amount == 450.0
    assert inv.remaining_amount == 75.0
    assert inv.balance_source == "unverified"
    assert inv.paid is None
    with pytest.raises(RefundReconciliationRequired):
        inv.receivable_amount()


def test_cancelled_and_auto_cancelled_are_not_reclassified_as_refunds() -> None:
    assert normalize_invoice({**RAW, "status": "CANCELLED"}).status == "cancelled"
    assert normalize_invoice({**RAW, "status": "AUTO_CANCELLED"}).status == "cancelled"


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


def test_empty_inventory_may_omit_items_as_observed_in_sandbox() -> None:
    def handler(_: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"total_items": 0, "total_pages": 0})

    assert make(token_then(handler)).list_invoices() == []


def test_missing_items_with_nonempty_totals_fails_closed() -> None:
    def handler(_: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"total_items": 1, "total_pages": 1})

    with pytest.raises(InvoiceInventoryIncomplete, match="pagination metadata"):
        make(token_then(handler)).list_invoices()


def test_full_20_page_limit_is_returned_without_truncation() -> None:
    seen: list[int] = []
    pages = {
        page: [listed_invoice((page - 1) * INVOICE_PAGE_SIZE + i) for i in range(INVOICE_PAGE_SIZE)]
        for page in range(1, MAX_INVOICE_PAGES + 1)
    }
    data = make(
        token_then(inventory_handler(pages, MAX_INVOICE_PAGES * INVOICE_PAGE_SIZE, seen_pages=seen))
    ).list_invoices()
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


def test_partial_external_payment_keeps_face_separate_from_paypal_due_amount() -> None:
    raw = {
        **RAW,
        "status": "PARTIALLY_PAID",
        "due_amount": {"currency_code": "EUR", "value": "250.75"},
        "payments": {
            "paid_amount": {"currency_code": "EUR", "value": "199.25"},
            "transactions": [
                {
                    "type": "EXTERNAL",
                    "payment_date": "2026-10-17",
                    "amount": {"currency_code": "EUR", "value": "199.25"},
                }
            ],
        },
    }
    inv = normalize_invoice(raw)
    assert inv.amount == 450.0
    assert inv.remaining_amount == 250.75
    assert inv.balance_source == "paypal_due_amount"
    assert inv.receivable_amount() == 250.75
    assert inv.payment_origin == "external"
    assert inv.status == "open"
    assert inv.paid is None
    assert inv.provider_status == "PARTIALLY_PAID"


def test_reported_due_amount_is_not_recomputed_or_double_allocated() -> None:
    transaction = {
        "type": "PAYPAL",
        "payment_id": "PAY-123",
        "payment_date": "2026-10-18",
        "amount": {"currency_code": "EUR", "value": "100.00"},
    }
    inv = normalize_invoice(
        {
            **RAW,
            "status": "PARTIALLY_PAID",
            "due_amount": {"currency_code": "EUR", "value": "350.00"},
            "payments": {"transactions": [transaction, dict(transaction)]},
        }
    )
    assert inv.amount == 450
    assert inv.remaining_amount == 350
    assert inv.payment_origin == "ambiguous"
    assert inv.paid is None
    assert inv.receivable_amount() == 350


def test_paid_without_transaction_date_never_invents_due_date_as_payment_date() -> None:
    inv = normalize_invoice({**RAW, "status": "PAID"})
    assert inv.paid is None
    assert inv.payment_origin == "paypal"
    assert inv.due == date(2026, 10, 15)


@pytest.mark.parametrize(
    ("status", "payment_type", "expected_origin"),
    [("PAID", "PAYPAL", "paypal"), ("MARKED_AS_PAID", "EXTERNAL", "external")],
)
def test_paid_date_comes_only_from_documented_transaction(
    status: str, payment_type: str, expected_origin: str
) -> None:
    transaction: JSON = {
        "type": payment_type,
        "payment_date": "2026-11-02",
        "amount": {"currency_code": "EUR", "value": "450.00"},
    }
    if payment_type == "PAYPAL":
        transaction["payment_id"] = "PAY-123"
    inv = normalize_invoice({**RAW, "status": status, "payments": {"transactions": [transaction]}})
    assert inv.paid == date(2026, 11, 2)
    assert inv.paid != inv.due
    assert inv.payment_origin == expected_origin


def test_paid_with_partial_or_contradictory_transaction_evidence_has_unknown_date() -> None:
    paid = normalize_invoice(
        {
            **RAW,
            "status": "PAID",
            "payments": {
                "transactions": [
                    {"type": "PAYPAL", "payment_id": "PAY-ONE", "payment_date": "2026-10-20"},
                    {"type": "PAYPAL", "payment_id": "PAY-TWO"},
                ],
            },
        }
    )
    assert paid.paid is None
    contradictory = normalize_invoice(
        {
            **RAW,
            "status": "PAID",
            "payments": {"transactions": [{"type": "EXTERNAL", "payment_date": "2026-10-20"}]},
        }
    )
    assert contradictory.payment_origin == "ambiguous"
    assert contradictory.paid is None


@pytest.mark.parametrize(
    "bad_due",
    [
        None,
        {"currency_code": "USD", "value": "300.00"},
        {"currency_code": "EUR", "value": "-1.00"},
        {"currency_code": "EUR", "value": "NaN"},
        {"currency_code": "EUR", "value": "100.005"},
        {"currency_code": "EUR", "value": 100},
        {"currency_code": "EUR"},
    ],
)
def test_missing_or_malformed_paypal_balance_never_falls_back_to_face(
    bad_due: object,
) -> None:
    inv = normalize_invoice({**RAW, "due_amount": bad_due})
    assert inv.amount == 450
    assert inv.remaining_amount is None
    assert inv.balance_source == "unverified"
    with pytest.raises(BalanceUnverified):
        inv.receivable_amount()
