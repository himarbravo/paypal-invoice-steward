"""The web app: a small JSON API plus a single-page interface."""

from __future__ import annotations

import logging
from collections.abc import Awaitable, Callable
from datetime import date
from ipaddress import ip_address
from pathlib import Path
from typing import Literal, Protocol
from urllib.parse import urlsplit

from fastapi import FastAPI, Query, Request
from fastapi.responses import FileResponse, JSONResponse, Response
from pydantic import BaseModel, Field

from .. import __version__
from ..core.agent import AgentReply, LLMAgent, OfflineAgent
from ..core.forecast import forecast
from ..core.models import JSON
from ..core.ports import PayPalError, PayPalPort, PayPalUncertain
from ..core.proposals import ProposalError, ProposalService
from ..persistence.anthropic_client import AnthropicClient
from ..persistence.paypal_demo import DemoPayPal
from ..persistence.paypal_sandbox import SandboxPayPal
from ..persistence.store import SqliteProposalStore
from .config import Settings, load_settings

log = logging.getLogger("paypal_invoice_steward")
STATIC = Path(__file__).parent / "static"


# Deliberate local-only hackathon threat boundary (not user authentication).
# The synthetic TestClient address/Host pairing exists only in in-process tests.
def _is_local_request(request: Request) -> bool:
    peer = request.client.host if request.client is not None else ""
    try:
        host = urlsplit("http://" + request.headers.get("host", "")).hostname
    except ValueError:
        return False
    if not (peer == "testclient" and host == "testserver"):
        if host not in {"localhost", "127.0.0.1", "::1"}:
            return False
        try:
            if not ip_address(peer).is_loopback:
                return False
        except ValueError:
            return False
    origin = request.headers.get("origin")
    if request.method not in {"GET", "HEAD", "OPTIONS"} and origin:
        try:
            parsed = urlsplit(origin)
            if parsed.scheme != request.url.scheme or parsed.netloc != request.headers.get("host"):
                return False
        except ValueError:
            return False
    return True


class ChatIn(BaseModel):
    session_id: str = Field(default="default", max_length=64)
    message: str = Field(min_length=1, max_length=2000)


class ConfirmIn(BaseModel):
    payload_hash: str = Field(min_length=1, max_length=64)


class FailNextIn(BaseModel):
    mode: Literal["timeout_after_send", "reject"] | None = None


class Assistant(Protocol):
    """Anything that answers chat messages: `LLMAgent` or `OfflineAgent`."""

    mode: str

    def run(self, session_id: str, user_text: str) -> AgentReply: ...


def build_port(settings: Settings, today: Callable[[], date]) -> PayPalPort:
    """The real sandbox when credentials are set, otherwise the demo."""
    if settings.mode == "sandbox":
        if not settings.paypal_client_id or not settings.paypal_client_secret:
            raise ValueError("Sandbox mode requires both PayPal credentials.")
        return SandboxPayPal(
            settings.paypal_client_id,
            settings.paypal_client_secret,
            settings.paypal_base_url,
            today=today,
        )
    if settings.mode == "demo":
        return DemoPayPal(today=today)
    raise ValueError("Only demo and sandbox modes are supported.")


def create_app(
    settings: Settings | None = None,
    port: PayPalPort | None = None,
    agent: Assistant | None = None,
    today: Callable[[], date] = date.today,
) -> FastAPI:
    """Wire settings, PayPal backend, store and assistant into a FastAPI app."""
    settings = settings or load_settings()
    port = port or build_port(settings, today)
    store = SqliteProposalStore(settings.db_path)
    service = ProposalService(port, store, settings.policy, today)
    if agent is None:
        if settings.anthropic_api_key:
            agent = LLMAgent(
                service,
                port,
                AnthropicClient(settings.anthropic_api_key),
                settings.anthropic_model,
                today,
            )
        else:
            agent = OfflineAgent(service, port, today)
    assistant: Assistant = agent

    app = FastAPI(title="PayPal Invoice Steward", version=__version__)
    app.state.service, app.state.port, app.state.agent = service, port, assistant

    @app.middleware("http")
    async def _local_only(
        request: Request, call_next: Callable[[Request], Awaitable[Response]]
    ) -> Response:
        if not _is_local_request(request):
            return JSONResponse(
                {"error": "This hackathon demo only accepts direct local browser requests."},
                status_code=403,
            )
        return await call_next(request)

    @app.exception_handler(ProposalError)
    async def _proposal_error(_: Request, exc: ProposalError) -> JSONResponse:
        return JSONResponse({"error": str(exc)}, status_code=exc.status_code)

    @app.exception_handler(PayPalError)
    async def _paypal_error(_: Request, exc: PayPalError) -> JSONResponse:
        return JSONResponse({"error": f"PayPal refused the request: {exc}"}, status_code=502)

    @app.exception_handler(PayPalUncertain)
    async def _paypal_uncertain(_: Request, exc: PayPalUncertain) -> JSONResponse:
        return JSONResponse({"error": f"PayPal did not answer: {exc}"}, status_code=502)

    @app.get("/", response_model=None)
    def index() -> FileResponse:
        return FileResponse(STATIC / "index.html")

    @app.get("/api/health")
    def health() -> JSON:
        return {
            "mode": port.mode,
            "outbound_actions_enabled": (
                port.mode != "sandbox" or settings.sandbox_writes_enabled
            ),
            "agent": assistant.mode,
            "model": settings.anthropic_model if isinstance(assistant, LLMAgent) else None,
            "today": today().isoformat(),
            "max_invoice_amount": settings.max_invoice_amount,
        }

    @app.get("/api/invoices")
    def invoices() -> JSON:
        now = today()
        rows = [inv.to_dict(now) for inv in port.list_invoices()]
        rows.sort(key=lambda r: (r["status"] != "open", -r["days_overdue"], r["due"]))
        return {"invoices": rows}

    @app.get("/api/forecast")
    def get_forecast() -> JSON:
        return {"forecasts": forecast(port.list_invoices(), today())}

    @app.get("/api/proposals")
    def proposals(status: str | None = Query(default=None)) -> JSON:
        statuses = [s for s in status.split(",") if s] if status else None
        return {"proposals": service.list(statuses)}

    @app.get("/api/proposals/{proposal_id}")
    def proposal(proposal_id: str) -> JSON:
        return service.get(proposal_id)

    @app.post("/api/chat", response_model=None)
    def chat(body: ChatIn) -> JSON | JSONResponse:
        try:
            reply = assistant.run(body.session_id, body.message.strip())
        except Exception:  # never leak provider errors to the page
            log.exception("agent failed")
            return JSONResponse(
                {"error": "The assistant is unavailable right now. Try again in a moment."},
                status_code=502,
            )
        return {
            "reply": reply.text,
            "proposals": [service.get(pid) for pid in reply.proposal_ids],
        }

    @app.post("/api/proposals/{proposal_id}/confirm")
    def confirm(proposal_id: str, body: ConfirmIn) -> JSON:
        return service.confirm(proposal_id, body.payload_hash)

    @app.post("/api/proposals/{proposal_id}/dismiss")
    def dismiss(proposal_id: str) -> JSON:
        return service.dismiss(proposal_id)

    @app.post("/api/proposals/{proposal_id}/verify")
    def verify(proposal_id: str) -> JSON:
        return service.verify(proposal_id)

    @app.post("/api/demo/fail-next", response_model=None)
    def fail_next(body: FailNextIn) -> JSON | JSONResponse:
        if not isinstance(port, DemoPayPal):
            return JSONResponse(
                {"error": "Failure simulation only exists in demo mode."}, status_code=404
            )
        port.fail_next = body.mode
        return {"fail_next": port.fail_next}

    return app
