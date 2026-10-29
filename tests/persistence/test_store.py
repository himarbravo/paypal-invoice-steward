import sqlite3
import threading
from pathlib import Path

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
