import sqlite3
import threading
from datetime import date
from pathlib import Path

import pytest

from paypal_invoice_steward.persistence.store import SCHEMA_VERSION, SqliteProposalStore


def _proposal(pid: str = "p1") -> dict[str, object]:
    return {
        "id": pid,
        "kind": "invoice",
        "payload": {"a": 1},
        "payload_hash": "h",
        "summary": "s",
        "reference": "STW-1",
        "status": "pending",
    }


def test_round_trip_and_filtering() -> None:
    store = SqliteProposalStore()
    store.insert(_proposal())
    got = store.get("p1")
    assert got is not None and got["payload"] == {"a": 1} and got["result"] is None
    assert [p["id"] for p in store.list(["pending"])] == ["p1"]
    assert store.list(["done"]) == []
    assert store.get("missing") is None


def test_transition_is_compare_and_swap() -> None:
    store = SqliteProposalStore()
    store.insert(_proposal())
    assert store.transition("p1", ["pending"], "executing")
    assert not store.transition("p1", ["pending"], "executing")
    assert store.transition("p1", ["executing"], "done", result={"ok": True})
    got = store.get("p1")
    assert got is not None and got["status"] == "done" and got["result"] == {"ok": True}


def test_claim_with_event_commits_reservation_and_audit_together() -> None:
    store = SqliteProposalStore()
    proposal = _proposal()
    store.insert(proposal)

    assert store.claim_with_event(proposal, date.today(), "confirmed", "from pending")

    current = store.get("p1")
    assert current is not None and current["status"] == "executing"
    assert [(event["event"], event["detail"]) for event in store.events("p1")] == [
        ("confirmed", "from pending")
    ]


def test_claim_with_event_rolls_back_if_audit_insert_fails() -> None:
    store = SqliteProposalStore()
    proposal = _proposal()
    store.insert(proposal)
    store._db.execute(
        "CREATE TRIGGER reject_event BEFORE INSERT ON events"
        " BEGIN SELECT RAISE(ABORT, 'event rejected'); END"
    )

    with pytest.raises(sqlite3.IntegrityError, match="event rejected"):
        store.claim_with_event(proposal, date.today(), "confirmed")

    current = store.get("p1")
    assert current is not None and current["status"] == "pending"
    assert store.events("p1") == []


def test_transition_with_event_rolls_back_if_audit_insert_fails() -> None:
    store = SqliteProposalStore()
    store.insert(_proposal())
    store._db.execute(
        "CREATE TRIGGER reject_event BEFORE INSERT ON events"
        " BEGIN SELECT RAISE(ABORT, 'event rejected'); END"
    )

    with pytest.raises(sqlite3.IntegrityError, match="event rejected"):
        store.transition_with_event("p1", ["pending"], "done", "done", result={"ok": True})

    current = store.get("p1")
    assert current is not None and current["status"] == "pending" and current["result"] is None
    assert store.events("p1") == []


def test_stale_transition_with_event_creates_no_event() -> None:
    store = SqliteProposalStore()
    store.insert(_proposal())

    assert not store.transition_with_event("p1", ["executing"], "done", "done")

    current = store.get("p1")
    assert current is not None and current["status"] == "pending"
    assert store.events("p1") == []


def test_log_if_status_rejects_a_stale_observation() -> None:
    store = SqliteProposalStore()
    store.insert(_proposal())

    assert store.log_if_status("p1", ["pending"], "verify", "invoice not found")
    assert store.transition("p1", ["pending"], "done")
    assert not store.log_if_status("p1", ["pending"], "verify", "stale")

    assert [(event["event"], event["detail"]) for event in store.events("p1")] == [
        ("verify", "invoice not found")
    ]


def test_only_one_concurrent_transition_wins() -> None:
    store = SqliteProposalStore()
    store.insert(_proposal())
    wins: list[bool] = []
    threads = [
        threading.Thread(target=lambda: wins.append(store.transition("p1", ["pending"], "x")))
        for _ in range(10)
    ]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    assert wins.count(True) == 1


def test_events_are_kept_in_order() -> None:
    store = SqliteProposalStore()
    store.log("p1", "proposed", "first")
    store.log("p1", "done")
    assert [e["event"] for e in store.events("p1")] == ["proposed", "done"]


def test_file_database_records_schema_version(tmp_path: Path) -> None:
    path = tmp_path / "sub" / "steward.db"
    SqliteProposalStore(str(path))
    version = sqlite3.connect(path).execute("PRAGMA user_version").fetchone()[0]
    assert version == SCHEMA_VERSION
