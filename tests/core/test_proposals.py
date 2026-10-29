import threading

import pytest

from paypal_invoice_steward.core.proposals import (
    Conflict,
    HashMismatch,
    NotFound,
    PolicyError,
    ProposalService,
)

from .conftest import INVOICE, FakePayPal

LATE = "INV1"


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
