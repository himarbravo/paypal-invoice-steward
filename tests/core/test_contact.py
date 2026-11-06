from pathlib import Path

import pytest

from paypal_invoice_steward.core.contact import ContactService
from paypal_invoice_steward.core.models import Invoice
from paypal_invoice_steward.core.proposals import Conflict, PolicyError, ProposalService
from paypal_invoice_steward.persistence.store import SqliteProposalStore

from .conftest import TODAY, FakePayPal


def test_hold_blocks_new_and_queued_reminders(service: ProposalService, port: FakePayPal) -> None:
    pending = service.propose_reminder("INV1")
    ContactService(service.store).change("INV1", "dispute")
    with pytest.raises(PolicyError, match="hold"):
        service.propose_reminder("INV1")
    with pytest.raises(Conflict, match="hold"):
        service.confirm(pending["id"], pending["payload_hash"])
    assert not port.sent_log
    assert service.get(pending["id"])["status"] == "pending"
    assert service.store.events(pending["id"])[-1]["event"] == "refused"
    other = service.propose_reminder("INV2")
    assert service.confirm(other["id"], other["payload_hash"])["status"] == "done"
    assert port.sent_log == [("reminder", "INV2")]


def test_hold_added_during_preflight_blocks_send(
    service: ProposalService, port: FakePayPal, monkeypatch: pytest.MonkeyPatch
) -> None:
    pending = service.propose_reminder("INV1")
    original = port.get_invoice

    def read_with_new_hold(invoice_id: str) -> Invoice | None:
        ContactService(service.store).change(invoice_id, "complaint")
        return original(invoice_id)

    monkeypatch.setattr(port, "get_invoice", read_with_new_hold)
    result = service.confirm(pending["id"], pending["payload_hash"])
    assert result["status"] == "failed" and "hold" in result["error"]
    assert not port.sent_log


def test_hold_survives_restart_and_only_current_version_can_be_released(tmp_path: Path) -> None:
    path = str(tmp_path / "store.db")
    first = ContactService(SqliteProposalStore(path))
    held = first.change("INV1", "dispute")["hold"]
    restarted = SqliteProposalStore(path)
    service = ProposalService(FakePayPal(), restarted, today=lambda: TODAY)
    with pytest.raises(PolicyError, match="hold"):
        service.propose_reminder("INV1")
    contacts = ContactService(restarted)
    assert contacts.change("INV1", None, held["version"])["hold"]["active"] is False
    assert service.propose_reminder("INV1")["status"] == "pending"
    current = contacts.change("INV1", "contact_preference")["hold"]
    with pytest.raises(Conflict):
        contacts.change("INV1", None, held["version"])
    assert restarted.contact_hold("INV1") == current
    assert contacts.change("INV1", "other_review")["hold"] == current
    assert [e["event"] for e in restarted.events("hold:INV1")] == [
        "hold_set",
        "reminder_blocked",
        "hold_released",
        "hold_set",
    ]


@pytest.mark.parametrize(("invoice_id", "reason"), [("../bad", "dispute"), ("INV1", "unknown")])
def test_invalid_hold_input_is_rejected(invoice_id: str, reason: str) -> None:
    store = SqliteProposalStore()
    with pytest.raises(PolicyError):
        ContactService(store).change(invoice_id, reason)
    assert store.contact_hold(invoice_id) is None


def test_hold_from_other_connection_blocks_pending_claim(tmp_path: Path) -> None:
    path = str(tmp_path / "store.db")
    port = FakePayPal()
    service = ProposalService(port, SqliteProposalStore(path), today=lambda: TODAY)
    pending = service.propose_reminder("INV1")
    ContactService(SqliteProposalStore(path)).change("INV1", "dispute")
    with pytest.raises(Conflict):
        service.confirm(pending["id"], pending["payload_hash"])
    assert not port.sent_log
