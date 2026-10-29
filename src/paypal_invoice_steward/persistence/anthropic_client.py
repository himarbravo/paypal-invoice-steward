"""`core.ports.LLMClient` backed by the Anthropic SDK (Claude)."""

from __future__ import annotations

from typing import Any

import anthropic


class AnthropicClient:
    """Thin adapter so `core` never imports the Anthropic SDK."""

    def __init__(self, api_key: str, client: anthropic.Anthropic | None = None) -> None:
        self._client = client or anthropic.Anthropic(api_key=api_key)

    def create_message(self, **kwargs: Any) -> Any:
        return self._client.messages.create(**kwargs)
