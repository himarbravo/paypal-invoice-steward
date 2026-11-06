from concurrent.futures import ThreadPoolExecutor
from copy import deepcopy
from pathlib import Path
from threading import Barrier

import pytest

from paypal_invoice_steward.core.proposals import Conflict, PolicyError, ProposalService
from paypal_invoice_steward.persistence.store import SqliteProposalStore

from .conftest import TODAY, FakePayPal


def test_different_proposals_cannot_send_same_invoice_concurrently(tmp_path: Path) -> None:
    path = str(tmp_path / "proposals.db")
    port = FakePayPal()
    services = [
        ProposalService(port, SqliteProposalStore(path), today=lambda: TODAY) for _ in range(2)
    ]
    first = services[0].propose_reminder("INV1")
    # Reproduce duplicate pending proposals from a creation race or an older database.
    second = deepcopy(first)
    second.update(id="second", reference="STW-SECOND")
    services[0].store.insert(second)
    barrier = Barrier(2)

    def confirm(index: int) -> str:
        proposal = [first, second][index]
        barrier.wait(timeout=5)
        try:
            return str(services[index].confirm(proposal["id"], proposal["payload_hash"])["status"])
        except Conflict:
            return "blocked"

    with ThreadPoolExecutor(max_workers=2) as pool:
        assert sorted(pool.map(confirm, range(2))) == ["blocked", "done"]
    assert port.sent_log == [("reminder", "INV1")]
    pending = services[0].store.list(["pending"])[0]
    assert services[0].store.events(pending["id"])[-1]["event"] == "refused"
    restarted = ProposalService(port, SqliteProposalStore(path), today=lambda: TODAY)
    with pytest.raises(Conflict):
        restarted.confirm(pending["id"], pending["payload_hash"])
    assert port.sent_log == [("reminder", "INV1")]


def test_executing_reminder_blocks_new_proposal(service: ProposalService) -> None:
    proposal = service.propose_reminder("INV1")
    assert service.store.transition(proposal["id"], ["pending"], "executing")
    with pytest.raises(PolicyError, match="executing|unknown outcome"):
        service.propose_reminder("INV1")
