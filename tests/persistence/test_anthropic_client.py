from types import SimpleNamespace as NS
from typing import Any

from paypal_invoice_steward.core.ports import LLMClient
from paypal_invoice_steward.persistence.anthropic_client import AnthropicClient


def test_forwards_requests_to_the_sdk() -> None:
    seen: dict[str, Any] = {}

    def create(**kwargs: Any) -> str:
        seen.update(kwargs)
        return "response"

    fake_sdk: Any = NS(messages=NS(create=create))
    client: LLMClient = AnthropicClient("key", client=fake_sdk)
    assert client.create_message(model="m", max_tokens=5) == "response"
    assert seen == {"model": "m", "max_tokens": 5}
