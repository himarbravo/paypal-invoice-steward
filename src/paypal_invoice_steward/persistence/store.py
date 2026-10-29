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
from datetime import UTC, datetime

from ..core.models import JSON

SCHEMA_VERSION = 1

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

    def events(self, proposal_id: str) -> builtins.list[JSON]:
        with self._lock:
            rows = self._db.execute(
                "SELECT event, detail, at FROM events WHERE proposal_id = ? ORDER BY id",
                (proposal_id,),
            ).fetchall()
        events: builtins.list[JSON] = [dict(r) for r in rows]
        return events
