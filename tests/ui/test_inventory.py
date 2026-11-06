from fastapi.testclient import TestClient

from paypal_invoice_steward.ui.config import Settings
from paypal_invoice_steward.ui.web import create_app

from ..core.conftest import TODAY, FakePayPal


def test_api_exposes_observation_and_refuses_missing_record_totals() -> None:
    port = FakePayPal()
    port.mode = "demo"
    client = TestClient(create_app(Settings(db_path=":memory:"), port=port, today=lambda: TODAY))
    observed = client.get("/api/invoices").json()["inventory"]
    assert observed["scope"] == "synthetic demo" and observed["atomic_snapshot"] is False
    port.invoices.pop("INV1")
    assert client.get("/api/forecast").status_code == 503
    assert client.get("/api/invoices").status_code == 503
    state = client.get("/api/inventory-status").json()
    assert state["missing_ids"] == ["INV1"] and state["stale"]
    page = client.get("/").text
    assert 'id="inventory-status"' in page and "Last invoice check" in page
