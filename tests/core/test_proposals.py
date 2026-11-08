import threading
from copy import deepcopy
from datetime import timedelta

import pytest

from paypal_invoice_steward.core.models import Invoice, invoice_content_digest
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


def test_sandbox_reminder_discloses_provider_delivery_before_approval(
    service: ProposalService,
    port: FakePayPal,
) -> None:
    port.mode = "sandbox"
    p = service.propose_reminder("INV1")
    assert "PayPal generates" in p["payload"]["note"]
    assert "does not stop external reminders" in p["payload"]["delivery_notice"]
    assert p["payload_hash"] == payload_hash("reminder", p["payload"])
    with pytest.raises(PolicyError, match="custom notes"):
        service.propose_reminder("INV2", "Custom text")
    assert port.sent_log == []
    service.policy = Policy(sandbox_writes_enabled=True)
    assert service.confirm(p["id"], p["payload_hash"])["status"] == "done"
    assert port.sent_log == [("reminder", "INV1")]


def test_legacy_sandbox_reminder_requires_fresh_delivery_review(
    service: ProposalService,
    port: FakePayPal,
) -> None:
    p = service.propose_reminder("INV1")
    port.mode = "sandbox"
    service.policy = Policy(sandbox_writes_enabled=True)
    result = service.confirm(p["id"], p["payload_hash"])
    assert result["status"] == "failed"
    assert "new proposal" in result["error"]
    assert port.sent_log == []


@pytest.mark.parametrize("raw", ["SCHEDULED", "PAYMENT_PENDING"])
def test_scheduled_or_pending_payment_never_gets_reminder(
    service: ProposalService,
    port: FakePayPal,
    raw: str,
) -> None:
    p = service.propose_reminder("INV1")
    port.invoices["INV1"].provider_status = raw
    with pytest.raises(PolicyError):
        service.propose_reminder("INV1")
    assert service.confirm(p["id"], p["payload_hash"])["status"] == "failed"
    assert port.sent_log == []


@pytest.mark.parametrize(
    "status,raw",
    [
        ("open", "SENT"),
        ("open", "UNPAID"),
        ("open", "PARTIALLY_PAID"),
        ("paid", "PAID"),
        ("paid", "MARKED_AS_PAID"),
    ],
)
def test_matching_provider_invoice_is_recovered_without_resending(
    service: ProposalService,
    port: FakePayPal,
    status: str,
    raw: str,
) -> None:
    p = service.propose_invoice(INVOICE)
    invoice = port.create_invoice_draft(p["payload"], p["reference"])
    invoice.status, invoice.provider_status = status, raw
    invoice.balance_source = "paypal_due_amount"
    assert service.confirm(p["id"], p["payload_hash"])["status"] == "done"
    assert port.sent_log == []


@pytest.mark.parametrize(
    "field,value",
    [
        ("customer_email", "wrong@example.com"),
        ("customer_name", "Other customer"),
        ("currency", "USD"),
        ("amount", 1.0),
        ("amount", float("nan")),
        ("number", "OTHER"),
        ("due", TODAY + timedelta(days=99)),
    ],
)
def test_changed_invoice_readback_never_sends_or_verifies(
    service: ProposalService,
    port: FakePayPal,
    monkeypatch: pytest.MonkeyPatch,
    field: str,
    value: object,
) -> None:
    p = service.propose_invoice(INVOICE)
    invoice = port.create_invoice_draft(p["payload"], p["reference"])
    setattr(invoice, field, value)
    monkeypatch.setattr(port, "find_by_reference", lambda _: invoice)
    assert service.confirm(p["id"], p["payload_hash"])["status"] == "unverified"
    assert port.sent_log == []
    invoice.status = "open"
    with pytest.raises(Conflict):
        service.verify(p["id"])
    assert service.get(p["id"])["status"] == "unverified"
    assert port.sent_log == []


@pytest.mark.parametrize(
    "changed",
    [
        {
            "note": "Substituted note",
            "items": [{"description": "Logo refresh", "quantity": 1, "unit_price": 450}],
        },
        {
            "note": "",
            "items": [{"description": "Replacement work", "quantity": 1, "unit_price": 450}],
        },
        {
            "note": "",
            "items": [{"description": "Logo refresh", "quantity": 2, "unit_price": 225}],
        },
        {
            "note": "",
            "items": [
                {"description": "First", "quantity": 1, "unit_price": 200},
                {"description": "Second", "quantity": 1, "unit_price": 250},
            ],
        },
    ],
)
def test_changed_provider_content_with_same_total_never_sends_or_verifies(
    service: ProposalService, port: FakePayPal, changed: dict[str, object]
) -> None:
    p = service.propose_invoice(INVOICE)
    invoice = port.create_invoice_draft(p["payload"], p["reference"])
    invoice.content_digest = invoice_content_digest(changed)
    assert service.confirm(p["id"], p["payload_hash"])["status"] == "unverified"
    assert not port.sent_log
    invoice.status = "open"
    with pytest.raises(Conflict):
        service.verify(p["id"])
    assert service.get(p["id"])["status"] == "unverified"


def test_missing_provider_content_never_sends_or_verifies(
    service: ProposalService, port: FakePayPal
) -> None:
    p = service.propose_invoice(INVOICE)
    invoice = port.create_invoice_draft(p["payload"], p["reference"])
    invoice.content_digest = None
    assert service.confirm(p["id"], p["payload_hash"])["status"] == "unverified"
    assert not port.sent_log


def test_reordered_provider_lines_never_send() -> None:
    spec = {
        **INVOICE,
        "items": [
            {"description": "First", "quantity": 1, "unit_price": 200},
            {"description": "Second", "quantity": 1, "unit_price": 250},
        ],
    }
    port = FakePayPal()
    service = ProposalService(port, SqliteProposalStore(":memory:"), today=lambda: TODAY)
    p = service.propose_invoice(spec)
    invoice = port.create_invoice_draft(p["payload"], p["reference"])
    invoice.content_digest = invoice_content_digest(
        {"note": "", "items": list(reversed(spec["items"]))}
    )
    assert service.confirm(p["id"], p["payload_hash"])["status"] == "unverified"
    assert not port.sent_log


@pytest.mark.parametrize(
    "status,raw",
    [
        ("draft", "DRAFT"),
        ("cancelled", "CANCELLED"),
        ("refund_review", "REFUNDED"),
        ("unknown", "NEW_STATE"),
        ("open", "SCHEDULED"),
        ("open", "PAYMENT_PENDING"),
    ],
)
def test_unconfirmed_readback_is_never_reported_as_sent(
    service: ProposalService,
    port: FakePayPal,
    monkeypatch: pytest.MonkeyPatch,
    status: str,
    raw: str,
) -> None:
    p = service.propose_invoice(INVOICE)
    original = port.send_invoice

    def send(invoice_id: str) -> Invoice:
        invoice = original(invoice_id)
        invoice.status, invoice.provider_status = status, raw
        return invoice

    monkeypatch.setattr(port, "send_invoice", send)
    assert service.confirm(p["id"], p["payload_hash"])["status"] == "unverified"
    assert service.verify(p["id"])["status"] == "unverified"
    assert len(port.sent_log) == 1


def test_wrong_invoice_after_send_is_uncertain(
    service: ProposalService,
    port: FakePayPal,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    p = service.propose_invoice(INVOICE)
    original = port.send_invoice

    def send(invoice_id: str) -> Invoice:
        invoice = deepcopy(original(invoice_id))
        invoice.id = "ANOTHER"
        return invoice

    monkeypatch.setattr(port, "send_invoice", send)
    assert service.confirm(p["id"], p["payload_hash"])["status"] == "unverified"
    assert len(port.sent_log) == 1


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


@pytest.mark.parametrize("status", ["executing", "unverified"])
def test_same_request_reuses_active_invoice_proposal(service: ProposalService, status: str) -> None:
    original = service.propose_invoice(INVOICE)
    assert service.store.transition(original["id"], ["pending"], status)

    repeated = service.propose_invoice(dict(INVOICE))

    assert repeated["id"] == original["id"]
    assert repeated["reference"] == original["reference"]
    assert repeated["status"] == status


@pytest.mark.parametrize("status", ["done", "failed", "dismissed"])
def test_same_request_after_terminal_invoice_proposal_creates_a_new_one(
    service: ProposalService, status: str
) -> None:
    original = service.propose_invoice(INVOICE)
    assert service.store.transition(original["id"], ["pending"], status)

    repeated = service.propose_invoice(dict(INVOICE))

    assert repeated["id"] != original["id"]
    assert repeated["reference"] != original["reference"]
    assert repeated["status"] == "pending"


def test_concurrent_equivalent_invoice_requests_reuse_one_active_proposal(tmp_path) -> None:
    path = str(tmp_path / "proposals.db")
    start = threading.Barrier(2)
    services = [
        ProposalService(FakePayPal(), SqliteProposalStore(path), today=lambda: TODAY)
        for _ in range(2)
    ]
    results: list[dict[str, object]] = []
    failures: list[BaseException] = []

    def propose(service: ProposalService) -> None:
        try:
            start.wait(timeout=5)
            results.append(service.propose_invoice(deepcopy(INVOICE)))
        except Exception as exc:
            failures.append(exc)

    threads = [threading.Thread(target=propose, args=(service,)) for service in services]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join(timeout=5)

    assert not failures
    assert len(results) == 2
    assert {result["id"] for result in results} == {results[0]["id"]}
    proposal_id = str(results[0]["id"])
    events = services[0].store.events(proposal_id)
    assert [event["event"] for event in events] == ["proposed"]
    assert len(services[0].list()) == 1


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


def test_interrupted_invoice_is_recovered_by_read_only_lookup_without_resend(
    service: ProposalService, port: FakePayPal
) -> None:
    proposal = service.propose_invoice(INVOICE)
    invoice = port.create_invoice_draft(proposal["payload"], proposal["reference"])
    port.send_invoice(invoice.id)
    assert service.store.transition(proposal["id"], ["pending"], "executing")

    recovered = service.verify(proposal["id"])

    assert recovered["status"] == "done"
    assert port.sent_log == [("invoice", invoice.id)]
    assert service.get(proposal["id"])["events"][-1]["event"] == "recovered"


@pytest.mark.parametrize("provider_state", ["missing", "draft", "mismatched"])
def test_interrupted_invoice_without_exact_sent_readback_stays_executing(
    service: ProposalService, port: FakePayPal, provider_state: str
) -> None:
    proposal = service.propose_invoice(INVOICE)
    assert service.store.transition(proposal["id"], ["pending"], "executing")
    if provider_state == "draft":
        port.create_invoice_draft(proposal["payload"], proposal["reference"])
    elif provider_state == "mismatched":
        invoice = port.create_invoice_draft(proposal["payload"], proposal["reference"])
        invoice.customer_email = "other@example.com"

    if provider_state == "mismatched":
        with pytest.raises(Conflict, match="Could not check PayPal"):
            service.verify(proposal["id"])
    else:
        assert service.verify(proposal["id"])["status"] == "executing"
    assert service.get(proposal["id"])["status"] == "executing"
    with pytest.raises(Conflict, match="already being executed"):
        service.confirm(proposal["id"], proposal["payload_hash"])
    assert port.sent_log == []


def test_interrupted_reminder_cannot_be_verified_or_retried(
    service: ProposalService, port: FakePayPal
) -> None:
    proposal = service.propose_reminder(LATE)
    assert service.store.transition(proposal["id"], ["pending"], "executing")

    with pytest.raises(Conflict, match="Reminders cannot be verified"):
        service.verify(proposal["id"])
    with pytest.raises(Conflict, match="already being executed"):
        service.confirm(proposal["id"], proposal["payload_hash"])
    assert port.sent_log == []


def test_interrupted_invoice_provider_outage_stays_executing(
    service: ProposalService, port: FakePayPal, monkeypatch: pytest.MonkeyPatch
) -> None:
    proposal = service.propose_invoice(INVOICE)
    assert service.store.transition(proposal["id"], ["pending"], "executing")

    def unavailable(_: str) -> Invoice | None:
        raise PayPalUncertain("UNTRUSTED_PROVIDER_TEXT")

    monkeypatch.setattr(port, "find_by_reference", unavailable)
    with pytest.raises(Conflict, match="Could not check PayPal"):
        service.verify(proposal["id"])
    assert service.get(proposal["id"])["status"] == "executing"
    assert port.sent_log == []


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


def test_concurrent_verify_cannot_append_a_stale_observation_after_confirm(
    service: ProposalService, port: FakePayPal, monkeypatch: pytest.MonkeyPatch
) -> None:
    proposal = service.propose_invoice(INVOICE)
    create_started = threading.Event()
    allow_create = threading.Event()
    verify_lookup_started = threading.Event()
    allow_verify_lookup = threading.Event()
    original_create = port.create_invoice_draft
    original_find = port.find_by_reference

    def create_after_verify_starts(spec: dict[str, object], reference: str) -> Invoice:
        create_started.set()
        assert allow_create.wait(timeout=2)
        return original_create(spec, reference)

    def find_for_current_operation(reference: str) -> Invoice | None:
        if threading.current_thread().name == "verify":
            verify_lookup_started.set()
            assert allow_verify_lookup.wait(timeout=2)
            return None
        return original_find(reference)

    monkeypatch.setattr(port, "create_invoice_draft", create_after_verify_starts)
    monkeypatch.setattr(port, "find_by_reference", find_for_current_operation)
    results: dict[str, dict[str, object]] = {}
    errors: list[Exception] = []

    def confirm() -> None:
        try:
            results["confirm"] = service.confirm(proposal["id"], proposal["payload_hash"])
        except Exception as exc:  # test thread reports failures below
            errors.append(exc)

    def verify() -> None:
        try:
            results["verify"] = service.verify(proposal["id"])
        except Exception as exc:  # test thread reports failures below
            errors.append(exc)

    confirmer = threading.Thread(target=confirm, name="confirm")
    confirmer.start()
    assert create_started.wait(timeout=2)

    verifier = threading.Thread(target=verify, name="verify")
    verifier.start()
    assert verify_lookup_started.wait(timeout=2)

    allow_create.set()
    confirmer.join(timeout=2)
    assert not confirmer.is_alive()
    allow_verify_lookup.set()
    verifier.join(timeout=2)
    assert not verifier.is_alive()

    assert errors == []
    assert results["confirm"]["status"] == results["verify"]["status"] == "done"
    assert [kind for kind, _ in port.sent_log] == ["invoice"]
    assert [event["event"] for event in service.get(proposal["id"])["events"]] == [
        "proposed",
        "confirmed",
        "done",
    ]


def test_audit_trail_records_steps(service: ProposalService) -> None:
    p = service.propose_invoice(INVOICE)
    service.confirm(p["id"], p["payload_hash"])
    events = [e["event"] for e in service.get(p["id"])["events"]]
    assert events[0] == "proposed" and "confirmed" in events and events[-1] == "done"


def test_confirm_persists_attribution_before_provider_write(
    service: ProposalService, port: FakePayPal, monkeypatch: pytest.MonkeyPatch
) -> None:
    service.policy = Policy(operator_id="demo-approver")
    proposal = service.propose_invoice(INVOICE)
    original = port.create_invoice_draft

    def create_after_audit(spec: dict[str, object], reference: str) -> Invoice:
        stored = service.get(proposal["id"])
        assert stored["status"] == "executing"
        assert stored["events"][-1]["event"] == "confirmed"
        assert stored["events"][-1]["detail"] == "from pending; operator=demo-approver"
        return original(spec, reference)

    monkeypatch.setattr(port, "create_invoice_draft", create_after_audit)

    assert service.confirm(proposal["id"], proposal["payload_hash"])["status"] == "done"


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
    ("reason_code", "expected_detail"),
    [
        ("provider_readback_missing", "reason=provider_readback_missing"),
        ("UNTRUSTED_PROVIDER_REASON", "reason=provider_outcome_unknown"),
    ],
)
def test_unverified_event_records_only_allowlisted_reason_code(
    service: ProposalService,
    port: FakePayPal,
    monkeypatch: pytest.MonkeyPatch,
    reason_code: str,
    expected_detail: str,
) -> None:
    def broken_create(*args: object) -> Invoice:
        raise PayPalUncertain("LEAK_TEST_SECRET", reason_code=reason_code)

    monkeypatch.setattr(port, "create_invoice_draft", broken_create)
    proposal = service.propose_invoice(INVOICE)
    result = service.confirm(proposal["id"], proposal["payload_hash"])

    assert result["status"] == "unverified"
    event = service.get(proposal["id"])["events"][-1]
    assert event["event"] == "unverified"
    assert event["detail"] == expected_detail
    assert "LEAK_TEST_SECRET" not in str(event)
    assert "UNTRUSTED_PROVIDER_REASON" not in str(event)


def test_unexpected_unverified_event_uses_generic_local_reason(
    service: ProposalService, port: FakePayPal, monkeypatch: pytest.MonkeyPatch
) -> None:
    def broken_create(*args: object) -> Invoice:
        raise ValueError("LEAK_TEST_SECRET")

    monkeypatch.setattr(port, "create_invoice_draft", broken_create)
    proposal = service.propose_invoice(INVOICE)
    result = service.confirm(proposal["id"], proposal["payload_hash"])

    assert result["status"] == "unverified"
    event = service.get(proposal["id"])["events"][-1]
    assert event["event"] == "unverified"
    assert event["detail"] == "reason=local_unexpected_error"
    assert "LEAK_TEST_SECRET" not in str(event)


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
