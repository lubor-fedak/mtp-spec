"""Anthropic (Claude) adapter for MTP execution."""

from __future__ import annotations

import os

from mtp_run.adapters import BaseAdapter, StepResult
from mtp_run.response_parser import parse_step_response


class AnthropicAdapter(BaseAdapter):
    """Execute MTP steps via the Anthropic Messages API (Claude).

    Requires:
        - ANTHROPIC_API_KEY environment variable
        - pip install mtp-run[anthropic]
    """

    name = "anthropic"

    def __init__(self, model: str = "claude-sonnet-4-20250514", max_tokens: int = 4096):
        self._model = model
        self._max_tokens = max_tokens
        self._client = None

    def _get_client(self):
        if self._client is None:
            try:
                import anthropic
            except ImportError:
                raise ImportError(
                    "Anthropic SDK not installed. Run: pip install mtp-run[anthropic]"
                )
            self._client = anthropic.Anthropic()
        return self._client

    def execute_step(
        self,
        system_context: str,
        step_prompt: str,
        data: str,
    ) -> StepResult:
        client = self._get_client()

        user_content = f"{step_prompt}\n\n{data}"

        response = client.messages.create(
            model=self._model,
            max_tokens=self._max_tokens,
            system=system_context,
            messages=[{"role": "user", "content": user_content}],
        )

        raw = response.content[0].text if response.content else ""
        return parse_step_response(raw)

    def is_available(self) -> bool:
        return bool(os.environ.get("ANTHROPIC_API_KEY"))

    def platform_id(self) -> str:
        return f"anthropic/{self._model}"
