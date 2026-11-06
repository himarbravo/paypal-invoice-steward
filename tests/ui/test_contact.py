from fastapi.testclient import TestClient

from paypal_invoice_steward.ui.config import Settings
from paypal_invoice_steward.ui.web import create_app

from ..core.conftest import TODAY, FakePayPal


def test_operator_hold_api_and_audit() -> None:
    app = create_app(Settings(db_path=":memory:"), port=FakePayPal(), today=lambda: TODAY)
    client = TestClient(app)
    url = "/api/invoices/INV1/hold"
    result = client.post(url, json={"reason": "dispute"})
    assert result.status_code == 200 and result.json()["hold"]["active"]
    assert "cannot recall" in result.json()["notice"]
    rows = client.get("/api/invoices").json()["invoices"]
    assert next(row for row in rows if row["id"] == "INV1")["contact_hold"]["active"]
    assert client.post(url + "/release", json={"version": "wrong"}).status_code == 409
    version = result.json()["hold"]["version"]
    assert not client.post(url + "/release", json={"version": version}).json()["hold"]["active"]
    events = client.get(url).json()["events"]
    assert [event["event"] for event in events] == ["hold_set", "hold_released"]
    assert client.post(url, json={"reason": "invented"}).status_code == 422


def test_hold_api_is_local_operator_only() -> None:
    app = create_app(Settings(db_path=":memory:"), port=FakePayPal(), today=lambda: TODAY)
    remote = TestClient(app, base_url="http://127.0.0.1", client=("203.0.113.9", 54000))
    url = "/api/invoices/INV1/hold"
    assert remote.post(url, json={"reason": "dispute"}).status_code == 403
    local = TestClient(app)
    assert (
        local.post(
            url, json={"reason": "dispute"}, headers={"Origin": "https://untrusted.example"}
        ).status_code
        == 403
    )
    assert local.get(url).json()["hold"] is None
