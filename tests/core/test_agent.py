import json
from types import SimpleNamespace as NS
from typing import Any

import pytest

from paypal_invoice_steward.core.agent import (
    PROPOSE_TOOLS,
    READ_TOOLS,
    SYSTEM_PROMPT,
    TOOLS,
    LLMAgent,
    OfflineAgent,
    Toolbox,
    tools_for,
)
from paypal_invoice_steward.core.models import REFUND_REVIEW_MESSAGE, Invoice
from paypal_invoice_steward.core.ports import (
    INCOMPLETE_INVENTORY_MESSAGE,
    InvoiceInventoryIncomplete,
    PayPalError,
    PayPalUncertain,
)
from paypal_invoice_steward.core.proposals import (
    PAYPAL_REMINDER_TEXT,
    PolicyError,
    ProposalService,
)

from .conftest import TODAY, FakePayPal


class ScriptedClient:
    """Asks for one reminder proposal, then answers with text."""

    def __init__(self, invoice_id: str, note: str | None = None) -> None:
        self.invoice_id = invoice_id
        self.note = note
        self.calls: list[dict[str, Any]] = []

    def create_message(self, **kwargs: Any) -> Any:
        self.calls.append(kwargs)
        if len(self.calls) == 1:
            args = {"invoice_id": self.invoice_id}
            if self.note is not None:
                args["note"] = self.note
            block = NS(type="tool_use", id="t1", name="propose_reminder", input=args)
            return NS(content=[block], stop_reason="tool_use")
        return NS(content=[NS(type="text", text="Prepared a reminder.")], stop_reason="end_turn")


def tool_results(call: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        block
        for message in call["messages"]
        if isinstance(message["content"], list)
        for block in message["content"]
        if block.get("type") == "tool_result"
    ]


def test_no_tool_can_execute_anything() -> None:
    names = {t["name"] for t in TOOLS}
    assert set(READ_TOOLS) == {
        "list_invoices",
        "get_cash_flow_forecast",
        "get_receivables_aging",
        "list_proposals",
    }
    assert set(PROPOSE_TOOLS) == {"propose_invoice", "propose_reminder"}
    assert names == set(READ_TOOLS) | set(PROPOSE_TOOLS)
    assert not set(READ_TOOLS) & set(PROPOSE_TOOLS)
    forbidden = ("send", "confirm", "execute", "pay", "cancel", "delete")
    assert not any(word in name for name in names for word in forbidden)


def test_receivables_aging_tool_is_read_only(service: ProposalService, port: FakePayPal) -> None:
    toolbox = Toolbox(service, port, lambda: TODAY)
    before = len(service.list())
    content, is_error = toolbox.run("get_receivables_aging", {})
    assert not is_error
    result = json.loads(content)
    assert result["basis"] == "current open invoice face amounts"
    assert len(service.list()) == before
    assert toolbox.created == []
    assert port.sent_log == []


def test_model_aging_projection_preserves_verified_paypal_residual_basis(
    service: ProposalService, port: FakePayPal
) -> None:
    for candidate in port.invoices.values():
        if candidate.status == "open":
            candidate.balance_source = "paypal_due_amount"
            candidate.remaining_amount = candidate.amount
    invoice = port.invoices["INV1"]
    invoice.amount = 450.0
    invoice.remaining_amount = 250.75
    invoice.balance_source = "paypal_due_amount"

    content, is_error = Toolbox(service, port, lambda: TODAY).run_for_model(
        "get_receivables_aging", {}
    )

    assert not is_error
    result = json.loads(content)
    assert result["basis"] == "PayPal due_amount residuals"
    row = next(row for row in result["invoices"] if row["id"] == "INV1")
    assert row["amount"] == 250.75


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


def test_sandbox_reminder_tool_offers_no_custom_note() -> None:
    sandbox = {tool["name"]: tool for tool in tools_for("sandbox")}
    reminder = sandbox["propose_reminder"]
    assert "note" not in reminder["input_schema"]["properties"]
    assert "PayPal writes the reminder email" in reminder["description"]
    assert set(sandbox) == {tool["name"] for tool in TOOLS}
    assert tools_for("demo") == TOOLS
    demo_reminder = next(tool for tool in TOOLS if tool["name"] == "propose_reminder")
    assert "note" in demo_reminder["input_schema"]["properties"]


def test_sandbox_agent_prepares_a_reminder_even_when_the_model_writes_a_note(
    service: ProposalService, port: FakePayPal
) -> None:
    port.mode = "sandbox"
    client = ScriptedClient("INV1", note="MODEL_NOTE_TEXT please pay soon.")
    reply = LLMAgent(service, port, client, "model", lambda: TODAY).run("s", "remind them")

    assert len(reply.proposal_ids) == 1
    proposal = service.get(reply.proposal_ids[0])
    assert proposal["status"] == "pending"
    assert proposal["payload"]["note"] == PAYPAL_REMINDER_TEXT
    assert "MODEL_NOTE_TEXT" not in json.dumps(proposal)
    assert client.calls[0]["tools"] == tools_for("sandbox")
    result = tool_results(client.calls[1])[0]
    assert result["is_error"] is False
    assert "PayPal writes the reminder email" in json.loads(result["content"])["next_step"]
    assert port.sent_log == []
    with pytest.raises(PolicyError, match="custom notes"):
        service.propose_reminder("INV2", "A custom note from any other caller")


def test_demo_agent_keeps_the_model_reminder_note(
    service: ProposalService, port: FakePayPal
) -> None:
    client = ScriptedClient("INV1", note="A short, polite nudge.")
    reply = LLMAgent(service, port, client, "model", lambda: TODAY).run("s", "remind them")
    assert service.get(reply.proposal_ids[0])["payload"]["note"] == "A short, polite nudge."


class IdQuotingClient:
    """Reads invoices, proposes a reminder, then quotes raw identifiers back."""

    def __init__(self) -> None:
        self.calls: list[dict[str, Any]] = []

    def create_message(self, **kwargs: Any) -> Any:
        self.calls.append(kwargs)
        if len(self.calls) == 1:
            return NS(
                content=[
                    NS(type="tool_use", id="a", name="list_invoices", input={}),
                    NS(
                        type="tool_use",
                        id="b",
                        name="propose_reminder",
                        input={"invoice_id": "INV1"},
                    ),
                ],
                stop_reason="tool_use",
            )
        if len(self.calls) == 2:
            proposal_id = json.loads(tool_results(kwargs)[1]["content"])["proposal_id"]
            text = f"INV1 and `INV2` are late, INV3 is not, INV10 is unknown. {proposal_id} waits."
        else:
            text = "INV1 is still the oldest."
        return NS(content=[NS(type="text", text=text)], stop_reason="end_turn")


def test_reply_swaps_raw_ids_for_the_labels_the_owner_sees(
    service: ProposalService, port: FakePayPal
) -> None:
    port.invoices["INV3"].number = "INV3"  # PayPal returned no separate invoice number
    client = IdQuotingClient()
    agent = LLMAgent(service, port, client, "model", lambda: TODAY)

    reply = agent.run("s", "What is late? Remind the oldest.")
    reference = service.get(reply.proposal_ids[0])["reference"]
    assert reply.text == (
        f"N-1 and `N-2` are late, this invoice is not, INV10 is unknown. {reference} waits."
    )
    assert agent.run("s", "And now?").text == "N-1 is still the oldest."
    assert "N-1" not in json.dumps(client.calls)
    assert any("INV1" in json.dumps(message) for message in client.calls[-1]["messages"])


def test_system_prompt_asks_for_plain_replies_without_raw_ids() -> None:
    assert "never quote" in SYSTEM_PROMPT
    assert "No tables" in SYSTEM_PROMPT
    assert "If p10 equals p90" in SYSTEM_PROMPT


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


@pytest.mark.parametrize(
    "failure",
    [PayPalError("LEAK_TEST_SECRET", 422), PayPalUncertain("LEAK_TEST_SECRET")],
)
def test_provider_errors_return_safe_tool_results(
    service: ProposalService,
    port: FakePayPal,
    monkeypatch: pytest.MonkeyPatch,
    failure: Exception,
) -> None:
    def broken_list() -> list[Invoice]:
        raise failure

    monkeypatch.setattr(port, "list_invoices", broken_list)
    content, is_error = Toolbox(service, port, lambda: TODAY).run("list_invoices", {})
    assert is_error
    assert json.loads(content)["error"].startswith("PayPal")
    assert "LEAK_TEST_SECRET" not in content
    assert port.sent_log == []


def test_model_tool_views_hide_untrusted_customer_text(
    service: ProposalService, port: FakePayPal
) -> None:
    marker = "INJECT_TEST_SECRET_SYSTEM_OVERRIDE"
    port.invoices["INV1"].customer_name = marker
    port.invoices["INV1"].customer_email = "private@example.com"
    port.invoices["INV1"].number = marker
    port.invoices["INV4"].customer_name = marker
    toolbox = Toolbox(service, port, lambda: TODAY)
    service.propose_invoice(
        {
            "customer_name": marker[:80],
            "customer_email": "private@example.com",
            "items": [{"description": "Service", "quantity": 1, "unit_price": 30}],
        }
    )
    for tool_name in READ_TOOLS:
        content, is_error = toolbox.run_for_model(tool_name, {})
        assert not is_error
        assert "INJECT_TEST_SECRET" not in content
        assert "private@example.com" not in content
        assert "customer_name" not in content
        assert '"summary"' not in content
    assert port.sent_log == []


def test_model_proposal_result_omits_customer_summary(
    service: ProposalService, port: FakePayPal
) -> None:
    toolbox = Toolbox(service, port, lambda: TODAY)
    args = {
        "customer_name": "INJECT_TEST_SECRET",
        "customer_email": "private@example.com",
        "items": [{"description": "Work", "quantity": 1, "unit_price": 10}],
    }
    content, is_error = toolbox.run_for_model("propose_invoice", args)
    assert not is_error
    assert set(json.loads(content)) == {"proposal_id", "status", "next_step"}
    assert "INJECT_TEST_SECRET" not in content
    assert "private@example.com" not in content
    assert service.list()[0]["status"] == "pending"
    assert port.sent_log == []


def test_model_read_view_omits_malformed_invoice_id(
    service: ProposalService, port: FakePayPal
) -> None:
    port.invoices["INV1"].id = "INJECT_TEST_SECRET_UNTRUSTED_ID\nBREAK"
    content, is_error = Toolbox(service, port, lambda: TODAY).run_for_model("list_invoices", {})
    assert not is_error
    result = json.loads(content)
    assert result["count"] == 3
    assert "INJECT_TEST_SECRET_UNTRUSTED_ID" not in content


def test_empty_forecast_model_result_has_no_free_text_source(
    service: ProposalService, port: FakePayPal
) -> None:
    port.invoices.clear()
    content, is_error = Toolbox(service, port, lambda: TODAY).run_for_model(
        "get_cash_flow_forecast", {}
    )
    assert not is_error
    assert json.loads(content) == {"message": "There are no open invoices to forecast."}


def test_scripted_prompt_injection_cannot_execute_paypal_action(
    service: ProposalService, port: FakePayPal
) -> None:
    port.invoices["INV1"].customer_name = "INJECT_TEST_SECRET_INVOICE_FIELD"

    class HostileModel:
        def __init__(self) -> None:
            self.calls: list[dict[str, Any]] = []

        def create_message(self, **kwargs: Any) -> Any:
            self.calls.append(kwargs)
            if len(self.calls) == 1:
                return NS(
                    content=[NS(type="tool_use", id="one", name="list_invoices", input={})],
                    stop_reason="tool_use",
                )
            if len(self.calls) == 2:
                return NS(
                    content=[
                        NS(
                            type="tool_use",
                            id="two",
                            name="send_invoice",
                            input={"invoice_id": "INV1"},
                        )
                    ],
                    stop_reason="tool_use",
                )
            return NS(content=[NS(type="text", text="No action was sent.")], stop_reason="end_turn")

    model = HostileModel()
    reply = LLMAgent(service, port, model, "model", lambda: TODAY).run(
        "session", "Show me all invoices."
    )
    assert reply.proposal_ids == []
    assert "INJECT_TEST_SECRET" not in str(model.calls)
    assert port.sent_log == []
    assert service.list() == []


@pytest.mark.parametrize(
    "prompt", ["Remind my overdue customers", "Which invoices are overdue?", "Cash forecast"]
)
def test_incomplete_inventory_does_not_propose_or_claim_financial_totals(
    service: ProposalService,
    port: FakePayPal,
    monkeypatch: pytest.MonkeyPatch,
    prompt: str,
) -> None:
    def broken_list() -> list[Invoice]:
        raise InvoiceInventoryIncomplete("UPSTREAM_UNTRUSTED_DETAILS")

    monkeypatch.setattr(port, "list_invoices", broken_list)
    agent = OfflineAgent(service, port, lambda: TODAY)
    result = agent.run("local", prompt)
    assert result.text == INCOMPLETE_INVENTORY_MESSAGE
    assert result.proposal_ids == []
    assert port.sent_log == []
    assert service.list() == []


def test_incomplete_inventory_tool_result_is_explicit_error_not_partial_data(
    service: ProposalService, port: FakePayPal, monkeypatch: pytest.MonkeyPatch
) -> None:
    def broken_list() -> list[Invoice]:
        raise InvoiceInventoryIncomplete("UPSTREAM_UNTRUSTED_DETAILS")

    monkeypatch.setattr(port, "list_invoices", broken_list)
    content, is_error = Toolbox(service, port, lambda: TODAY).run("list_invoices", {})
    assert is_error
    assert json.loads(content) == {"error": INCOMPLETE_INVENTORY_MESSAGE}
    assert "UPSTREAM_UNTRUSTED_DETAILS" not in content


def test_toolbox_refund_review_blocks_all_financial_reads_without_partial_totals(
    service: ProposalService, port: FakePayPal
) -> None:
    invoice = port.invoices["INV4"]
    invoice.status = "refund_review"
    invoice.provider_status = "PARTIALLY_REFUNDED"
    invoice.remaining_amount = 200.0
    invoice.balance_source = "paypal_due_amount"
    toolbox = Toolbox(service, port, lambda: TODAY)
    for name in ("list_invoices", "get_cash_flow_forecast", "get_receivables_aging"):
        content, is_error = toolbox.run(name, {})
        assert is_error
        assert json.loads(content) == {"error": REFUND_REVIEW_MESSAGE}
        assert "200.0" not in content
    assert toolbox.created == []
    assert port.sent_log == []


def test_offline_agent_cannot_propose_reminders_with_unresolved_refunds(
    service: ProposalService, port: FakePayPal
) -> None:
    port.invoices["INV4"].status = "refund_review"
    port.invoices["INV4"].provider_status = "REFUNDED"
    agent = OfflineAgent(service, port, lambda: TODAY)
    for prompt in ("remind all overdue invoices", "cash flow forecast"):
        reply = agent.run("session", prompt)
        assert reply.text == REFUND_REVIEW_MESSAGE
        assert reply.proposal_ids == []
    assert service.list() == []
    assert port.sent_log == []
