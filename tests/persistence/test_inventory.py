from pathlib import Path

import pytest

from paypal_invoice_steward.core.ports import InvoiceInventoryIncomplete, PayPalUncertain
from paypal_invoice_steward.persistence.inventory import ObservedPayPal
from paypal_invoice_steward.persistence.store import SqliteProposalStore

from ..core.conftest import FakePayPal


def test_missing_records_persist_until_observed_again(tmp_path: Path) -> None:
    path = str(tmp_path / "state.db")
    port = FakePayPal()
    reader = ObservedPayPal(port, SqliteProposalStore(path), "app-one")
    assert reader.inventory_status()["stale"]
    assert len(reader.list_invoices()) == 4
    removed = port.invoices.pop("INV1")
    for _ in range(2):
        with pytest.raises(InvoiceInventoryIncomplete):
            reader.list_invoices()
    restarted = ObservedPayPal(port, SqliteProposalStore(path), "app-one")
    state = restarted.inventory_status()
    assert state["observed_count"] == 3 and state["missing_ids"] == ["INV1"]
    assert state["last_success_at"] and state["stale"]
    port.invoices[removed.id] = removed
    assert len(restarted.list_invoices()) == 4
    assert restarted.inventory_status()["missing_ids"] == []
    assert not restarted.inventory_status()["stale"]


def test_failure_keeps_last_success_but_never_returns_cached_data(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    port = FakePayPal()
    reader = ObservedPayPal(port, SqliteProposalStore(), "app")
    reader.list_invoices()
    before = reader.inventory_status()

    def fail() -> None:
        raise PayPalUncertain("secret provider payload")

    monkeypatch.setattr(port, "list_invoices", fail)
    with pytest.raises(PayPalUncertain):
        reader.list_invoices()
    state = reader.inventory_status()
    assert state["status"] == "failed" and state["stale"]
    assert state["last_success_at"] == before["last_success_at"]
    assert state["observed_count"] == before["observed_count"]
    assert "secret" not in str(state)


def test_sources_are_isolated_by_mode_and_app() -> None:
    port = FakePayPal()
    store = SqliteProposalStore()
    demo = ObservedPayPal(port, store, "app")
    demo.list_invoices()
    assert ObservedPayPal(port, store, "another-app").inventory_status()["status"] == "not_read"
    port.mode = "sandbox"
    assert ObservedPayPal(port, store, "app").inventory_status()["status"] == "not_read"


def test_older_response_cannot_replace_newer_attempt(tmp_path: Path) -> None:
    path = str(tmp_path / "state.db")
    first, second = SqliteProposalStore(path), SqliteProposalStore(path)
    first.observe_inventory("app", "old", start=True)
    second.observe_inventory("app", "new", start=True)
    assert first.observe_inventory("app", "old", ["OLD"]) is None
    assert second.inventory("app")["status"] == "reading"
    second.observe_inventory("app", "new", ["NEW"])
    assert first.observe_inventory("app", "old") is None
    assert first.inventory("app")["observed_ids"] == ["NEW"]


@pytest.mark.parametrize("when", ["2000-01-01T00:00:00+00:00", "2100-01-01T00:00:00+00:00"])
def test_old_or_future_watermark_is_stale(monkeypatch: pytest.MonkeyPatch, when: str) -> None:
    monkeypatch.setattr("paypal_invoice_steward.persistence.store._now", lambda: when)
    reader = ObservedPayPal(FakePayPal(), SqliteProposalStore(), "app")
    reader.list_invoices()
    assert reader.inventory_status()["stale"]


def test_interrupted_read_stays_unverified_after_restart(tmp_path: Path) -> None:
    path = str(tmp_path / "state.db")
    reader = ObservedPayPal(FakePayPal(), SqliteProposalStore(path), "app")
    reader.list_invoices()
    reader.store.observe_inventory(reader.source, "interrupted", start=True)
    state = ObservedPayPal(FakePayPal(), SqliteProposalStore(path), "app").inventory_status()
    assert state["status"] == "reading" and state["stale"] and state["last_success_at"]


def test_superseded_adapter_read_returns_no_financial_data(monkeypatch: pytest.MonkeyPatch) -> None:
    port, store = FakePayPal(), SqliteProposalStore()
    reader = ObservedPayPal(port, store, "app")
    original = port.list_invoices

    def replaced() -> list:
        store.observe_inventory(reader.source, "newer", start=True)
        return original()

    monkeypatch.setattr(port, "list_invoices", replaced)
    with pytest.raises(InvoiceInventoryIncomplete):
        reader.list_invoices()
    assert reader.inventory_status()["stale"]
