"""SQLite implementation of `core.ports.ProposalStore`: proposals and their audit trail.

A proposal's status only changes through `transition`, which is a compare and
swap: it succeeds for exactly one caller. That is what stops two simultaneous
"Confirm" clicks from running the same action twice.
"""

from __future__ import annotations

import builtins
import json
import os
import sqlite3
import threading
from collections.abc import Iterable
from datetime import UTC, date, datetime

from ..core.models import JSON

SCHEMA_VERSION = 2

_SCHEMA = """
CREATE TABLE IF NOT EXISTS proposals (
    id           TEXT PRIMARY KEY,
    kind         TEXT NOT NULL,
    payload      TEXT NOT NULL,
    payload_hash TEXT NOT NULL,
    summary      TEXT NOT NULL,
    reference    TEXT NOT NULL,
    status       TEXT NOT NULL,
    result       TEXT,
    error        TEXT,
    created_at   TEXT NOT NULL,
    updated_at   TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS events (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    proposal_id TEXT NOT NULL,
    event       TEXT NOT NULL,
    detail      TEXT NOT NULL,
    at          TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS inventory_state (
    source TEXT PRIMARY KEY,
    data TEXT NOT NULL
);
"""


def _now() -> str:
    return datetime.now(UTC).isoformat(timespec="seconds")


class SqliteProposalStore:
    """Thread-safe SQLite store. `path` may be `:memory:` for tests."""

    def __init__(self, path: str = ":memory:") -> None:
        if path != ":memory:":
            os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
        self._lock = threading.RLock()
        self._db = sqlite3.connect(path, check_same_thread=False)
        self._db.row_factory = sqlite3.Row
        with self._lock:
            self._db.executescript(_SCHEMA)
            self._db.execute(f"PRAGMA user_version = {SCHEMA_VERSION}")
            self._db.commit()

    @staticmethod
    def _row(row: sqlite3.Row | None) -> JSON | None:
        if row is None:
            return None
        data: JSON = dict(row)
        data["payload"] = json.loads(data["payload"])
        data["result"] = json.loads(data["result"]) if data["result"] else None
        return data

    def insert(self, proposal: JSON) -> None:
        now = _now()
        with self._lock:
            self._db.execute(
                "INSERT INTO proposals (id, kind, payload, payload_hash, summary, reference,"
                " status, result, error, created_at, updated_at)"
                " VALUES (?, ?, ?, ?, ?, ?, ?, NULL, NULL, ?, ?)",
                (
                    proposal["id"],
                    proposal["kind"],
                    json.dumps(proposal["payload"]),
                    proposal["payload_hash"],
                    proposal["summary"],
                    proposal["reference"],
                    proposal["status"],
                    now,
                    now,
                ),
            )
            self._db.commit()

    def get(self, proposal_id: str) -> JSON | None:
        with self._lock:
            row = self._db.execute(
                "SELECT * FROM proposals WHERE id = ?", (proposal_id,)
            ).fetchone()
        return self._row(row)

    def list(self, statuses: Iterable[str] | None = None) -> list[JSON]:
        with self._lock:
            if statuses is None:
                rows = self._db.execute(
                    "SELECT * FROM proposals ORDER BY created_at DESC, rowid DESC"
                ).fetchall()
            else:
                wanted = [*statuses]
                marks = ",".join("?" for _ in wanted)
                rows = self._db.execute(
                    f"SELECT * FROM proposals WHERE status IN ({marks})"
                    " ORDER BY created_at DESC, rowid DESC",
                    wanted,
                ).fetchall()
        return [data for data in map(self._row, rows) if data is not None]

    def claim(self, proposal: JSON, reminder_cutoff: date) -> bool:
        # BEGIN IMMEDIATE serializes readers that intend to write, including
        # separate connections/processes; a per-instance lock alone cannot do so.
        with self._lock, self._db:
            self._db.execute("BEGIN IMMEDIATE")
            current = self.get(proposal["id"])
            if current is None or any(
                current[key] != proposal[key]
                for key in ("kind", "payload", "payload_hash", "reference", "status")
            ):
                return False
            if current["status"] not in ("pending", "unverified"):
                return False
            if current["kind"] == "reminder":
                if current["status"] != "pending":
                    return False
                invoice_id = current["payload"]["invoice_id"]
                for other in self.list(["executing", "unverified", "done"]):
                    if other["kind"] != "reminder":
                        continue
                    if other["payload"]["invoice_id"] != invoice_id:
                        continue
                    if other["status"] != "done":
                        return False
                    if datetime.fromisoformat(other["updated_at"]).date() > reminder_cutoff:
                        return False
            self._db.execute(
                "UPDATE proposals SET status = 'executing', error = NULL, updated_at = ?"
                " WHERE id = ?",
                (_now(), proposal["id"]),
            )
            return True

    def transition(
        self,
        proposal_id: str,
        from_statuses: Iterable[str],
        to_status: str,
        result: JSON | None = None,
        error: str | None = None,
    ) -> bool:
        """Move a proposal to a new status only if it is currently in one of
        `from_statuses`. Returns True for exactly one of any concurrent callers."""
        allowed = [*from_statuses]
        marks = ",".join("?" for _ in allowed)
        with self._lock:
            cur = self._db.execute(
                "UPDATE proposals SET status = ?, result = COALESCE(?, result),"
                f" error = ?, updated_at = ? WHERE id = ? AND status IN ({marks})",
                (
                    to_status,
                    json.dumps(result) if result is not None else None,
                    error,
                    _now(),
                    proposal_id,
                    *allowed,
                ),
            )
            self._db.commit()
            return cur.rowcount == 1

    def log(self, proposal_id: str, event: str, detail: str = "") -> None:
        with self._lock:
            self._db.execute(
                "INSERT INTO events (proposal_id, event, detail, at) VALUES (?, ?, ?, ?)",
                (proposal_id, event, detail, _now()),
            )
            self._db.commit()

    def inventory(self, source: str) -> JSON:
        with self._lock:
            row = self._db.execute(
                "SELECT data FROM inventory_state WHERE source = ?", (source,)
            ).fetchone()
        return json.loads(row[0]) if row else {"status": "not_read", "missing_ids": []}

    def observe_inventory(
        self,
        source: str,
        attempt: str,
        ids: builtins.list[str] | None = None,
        *,
        start: bool = False,
    ) -> JSON | None:
        with self._lock, self._db:
            self._db.execute("BEGIN IMMEDIATE")
            state = self.inventory(source)
            if start:
                state.update(attempt=attempt, last_attempt_at=_now(), status="reading")
            elif state.get("attempt") != attempt:
                return None  # an older response cannot overwrite a newer read
            elif ids is None:
                state["status"] = "failed"
            else:
                known = set(state.get("observed_ids", [])) | set(state["missing_ids"])
                state.update(
                    status="observed",
                    last_success_at=_now(),
                    observed_ids=sorted(ids),
                    observed_count=len(ids),
                    missing_ids=sorted(known - set(ids)),
                )
            self._db.execute(
                "INSERT INTO inventory_state VALUES (?, ?) "
                "ON CONFLICT(source) DO UPDATE SET data = excluded.data",
                (source, json.dumps(state)),
            )
            return state

    def events(self, proposal_id: str) -> builtins.list[JSON]:
        with self._lock:
            rows = self._db.execute(
                "SELECT event, detail, at FROM events WHERE proposal_id = ? ORDER BY id",
                (proposal_id,),
            ).fetchall()
        events: builtins.list[JSON] = [dict(r) for r in rows]
        return events
