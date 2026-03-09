"""OpenAI / Azure OpenAI adapter for MTP execution."""

from __future__ import annotations

import os

from mtp_run.adapters import BaseAdapter, StepResult
from mtp_run.response_parser import parse_step_response


class OpenAIAdapter(BaseAdapter):
    """Execute MTP steps via the OpenAI Chat Completions API.

    Works with both OpenAI and Azure OpenAI.

    OpenAI requires:
        - OPENAI_API_KEY environment variable
        - pip install mtp-run[openai]

    Azure OpenAI requires:
        - AZURE_OPENAI_API_KEY environment variable
        - AZURE_OPENAI_ENDPOINT environment variable
        - AZURE_OPENAI_API_VERSION environment variable (default: 2024-10-21)
    """

    name = "openai"

    def __init__(
        self,
        model: str = "gpt-4o",
        max_tokens: int = 4096,
        azure: bool = False,
    ):
        self._model = model
        self._max_tokens = max_tokens
        self._azure = azure
        self._client = None

    def _get_client(self):
        if self._client is None:
            try:
                import openai
            except ImportError:
                raise ImportError(
                    "OpenAI SDK not installed. Run: pip install mtp-run[openai]"
                )

            if self._azure:
                self._client = openai.AzureOpenAI(
                    api_key=os.environ.get("AZURE_OPENAI_API_KEY"),
                    azure_endpoint=os.environ.get("AZURE_OPENAI_ENDPOINT", ""),
                    api_version=os.environ.get("AZURE_OPENAI_API_VERSION", "2024-10-21"),
                )
            else:
                self._client = openai.OpenAI()
        return self._client

    def execute_step(
        self,
        system_context: str,
        step_prompt: str,
        data: str,
    ) -> StepResult:
        client = self._get_client()

        user_content = f"{step_prompt}\n\n{data}"

        response = client.chat.completions.create(
            model=self._model,
            max_tokens=self._max_tokens,
            messages=[
                {"role": "system", "content": system_context},
                {"role": "user", "content": user_content},
            ],
        )

        raw = response.choices[0].message.content if response.choices else ""
        return parse_step_response(raw)

    def is_available(self) -> bool:
        if self._azure:
            return bool(
                os.environ.get("AZURE_OPENAI_API_KEY")
                and os.environ.get("AZURE_OPENAI_ENDPOINT")
            )
        return bool(os.environ.get("OPENAI_API_KEY"))

    def platform_id(self) -> str:
        prefix = "azure-openai" if self._azure else "openai"
        return f"{prefix}/{self._model}"
