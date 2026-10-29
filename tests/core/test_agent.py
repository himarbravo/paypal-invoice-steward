import json
from types import SimpleNamespace as NS
from typing import Any

from paypal_invoice_steward.core.agent import TOOLS, LLMAgent, OfflineAgent, Toolbox
from paypal_invoice_steward.core.proposals import ProposalService

from .conftest import TODAY, FakePayPal


class ScriptedClient:
    """Asks for one reminder proposal, then answers with text."""

    def __init__(self, invoice_id: str) -> None:
        self.invoice_id = invoice_id
        self.calls: list[dict[str, Any]] = []

    def create_message(self, **kwargs: Any) -> Any:
        self.calls.append(kwargs)
        if len(self.calls) == 1:
            block = NS(
                type="tool_use",
                id="t1",
                name="propose_reminder",
                input={"invoice_id": self.invoice_id},
            )
            return NS(content=[block], stop_reason="tool_use")
        return NS(content=[NS(type="text", text="Prepared a reminder.")], stop_reason="end_turn")


def test_no_tool_can_execute_anything() -> None:
    names = {t["name"] for t in TOOLS}
    assert names == {
        "list_invoices",
        "get_cash_flow_forecast",
        "list_proposals",
        "propose_invoice",
        "propose_reminder",
    }
    forbidden = ("send", "confirm", "execute", "pay", "cancel", "delete")
    assert not any(word in name for name in names for word in forbidden)


def test_llm_agent_only_creates_pending_proposals(
    service: ProposalService, port: FakePayPal
) -> None:
    client = ScriptedClient("INV1")
    reply = LLMAgent(service, port, client, "model", lambda: TODAY).run("s", "remind them")
    assert reply.text == "Prepared a reminder."
    assert len(reply.proposal_ids) == 1
    assert service.get(reply.proposal_ids[0])["status"] == "pending"
    assert port.sent_log == []
    assert client.calls[0]["tools"] == TOOLS


def test_tool_errors_go_back_to_the_model(service: ProposalService, port: FakePayPal) -> None:
    client = ScriptedClient("missing")
    reply = LLMAgent(service, port, client, "model", lambda: TODAY).run("s", "remind them")
    assert reply.proposal_ids == []
    results = [
        block
        for message in client.calls[1]["messages"]
        if isinstance(message["content"], list)
        for block in message["content"]
        if block.get("type") == "tool_result"
    ]
    assert results and results[0]["is_error"] is True


def test_toolbox_rejects_unknown_tools(service: ProposalService, port: FakePayPal) -> None:
    content, is_error = Toolbox(service, port, lambda: TODAY).run("send_invoice", {})
    assert is_error and "error" in json.loads(content)


def test_offline_agent_parses_an_invoice_request(
    service: ProposalService, port: FakePayPal
) -> None:
    reply = OfflineAgent(service, port, lambda: TODAY).run(
        "s", "Invoice Alba Design Studio billing@albadesign.example 450 EUR for a logo refresh"
    )
    proposal = service.get(reply.proposal_ids[0])
    assert proposal["payload"]["customer_name"] == "Alba Design Studio"
    assert proposal["payload"]["items"][0] == {
        "description": "Logo refresh",
        "quantity": 1,
        "unit_price": 450.0,
    }
    assert port.sent_log == []


def test_offline_agent_reminds_only_late_invoices(
    service: ProposalService, port: FakePayPal
) -> None:
    reply = OfflineAgent(service, port, lambda: TODAY).run("s", "Remind my late customers")
    targets = {service.get(pid)["payload"]["invoice_id"] for pid in reply.proposal_ids}
    assert targets == {"INV1", "INV2"}


def test_offline_agent_forecast_and_fallback(service: ProposalService, port: FakePayPal) -> None:
    agent = OfflineAgent(service, port, lambda: TODAY)
    assert "Next 8 weeks (EUR)" in agent.run("s", "What is my cash flow forecast?").text
    assert "Offline demo mode" in agent.run("s", "hello").text
