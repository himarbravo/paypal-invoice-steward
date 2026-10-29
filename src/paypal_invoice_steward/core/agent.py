"""The agent: Claude with tools that can read and propose, never execute.

There is deliberately no tool here that sends an invoice, sends a reminder, or
moves money. The strongest thing the model can do is create a proposal, which a
person must confirm in the interface. Policy limits live in ProposalService, so
they hold even if the model misbehaves.
"""

from __future__ import annotations

import json
import re
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import date
from typing import Any

from .forecast import forecast
from .models import JSON
from .ports import LLMClient, PayPalError, PayPalPort, PayPalUncertain
from .proposals import ProposalError, ProposalService

Today = Callable[[], date]

READ_TOOLS = ("list_invoices", "get_cash_flow_forecast", "list_proposals")
PROPOSE_TOOLS = ("propose_invoice", "propose_reminder")

SYSTEM_PROMPT = """\
You are Invoice Steward, an assistant that helps a freelancer or small business get paid on time.
You work with their PayPal invoices: you can look at them, forecast when the money will arrive,
and prepare invoices and payment reminders for the owner to approve.

How you work:
- You cannot send, charge, or change anything. Your propose_* tools only create a proposal,
  shown to the owner as a card they must confirm. After proposing, say what you prepared and
  ask them to review and confirm it. Never say something was sent unless a tool result shows
  a proposal with status "done".
- If a proposal is "unverified", say plainly that the outcome is unknown and that they can
  press Verify. Never call an unverified proposal failed.
- Use figures only from tool results. When you quote the forecast, give the range (p10 to p90),
  not just the expected value, and name the invoices that drive the risk.
- If a tool returns an error, explain it simply and say what the owner can do instead.
- Reminders: only for open invoices that are overdue or due within 3 days. Keep reminder notes
  polite and short. Do not write threats or mention legal action.
- Answer in the language the owner writes in. Be concise: a few short sentences or a short list.
"""

TOOLS: list[dict[str, Any]] = [
    {
        "name": "list_invoices",
        "description": (
            "List the owner's PayPal invoices. Use status 'overdue' for late open invoices."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "status": {"type": "string", "enum": ["all", "open", "overdue", "paid", "draft"]},
            },
        },
    },
    {
        "name": "get_cash_flow_forecast",
        "description": (
            "Forecast when open invoices will be paid: expected weekly inflow with p10 to p90 "
            "range, "
            "per-invoice chance of payment within 30 days, and each customer's payment habit."
        ),
        "input_schema": {"type": "object", "properties": {}},
    },
    {
        "name": "list_proposals",
        "description": (
            "List proposals and their status (pending, done, unverified, failed, dismissed)."
        ),
        "input_schema": {"type": "object", "properties": {}},
    },
    {
        "name": "propose_invoice",
        "description": (
            "Prepare a new invoice for the owner to approve. "
            "Nothing is created or sent until they confirm."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "customer_name": {"type": "string"},
                "customer_email": {"type": "string"},
                "items": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "description": {"type": "string"},
                            "quantity": {"type": "integer"},
                            "unit_price": {"type": "number"},
                        },
                        "required": ["description", "unit_price"],
                    },
                },
                "currency": {"type": "string", "enum": ["EUR", "USD", "GBP"]},
                "due_days": {
                    "type": "integer",
                    "description": "Days until payment is due (1 to 90).",
                },
                "note": {"type": "string"},
            },
            "required": ["customer_name", "customer_email", "items"],
        },
    },
    {
        "name": "propose_reminder",
        "description": (
            "Prepare a payment reminder for one open invoice, for the owner to approve. "
            "Nothing is sent until they confirm."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "invoice_id": {
                    "type": "string",
                    "description": "The invoice id from list_invoices.",
                },
                "note": {
                    "type": "string",
                    "description": "Optional custom message. Polite and short.",
                },
            },
            "required": ["invoice_id"],
        },
    },
]


@dataclass
class AgentReply:
    text: str
    proposal_ids: list[str] = field(default_factory=list)


class Toolbox:
    """Runs tool calls. Collects the ids of proposals created along the way."""

    def __init__(self, service: ProposalService, port: PayPalPort, today: Today) -> None:
        self.service = service
        self.port = port
        self.today = today
        self.created: list[str] = []

    def run(self, name: str, args: JSON) -> tuple[str, bool]:
        """Return (json text for the model, is_error)."""
        try:
            return json.dumps(self._dispatch(name, args), default=str), False
        except ProposalError as exc:
            return json.dumps({"error": str(exc)}), True
        except (PayPalError, PayPalUncertain) as exc:
            return json.dumps({"error": f"PayPal problem: {exc}"}), True
        except (KeyError, TypeError, ValueError, AttributeError):
            return json.dumps({"error": "Invalid tool input."}), True

    def _dispatch(self, name: str, args: JSON) -> Any:
        today = self.today()
        if name == "list_invoices":
            wanted = args.get("status", "all")
            rows: list[JSON] = []
            for inv in self.port.list_invoices():
                late = inv.days_overdue(today)
                if wanted == "overdue" and late == 0:
                    continue
                if wanted in ("open", "paid", "draft") and inv.status != wanted:
                    continue
                rows.append(
                    {
                        "id": inv.id,
                        "number": inv.number,
                        "customer": inv.customer_name,
                        "amount": inv.amount,
                        "currency": inv.currency,
                        "status": inv.status,
                        "due": inv.due.isoformat(),
                        "days_overdue": late,
                    }
                )
            rows.sort(key=lambda r: (-r["days_overdue"], r["number"]))
            return {"count": len(rows), "invoices": rows[:40]}
        if name == "get_cash_flow_forecast":
            result = forecast(self.port.list_invoices(), today)
            return result or {"message": "There are no open invoices to forecast."}
        if name == "list_proposals":
            return {
                "proposals": [
                    {
                        "id": p["id"],
                        "summary": p["summary"],
                        "status": p["status"],
                        "error": p["error"],
                    }
                    for p in self.service.list()[:20]
                ]
            }
        if name == "propose_invoice":
            proposal = self.service.propose_invoice(args)
        elif name == "propose_reminder":
            proposal = self.service.propose_reminder(args["invoice_id"], args.get("note"))
        else:
            raise ValueError("unknown tool")
        if proposal["id"] not in self.created:
            self.created.append(proposal["id"])
        return {
            "proposal_id": proposal["id"],
            "status": proposal["status"],
            "summary": proposal["summary"],
            "next_step": "Waiting for the owner to review and confirm it in the interface.",
        }


def _trim(history: list[JSON], keep_turns: int = 6) -> list[JSON]:
    """Keep the last few user turns, never cutting between a tool call and its result."""
    starts = [
        i for i, m in enumerate(history) if m["role"] == "user" and isinstance(m["content"], str)
    ]
    if len(starts) <= keep_turns:
        return history
    return history[starts[-keep_turns] :]


class LLMAgent:
    mode = "claude"

    def __init__(
        self,
        service: ProposalService,
        port: PayPalPort,
        client: LLMClient,
        model: str,
        today: Today,
        max_steps: int = 8,
    ) -> None:
        self.service, self.port, self.client, self.model = service, port, client, model
        self.today = today
        self.max_steps = max_steps
        self._history: dict[str, list[JSON]] = {}

    def run(self, session_id: str, user_text: str) -> AgentReply:
        history = self._history.setdefault(session_id, [])
        history.append({"role": "user", "content": user_text})
        toolbox = Toolbox(self.service, self.port, self.today)
        text = ""
        for _ in range(self.max_steps):
            response = self.client.create_message(
                model=self.model,
                max_tokens=1024,
                system=SYSTEM_PROMPT,
                tools=TOOLS,
                messages=_trim(history),
            )
            blocks, calls, text_parts = [], [], []
            for block in response.content:
                if block.type == "text":
                    blocks.append({"type": "text", "text": block.text})
                    text_parts.append(block.text)
                elif block.type == "tool_use":
                    blocks.append(
                        {
                            "type": "tool_use",
                            "id": block.id,
                            "name": block.name,
                            "input": block.input,
                        }
                    )
                    calls.append(block)
            history.append({"role": "assistant", "content": blocks})
            text = "\n".join(text_parts).strip()
            if response.stop_reason != "tool_use" or not calls:
                break
            results = []
            for call in calls:
                content, is_error = toolbox.run(call.name, dict(call.input or {}))
                results.append(
                    {
                        "type": "tool_result",
                        "tool_use_id": call.id,
                        "content": content,
                        "is_error": is_error,
                    }
                )
            history.append({"role": "user", "content": results})
        else:
            text = text or "I could not finish that request. Try asking in smaller steps."
        self._history[session_id] = _trim(history, keep_turns=6)
        return AgentReply(text=text or "Done.", proposal_ids=toolbox.created)


class OfflineAgent:
    """A small rule-based stand-in used when there is no Anthropic API key.

    It exists so the app can be explored end to end without a key. It uses the
    same tools and the same proposal safeguards as the Claude agent.
    """

    mode = "offline"
    _NUMBER = re.compile(r"INV-\d{4}-\d{3}", re.I)
    _EMAIL = re.compile(r"[\w.+-]+@[\w-]+\.[\w.-]+")
    _AMOUNT = re.compile(r"(\d+(?:[.,]\d{1,2})?)\s*(eur|usd|gbp|€|\$|£)?", re.I)

    def __init__(self, service: ProposalService, port: PayPalPort, today: Today) -> None:
        self.service, self.port, self.today = service, port, today

    def run(self, session_id: str, user_text: str) -> AgentReply:
        toolbox = Toolbox(self.service, self.port, self.today)
        text = user_text.lower()

        if self._EMAIL.search(user_text) and re.search(r"invoice|factura", text):
            return self._invoice(toolbox, user_text)
        if re.search(r"remind|recuerd|recordatorio", text):
            return self._reminders(toolbox, user_text)
        if re.search(r"forecast|cash|previs|flujo", text):
            return self._forecast(toolbox)
        if re.search(r"overdue|late|vencid|atrasad|retras", text):
            return self._overdue(toolbox)
        return AgentReply(
            "Offline demo mode (no ANTHROPIC_API_KEY). Try: "
            '"cash flow forecast", "which invoices are overdue", "remind all overdue", or '
            '"invoice Alba Design Studio billing@albadesign.example 450 EUR for logo refresh".'
        )

    def _forecast(self, toolbox: Toolbox) -> AgentReply:
        data = json.loads(toolbox.run("get_cash_flow_forecast", {})[0])
        if "message" in data:
            return AgentReply(data["message"])
        lines = []
        for currency, f in data.items():
            total = f["total"]
            lines.append(
                f"Next 8 weeks ({currency}): expect {total['expected']:,.0f}, likely between "
                f"{total['p10']:,.0f} and {total['p90']:,.0f}, out of {f['open_amount']:,.0f} open."
            )
            risky = [r for r in f["invoices"] if r["risk"] == "high"]
            for r in risky:
                lines.append(
                    f"At risk: {r['number']} from {r['customer']} ({r['amount']:,.0f}), "
                    f"{r['days_overdue']} days overdue, "
                    f"{r['p_paid_30d']:.0%} chance of payment within 30 days."
                )
        return AgentReply("\n".join(lines))

    def _overdue(self, toolbox: Toolbox) -> AgentReply:
        data = json.loads(toolbox.run("list_invoices", {"status": "overdue"})[0])
        if not data["invoices"]:
            return AgentReply("No invoices are overdue.")
        lines = [f"{data['count']} overdue invoices:"]
        lines += [
            f"{r['number']}  {r['customer']}  {r['amount']:,.0f} {r['currency']}  "
            f"{r['days_overdue']} days late"
            for r in data["invoices"]
        ]
        return AgentReply("\n".join(lines))

    def _reminders(self, toolbox: Toolbox, user_text: str) -> AgentReply:
        invoices = json.loads(toolbox.run("list_invoices", {"status": "open"})[0])["invoices"]
        wanted = {m.upper() for m in self._NUMBER.findall(user_text)}
        targets = (
            [r for r in invoices if r["number"] in wanted]
            if wanted
            else [r for r in invoices if r["days_overdue"] > 0]
        )
        if not targets:
            return AgentReply("I found no matching open invoices to remind.")
        prepared, skipped = [], []
        for row in targets:
            content, is_error = toolbox.run("propose_reminder", {"invoice_id": row["id"]})
            if is_error:
                skipped.append(f"{row['number']}: {json.loads(content)['error']}")
            else:
                prepared.append(row["number"])
        lines = []
        if prepared:
            lines.append(
                f"Prepared {len(prepared)} reminder(s): {', '.join(prepared)}. "
                "Review and confirm each card; nothing is sent until you do."
            )
        lines += skipped
        return AgentReply("\n".join(lines), toolbox.created)

    def _invoice(self, toolbox: Toolbox, user_text: str) -> AgentReply:
        email_match = self._EMAIL.search(user_text)
        if email_match is None:
            return AgentReply("Include the customer's email address in the request.")
        email = email_match.group(0)
        before_email = user_text[: user_text.index(email)]
        name = re.sub(
            r"(?i)^.*?\b(?:invoice|factura)\b\s*(?:\b(?:to|for|a|para)\b\s+)?", "", before_email
        ).strip(" ,:")
        name = name or email.split("@")[0].replace(".", " ").title()
        after = user_text[user_text.index(email) + len(email) :]
        amount_match = self._AMOUNT.search(after)
        if not amount_match:
            return AgentReply(
                "Tell me the amount too, for example: "
                "invoice Acme billing@acme.example 450 EUR for design work."
            )
        amount = float(amount_match.group(1).replace(",", "."))
        symbol = (amount_match.group(2) or "EUR").upper()
        currency = {"€": "EUR", "$": "USD", "£": "GBP"}.get(symbol, symbol)
        desc_match = re.search(r"(?i)\b(?:for|por|de)\b\s+(.+)$", after)
        description = desc_match.group(1).strip(" .") if desc_match else "Services"
        description = re.sub(r"(?i)^(?:a|an|the|un|una|el|la)\s+", "", description) or "Services"
        description = description[:1].upper() + description[1:]
        content, is_error = toolbox.run(
            "propose_invoice",
            {
                "customer_name": name,
                "customer_email": email,
                "currency": currency,
                "items": [{"description": description, "quantity": 1, "unit_price": amount}],
            },
        )
        if is_error:
            return AgentReply(f"I could not prepare that invoice: {json.loads(content)['error']}")
        return AgentReply(
            "Invoice prepared. Review the card and confirm it to create and send it.",
            toolbox.created,
        )
