from datetime import date
from typing import Any

import pytest
from fastapi.testclient import TestClient

from paypal_invoice_steward.persistence.paypal_demo import DemoPayPal
from paypal_invoice_steward.ui.config import Settings
from paypal_invoice_steward.ui.web import create_app

TODAY = date(2026, 10, 29)
INVOICE_REQUEST = "Invoice Alba Design Studio billing@albadesign.example 450 EUR for a logo refresh"


@pytest.fixture
def client() -> TestClient:
    settings = Settings(mode="demo", db_path=":memory:")
    return TestClient(create_app(settings, today=lambda: TODAY))


def chat(client: TestClient, text: str) -> Any:
    response = client.post("/api/chat", json={"message": text, "session_id": "t"})
    assert response.status_code == 200
    return response.json()


def test_health_and_index(client: TestClient) -> None:
    health = client.get("/api/health").json()
    assert health["mode"] == "demo" and health["agent"] == "offline" and health["model"] is None
    page = client.get("/")
    assert page.status_code == 200 and "Invoice Steward" in page.text


def test_overview_endpoints(client: TestClient) -> None:
    invoices = client.get("/api/invoices").json()["invoices"]
    assert invoices and invoices[0]["status"] == "open"
    assert "EUR" in client.get("/api/forecast").json()["forecasts"]


def test_chat_then_confirm_with_the_reviewed_hash(client: TestClient) -> None:
    proposal = chat(client, "Remind my late customers")["proposals"][0]
    assert proposal["status"] == "pending"
    url = f"/api/proposals/{proposal['id']}/confirm"
    assert client.post(url, json={"payload_hash": "x" * 16}).status_code == 409
    done = client.post(url, json={"payload_hash": proposal["payload_hash"]}).json()
    assert done["status"] == "done"
    listed = client.get("/api/proposals", params={"status": "done"}).json()["proposals"]
    assert [p["id"] for p in listed] == [proposal["id"]]


def test_unknown_proposal_is_404(client: TestClient) -> None:
    assert client.get("/api/proposals/nope").status_code == 404


def test_simulated_timeout_then_check_paypal(client: TestClient) -> None:
    proposal = chat(client, INVOICE_REQUEST)["proposals"][0]
    client.post("/api/demo/fail-next", json={"mode": "timeout_after_send"})
    url = f"/api/proposals/{proposal['id']}"
    result = client.post(f"{url}/confirm", json={"payload_hash": proposal["payload_hash"]})
    assert result.json()["status"] == "unverified"
    assert client.post(f"{url}/verify").json()["status"] == "done"


def test_policy_errors_are_422(client: TestClient) -> None:
    reply = chat(client, "Invoice Big Co big@co.example 50000 EUR for a lot")
    assert reply["proposals"] == []
    assert "directly in PayPal" in reply["reply"]


def test_agent_failure_does_not_leak() -> None:
    class Broken:
        mode = "broken"

        def run(self, session_id: str, user_text: str) -> Any:
            raise RuntimeError("secret provider detail")

    settings = Settings(mode="demo", db_path=":memory:")
    client = TestClient(create_app(settings, agent=Broken(), today=lambda: TODAY))
    response = client.post("/api/chat", json={"message": "hi", "session_id": "t"})
    assert response.status_code == 502 and "secret" not in response.text


@pytest.mark.parametrize("path", ["/", "/api/health", "/api/invoices", "/api/proposals"])
def test_remote_clients_cannot_access_demo(path: str) -> None:
    app = create_app(Settings(mode="demo", db_path=":memory:"), today=lambda: TODAY)
    remote = TestClient(app, base_url="http://127.0.0.1", client=("203.0.113.9", 54000))
    response = remote.get(path, headers={"X-Forwarded-For": "127.0.0.1"})
    assert response.status_code == 403


def test_remote_clients_cannot_confirm_proposals() -> None:
    app = create_app(Settings(mode="demo", db_path=":memory:"), today=lambda: TODAY)
    remote = TestClient(app, base_url="http://127.0.0.1", client=("203.0.113.9", 54000))
    response = remote.post("/api/proposals/some-id/confirm", json={"payload_hash": "a" * 64})
    assert response.status_code == 403


def test_rejects_untrusted_host_header_even_from_local_client() -> None:
    app = create_app(Settings(mode="demo", db_path=":memory:"), today=lambda: TODAY)
    local = TestClient(app, base_url="http://127.0.0.1", client=("127.0.0.1", 50000))
    response = local.get("/api/invoices", headers={"Host": "evil.example"})
    assert response.status_code == 403


def test_rejects_cross_origin_write_from_local_browser(client: TestClient) -> None:
    response = client.post(
        "/api/proposals/unknown/dismiss", headers={"Origin": "https://evil.example"}
    )
    assert response.status_code == 403


def test_same_origin_write_reaches_the_normal_route(client: TestClient) -> None:
    response = client.post(
        "/api/proposals/unknown/dismiss", headers={"Origin": "http://testserver"}
    )
    assert response.status_code == 404


class SandboxTestPort(DemoPayPal):
    mode = "sandbox"


def test_sandbox_http_confirm_is_blocked_with_default_settings() -> None:
    port = SandboxTestPort(today=lambda: TODAY)
    app = create_app(
        Settings(mode="sandbox", db_path=":memory:"),
        port=port,
        today=lambda: TODAY,
    )
    client = TestClient(app)
    proposal = chat(client, INVOICE_REQUEST)["proposals"][0]
    reply = client.post(
        f"/api/proposals/{proposal['id']}/confirm",
        json={"payload_hash": proposal["payload_hash"]},
    )
    assert reply.status_code == 403
    assert "read-only" in reply.json()["error"]
    assert client.get(f"/api/proposals/{proposal['id']}").json()["status"] == "pending"
    assert port.sent_log == []


@pytest.mark.parametrize("enabled", [False, True])
def test_sandbox_health_shows_outbound_permission_without_credentials(enabled: bool) -> None:
    settings = Settings(mode="sandbox", sandbox_writes_enabled=enabled, db_path=":memory:")
    port = SandboxTestPort(today=lambda: TODAY)
    health = TestClient(create_app(settings, port=port, today=lambda: TODAY)).get(
        "/api/health"
    ).json()
    assert health["mode"] == "sandbox"
    assert health["outbound_actions_enabled"] is enabled
    assert "client_secret" not in health
