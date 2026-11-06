import threading
from copy import deepcopy

import pytest

from paypal_invoice_steward.core.models import Invoice
from paypal_invoice_steward.core.ports import PayPalError, PayPalUncertain
from paypal_invoice_steward.core.proposals import (
    Conflict,
    HashMismatch,
    NotFound,
    Policy,
    PolicyError,
    ProposalService,
    SandboxWritesDisabled,
    payload_hash,
)
from paypal_invoice_steward.persistence.store import SqliteProposalStore

from .conftest import INVOICE, TODAY, FakePayPal

LATE = "INV1"


@pytest.mark.parametrize("field", ["quantity", "unit_price"])
@pytest.mark.parametrize("value", [float("nan"), float("inf"), float("-inf"), "NaN", "Infinity"])
def test_nonfinite_invoice_values_never_create_proposals(
    service: ProposalService, port: FakePayPal, field: str, value: object
) -> None:
    spec = deepcopy(INVOICE)
    spec["items"][0][field] = value
    with pytest.raises(PolicyError):
        service.propose_invoice(spec)
    assert service.list() == []
    assert port.sent_log == []


@pytest.mark.parametrize("field", ["note", "customer_email", "items"])
def test_stored_payload_mutation_cannot_reuse_reviewed_hash(
    service: ProposalService, port: FakePayPal, monkeypatch: pytest.MonkeyPatch, field: str
) -> None:
    proposal = service.propose_invoice(INVOICE)
    original = service.store.get

    def changed(proposal_id: str) -> dict[str, object]:
        record = original(proposal_id)
        assert record is not None
        record["payload"][field] = {
            "note": "changed",
            "customer_email": "other@example.com",
            "items": [{"description": "Different", "quantity": 1, "unit_price": 99}],
        }[field]
        return record

    monkeypatch.setattr(service.store, "get", changed)
    before = len(port.invoices)
    with pytest.raises(HashMismatch, match="stored proposal changed"):
        service.confirm(proposal["id"], proposal["payload_hash"])
    assert len(port.invoices) == before
    assert port.sent_log == []
    assert service.get(proposal["id"])["events"][-1]["event"] == "refused"


@pytest.mark.parametrize(
    "kind,price", [("invoice", float("nan")), ("invoice", 10001), ("refund", 10)]
)
def test_invalid_legacy_proposal_is_blocked_even_with_matching_hash(
    service: ProposalService,
    port: FakePayPal,
    monkeypatch: pytest.MonkeyPatch,
    kind: str,
    price: float,
) -> None:
    proposal = service.propose_invoice(INVOICE)
    record = service.store.get(proposal["id"])
    assert record is not None
    record["kind"] = kind
    record["payload"]["items"][0]["unit_price"] = price
    record["payload_hash"] = payload_hash(kind, record["payload"])
    monkeypatch.setattr(service.store, "get", lambda _: deepcopy(record))
    before = len(port.invoices)
    with pytest.raises(PolicyError):
        service.confirm(proposal["id"], record["payload_hash"])
    assert len(port.invoices) == before
    assert port.sent_log == []


def test_proposing_sends_nothing(service: ProposalService, port: FakePayPal) -> None:
    service.propose_invoice(INVOICE)
    assert port.sent_log == []


def test_confirm_sends_exactly_once_even_if_repeated(
    service: ProposalService, port: FakePayPal
) -> None:
    p = service.propose_invoice(INVOICE)
    first = service.confirm(p["id"], p["payload_hash"])
    second = service.confirm(p["id"], p["payload_hash"])
    assert first["status"] == second["status"] == "done"
    assert [k for k, _ in port.sent_log].count("invoice") == 1


def test_hash_mismatch_is_refused(service: ProposalService, port: FakePayPal) -> None:
    p = service.propose_invoice(INVOICE)
    with pytest.raises(HashMismatch):
        service.confirm(p["id"], "0" * 16)
    assert port.sent_log == []
    assert service.get(p["id"])["status"] == "pending"


def test_same_request_reuses_pending_proposal(service: ProposalService) -> None:
    a = service.propose_invoice(INVOICE)
    b = service.propose_invoice(dict(INVOICE))
    assert a["id"] == b["id"]


@pytest.mark.parametrize(
    "change",
    [
        {"customer_email": "not-an-email"},
        {"currency": "JPY"},
        {"due_days": 0},
        {"due_days": 91},
        {"items": []},
        {"items": [{"description": "x", "quantity": 1, "unit_price": -5}]},
        {"items": [{"description": "x", "quantity": 1, "unit_price": 10_001}]},
        {"customer_name": ""},
    ],
)
def test_policy_rejects_bad_invoices(service: ProposalService, change: dict[str, object]) -> None:
    with pytest.raises(PolicyError):
        service.propose_invoice({**INVOICE, **change})


def test_timeout_after_send_is_unverified_then_verified_without_duplicate(
    service: ProposalService, port: FakePayPal
) -> None:
    p = service.propose_invoice(INVOICE)
    port.fail_next = "timeout_after_send"
    result = service.confirm(p["id"], p["payload_hash"])
    assert result["status"] == "unverified"
    assert result["status"] != "failed"
    verified = service.verify(p["id"])
    assert verified["status"] == "done"
    assert [k for k, _ in port.sent_log].count("invoice") == 1


def test_retry_after_unverified_does_not_duplicate(
    service: ProposalService, port: FakePayPal
) -> None:
    p = service.propose_invoice(INVOICE)
    port.fail_next = "timeout_after_send"
    service.confirm(p["id"], p["payload_hash"])
    again = service.confirm(p["id"], p["payload_hash"])
    assert again["status"] == "done"
    assert [k for k, _ in port.sent_log].count("invoice") == 1
    created = [i for i in port.list_invoices() if i.number == p["reference"]]
    assert len(created) == 1


def test_definitive_rejection_is_failed_and_final(
    service: ProposalService, port: FakePayPal
) -> None:
    p = service.propose_invoice(INVOICE)
    port.fail_next = "reject"
    result = service.confirm(p["id"], p["payload_hash"])
    assert result["status"] == "failed"
    assert result["error"]
    with pytest.raises(Conflict):
        service.confirm(p["id"], p["payload_hash"])


def test_reminder_flow_and_cooldown(service: ProposalService, port: FakePayPal) -> None:
    p = service.propose_reminder(LATE)
    done = service.confirm(p["id"], p["payload_hash"])
    assert done["status"] == "done"
    assert ("reminder", LATE) in port.sent_log
    with pytest.raises(PolicyError, match="wait"):
        service.propose_reminder(LATE)


def test_identical_pending_reminder_is_reused(service: ProposalService) -> None:
    a = service.propose_reminder(LATE)
    b = service.propose_reminder(LATE)
    assert a["id"] == b["id"]


def test_reminder_unknown_outcome_is_not_auto_retried(
    service: ProposalService, port: FakePayPal
) -> None:
    p = service.propose_reminder(LATE)
    port.fail_next = "timeout_after_send"
    assert service.confirm(p["id"], p["payload_hash"])["status"] == "unverified"
    with pytest.raises(Conflict):
        service.confirm(p["id"], p["payload_hash"])
    with pytest.raises(PolicyError):
        service.propose_reminder(LATE)


def test_reminder_policy_rejects_paid_and_far_future(
    service: ProposalService, port: FakePayPal
) -> None:
    with pytest.raises(PolicyError, match="paid"):
        service.propose_reminder("INV4")
    with pytest.raises(PolicyError, match="not due until"):
        service.propose_reminder("INV3")
    with pytest.raises(PolicyError):
        service.propose_reminder("does-not-exist")


def test_dismiss_only_pending(service: ProposalService) -> None:
    p = service.propose_invoice(INVOICE)
    assert service.dismiss(p["id"])["status"] == "dismissed"
    with pytest.raises(Conflict):
        service.dismiss(p["id"])
    with pytest.raises(NotFound):
        service.get("nope")


def test_concurrent_confirms_execute_once(service: ProposalService, port: FakePayPal) -> None:
    p = service.propose_invoice(INVOICE)
    results: list[str] = []
    errors: list[str] = []

    def go() -> None:
        try:
            results.append(service.confirm(p["id"], p["payload_hash"])["status"])
        except Conflict as exc:
            errors.append(str(exc))

    threads = [threading.Thread(target=go) for _ in range(8)]
    [t.start() for t in threads]
    [t.join() for t in threads]
    assert [k for k, _ in port.sent_log].count("invoice") == 1
    assert service.get(p["id"])["status"] == "done"


def test_audit_trail_records_steps(service: ProposalService) -> None:
    p = service.propose_invoice(INVOICE)
    service.confirm(p["id"], p["payload_hash"])
    events = [e["event"] for e in service.get(p["id"])["events"]]
    assert events[0] == "proposed" and "confirmed" in events and events[-1] == "done"


def test_unknown_status_after_create_is_unverified_not_done(
    service: ProposalService, port: FakePayPal
) -> None:
    p = service.propose_invoice(INVOICE)
    original = port.create_invoice_draft

    def create_unknown(spec: dict[str, object], reference: str) -> object:
        invoice = original(spec, reference)
        invoice.status = "unknown"
        return invoice

    port.create_invoice_draft = create_unknown
    assert service.confirm(p["id"], p["payload_hash"])["status"] == "unverified"
    assert port.sent_log == []


def test_unknown_invoices_get_no_reminders(service: ProposalService, port: FakePayPal) -> None:
    port.invoices["INV1"].status = "unknown"
    with pytest.raises(PolicyError):
        service.propose_reminder("INV1")


def test_sandbox_invoice_confirm_is_read_only_by_default() -> None:
    port = FakePayPal()
    port.mode = "sandbox"
    service = ProposalService(port, SqliteProposalStore(":memory:"), today=lambda: TODAY)
    proposal = service.propose_invoice(INVOICE)
    before = len(port.invoices)
    for _ in range(2):
        with pytest.raises(SandboxWritesDisabled, match="read-only"):
            service.confirm(proposal["id"], proposal["payload_hash"])
    assert service.get(proposal["id"])["status"] == "pending"
    assert [e["event"] for e in service.get(proposal["id"])["events"]] == [
        "proposed",
        "refused",
        "refused",
    ]
    assert port.sent_log == []
    assert len(port.invoices) == before


def test_sandbox_reminder_confirm_is_read_only_by_default() -> None:
    port = FakePayPal()
    port.mode = "sandbox"
    service = ProposalService(port, SqliteProposalStore(":memory:"), today=lambda: TODAY)
    proposal = service.propose_reminder("INV1")
    assert service.list()[0]["status"] == "pending"
    with pytest.raises(SandboxWritesDisabled):
        service.confirm(proposal["id"], proposal["payload_hash"])
    assert service.get(proposal["id"])["status"] == "pending"
    assert port.sent_log == []


def test_explicit_sandbox_opt_in_preserves_approval_and_idempotency() -> None:
    port = FakePayPal()
    port.mode = "sandbox"
    service = ProposalService(
        port,
        SqliteProposalStore(":memory:"),
        Policy(sandbox_writes_enabled=True),
        today=lambda: TODAY,
    )
    proposal = service.propose_invoice(INVOICE)
    with pytest.raises(HashMismatch):
        service.confirm(proposal["id"], "0" * 16)
    assert port.sent_log == []
    first = service.confirm(proposal["id"], proposal["payload_hash"])
    second = service.confirm(proposal["id"], proposal["payload_hash"])
    assert first["status"] == second["status"] == "done"
    assert [kind for kind, _ in port.sent_log] == ["invoice"]


@pytest.mark.parametrize(
    ("failure", "expected_state"),
    [
        (PayPalError("LEAK_TEST_SECRET", 422), "failed"),
        (PayPalUncertain("LEAK_TEST_SECRET"), "unverified"),
    ],
)
def test_provider_error_text_never_enters_proposal_or_audit_log(
    service: ProposalService,
    port: FakePayPal,
    monkeypatch: pytest.MonkeyPatch,
    failure: Exception,
    expected_state: str,
) -> None:
    def broken_create(*args: object) -> Invoice:
        raise failure

    monkeypatch.setattr(port, "create_invoice_draft", broken_create)
    proposal = service.propose_invoice(INVOICE)
    result = service.confirm(proposal["id"], proposal["payload_hash"])
    assert result["status"] == expected_state
    assert result["error"]
    assert "LEAK_TEST_SECRET" not in result["error"]
    record = service.get(proposal["id"])
    assert "LEAK_TEST_SECRET" not in str(record["events"])
    assert expected_state in [entry["event"] for entry in record["events"]]


@pytest.mark.parametrize(
    "failure", [PayPalError("LEAK_TEST_SECRET", 403), PayPalUncertain("LEAK_TEST_SECRET")]
)
def test_verification_errors_hide_upstream_text(
    service: ProposalService,
    port: FakePayPal,
    monkeypatch: pytest.MonkeyPatch,
    failure: Exception,
) -> None:
    proposal = service.propose_invoice(INVOICE)
    assert service.store.transition(proposal["id"], ["pending"], "unverified")

    def broken_lookup(reference: str) -> Invoice | None:
        raise failure

    monkeypatch.setattr(port, "find_by_reference", broken_lookup)
    with pytest.raises(Conflict) as exc_info:
        service.verify(proposal["id"])
    assert "LEAK_TEST_SECRET" not in str(exc_info.value)


def test_reminder_mentions_verified_paypal_residual_not_invoice_face(
    service: ProposalService, port: FakePayPal
) -> None:
    inv = port.invoices["INV1"]
    inv.amount = 450.0
    inv.remaining_amount = 250.75
    inv.balance_source = "paypal_due_amount"
    reminder = service.propose_reminder("INV1")
    assert "250.75" in reminder["summary"]
    assert "450.00" not in reminder["summary"]
    assert "250.75" in reminder["payload"]["note"]
    assert port.sent_log == []


@pytest.mark.parametrize("remaining", [None, 0.0])
def test_reminder_refuses_unknown_or_zero_paypal_due_without_sending(
    service: ProposalService, port: FakePayPal, remaining: float | None
) -> None:
    inv = port.invoices["INV1"]
    inv.balance_source = "unverified" if remaining is None else "paypal_due_amount"
    inv.remaining_amount = remaining
    with pytest.raises(PolicyError, match="unverified|no confirmed balance"):
        service.propose_reminder("INV1")
    assert port.sent_log == []
    assert service.list() == []


@pytest.mark.parametrize("new_status", ["refund_review", "paid", "cancelled", "unknown"])
def test_confirm_refuses_stale_reminder_after_paypal_status_change(
    service: ProposalService, port: FakePayPal, new_status: str
) -> None:
    proposal = service.propose_reminder("INV1")
    assert proposal["status"] == "pending"
    port.invoices["INV1"].status = new_status
    result = service.confirm(proposal["id"], proposal["payload_hash"])
    assert result["status"] == "failed"
    assert "blocked" in result["error"].lower()
    assert port.sent_log == []
    assert "blocked" in [e["event"] for e in service.get(proposal["id"])["events"]]
    with pytest.raises(Conflict):
        service.confirm(proposal["id"], proposal["payload_hash"])
    assert port.sent_log == []


@pytest.mark.parametrize(
    "change",
    ["remaining", "currency", "due", "email", "invoice_number", "zero"],
)
def test_confirm_refuses_reminder_when_approved_financial_snapshot_changes(
    service: ProposalService, port: FakePayPal, change: str
) -> None:
    proposal = service.propose_reminder("INV1")
    inv = port.invoices["INV1"]
    if change == "remaining":
        inv.balance_source = "paypal_due_amount"
        inv.remaining_amount = inv.amount - 1
    elif change == "zero":
        inv.balance_source = "paypal_due_amount"
        inv.remaining_amount = 0.0
    elif change == "currency":
        inv.currency = "USD"
    elif change == "due":
        inv.due = inv.due.replace(day=inv.due.day - 1) if inv.due.day > 1 else inv.issued
    elif change == "email":
        inv.customer_email = "different@example.com"
    else:
        inv.number = "CHANGED-1"
    result = service.confirm(proposal["id"], proposal["payload_hash"])
    assert result["status"] == "failed"
    assert "blocked" in result["error"].lower()
    assert port.sent_log == []


def test_confirm_refuses_old_reminder_without_balance_snapshot(
    service: ProposalService, port: FakePayPal
) -> None:
    proposal = service.propose_reminder("INV1")
    # Simulate a pending proposal persisted before the new preflight contract.
    stored = service.store.get(proposal["id"])
    assert stored is not None
    stored["payload"].pop("expected_balance")
    from paypal_invoice_steward.core.proposals import ReminderPreflightBlocked

    with pytest.raises(ReminderPreflightBlocked, match="balance changed"):
        service._execute(stored)
    assert port.sent_log == []


def test_preflight_provider_outage_does_not_send_a_reminder(
    service: ProposalService, port: FakePayPal, monkeypatch: pytest.MonkeyPatch
) -> None:
    proposal = service.propose_reminder("INV1")

    def unavailable(invoice_id: str) -> Invoice | None:
        raise PayPalUncertain("UNTRUSTED_PROVIDER_TEXT")

    monkeypatch.setattr(port, "get_invoice", unavailable)
    result = service.confirm(proposal["id"], proposal["payload_hash"])
    assert result["status"] == "unverified"
    assert "UNTRUSTED_PROVIDER_TEXT" not in str(result)
    assert port.sent_log == []


def test_stable_invoice_reminder_is_sent_once_after_preflight(
    service: ProposalService, port: FakePayPal
) -> None:
    proposal = service.propose_reminder("INV1")
    result = service.confirm(proposal["id"], proposal["payload_hash"])
    assert result["status"] == "done"
    assert port.sent_log == [("reminder", "INV1")]
    again = service.confirm(proposal["id"], proposal["payload_hash"])
    assert again["status"] == "done"
    assert port.sent_log == [("reminder", "INV1")]
