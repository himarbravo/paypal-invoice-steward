import json
import sqlite3
from datetime import date
from pathlib import Path

import pytest

from paypal_invoice_steward.core.models import JSON
from paypal_invoice_steward.persistence.store import SqliteProposalStore


def proposal(pid: str, invoice_id: str = "INV1") -> JSON:
    return {
        "id": pid,
        "kind": "reminder",
        "payload": {"invoice_id": invoice_id},
        "payload_hash": "hash",
        "reference": f"STW-{pid}",
        "summary": "Remind invoice",
        "status": "pending",
    }


@pytest.mark.parametrize(
    ("status", "updated", "allowed"),
    [
        ("executing", "2020-01-01", False),
        ("unverified", "2020-01-01", False),
        ("done", "2026-10-27", False),
        ("done", "2026-10-26", True),
        ("done", "2026-10-25", True),
        ("failed", "2026-10-29", True),
        ("dismissed", "2026-10-29", True),
    ],
)
def test_claim_checks_durable_cooldown_after_restart(
    tmp_path: Path, status: str, updated: str, allowed: bool
) -> None:
    path = str(tmp_path / "store.db")
    first = SqliteProposalStore(path)
    first.insert(proposal("previous"))
    first.insert(proposal("next"))
    with sqlite3.connect(path) as db:
        db.execute(
            "UPDATE proposals SET status = ?, updated_at = ? WHERE id = 'previous'",
            (status, updated + "T12:00:00+00:00"),
        )
    restarted = SqliteProposalStore(path)
    assert restarted.claim(proposal("next"), date(2026, 10, 26)) is allowed
    current = restarted.get("next")
    assert current is not None
    assert current["status"] == ("executing" if allowed else "pending")


@pytest.mark.parametrize("status", ["executing", "unverified", "done"])
def test_other_invoices_do_not_share_execution_slot(status: str) -> None:
    store = SqliteProposalStore()
    store.insert(proposal("other", "INV2"))
    store.transition("other", ["pending"], status)
    store.insert(proposal("next"))
    assert store.claim(proposal("next"), date(2026, 10, 26))


@pytest.mark.parametrize("field", ["kind", "payload", "payload_hash", "reference", "status"])
def test_claim_rejects_changed_snapshot(tmp_path: Path, field: str) -> None:
    path = str(tmp_path / "store.db")
    store = SqliteProposalStore(path)
    reviewed = proposal("next")
    store.insert(reviewed)
    changed = json.dumps({"invoice_id": "WRONG"}) if field == "payload" else "changed"
    with sqlite3.connect(path) as db:
        db.execute(f"UPDATE proposals SET {field} = ? WHERE id = 'next'", (changed,))
    assert not store.claim(reviewed, date(2026, 10, 26))
    current = store.get("next")
    assert current is not None and current["status"] != "executing"


@pytest.mark.parametrize(("kind", "allowed"), [("invoice", True), ("reminder", False)])
def test_only_invoice_uncertain_outcomes_may_be_claimed_again(kind: str, allowed: bool) -> None:
    store = SqliteProposalStore()
    reviewed = proposal("retry")
    reviewed.update(kind=kind, status="unverified")
    store.insert(reviewed)
    assert store.claim(reviewed, date(2026, 10, 26)) is allowed


def test_exception_rolls_back_claim_transaction(tmp_path: Path) -> None:
    path = str(tmp_path / "store.db")
    store = SqliteProposalStore(path)
    store.insert(proposal("previous"))
    store.insert(proposal("next"))
    with sqlite3.connect(path) as db:
        db.execute(
            "UPDATE proposals SET status = 'done', updated_at = 'invalid' WHERE id = 'previous'"
        )
    with pytest.raises(ValueError):
        store.claim(proposal("next"), date(2026, 10, 26))
    # A failed transaction must not leave the database write-locked.
    other = SqliteProposalStore(path)
    assert other.transition("previous", ["done"], "failed")
    assert store.claim(proposal("next"), date(2026, 10, 26))
