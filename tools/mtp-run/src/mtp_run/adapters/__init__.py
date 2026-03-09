"""Abstract base adapter and registry for LLM connections."""

from __future__ import annotations

import importlib.util
import os
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any


@dataclass
class StepResult:
    """Structured result from executing a single MTP step."""
    state: str  # success | partial | deviation | failure | escalated | skipped
    validation_result: str  # pass | fail | not_applicable
    output: str  # the actual output/work product of the step
    deviation_description: str = ""
    deviation_reason: str = ""
    failure_reason: str = ""
    notes: str = ""
    edge_cases_encountered: list[dict] = field(default_factory=list)
    novel_situations: list[dict] = field(default_factory=list)
    dead_ends_considered: list[dict] = field(default_factory=list)
    dead_ends_repeated: list[dict] = field(default_factory=list)
    raw_response: str = ""  # full LLM response for debugging

    def to_dict(self) -> dict:
        d = {
            "state": self.state,
            "validation_result": self.validation_result,
            "output": self.output,
            "notes": self.notes,
        }
        if self.state == "deviation":
            d["deviation"] = {
                "description": self.deviation_description,
                "reason": self.deviation_reason,
            }
        if self.state == "failure":
            d["failure_reason"] = self.failure_reason
        if self.edge_cases_encountered:
            d["edge_cases_encountered"] = self.edge_cases_encountered
        if self.novel_situations:
            d["novel_situations"] = self.novel_situations
        if self.dead_ends_considered:
            d["dead_ends_considered"] = self.dead_ends_considered
        if self.dead_ends_repeated:
            d["dead_ends_repeated"] = self.dead_ends_repeated
        return d


class BaseAdapter(ABC):
    """Abstract base class for LLM adapters.

    An adapter translates MTP step execution into LLM API calls
    and parses structured responses.
    """

    name: str = "base"

    @abstractmethod
    def execute_step(
        self,
        system_context: str,
        step_prompt: str,
        data: str,
    ) -> StepResult:
        """Execute a single methodology step via the LLM.

        Args:
            system_context: Methodology-level context (intent, approach, dead ends)
            step_prompt: Step-specific prompt (action, validation, edge cases)
            data: The actual data to process

        Returns:
            StepResult with structured execution outcome
        """
        ...

    @abstractmethod
    def is_available(self) -> bool:
        """Check if this adapter is configured and ready."""
        ...

    def platform_id(self) -> str:
        """Return a platform identifier for execution reports."""
        return self.name


@dataclass(frozen=True)
class AdapterStatus:
    """Runtime availability summary for a configured adapter surface."""

    name: str
    variant: str
    status: str
    platform: str
    notes: str


def _sdk_available(module_name: str) -> bool:
    return importlib.util.find_spec(module_name) is not None


def _configured(env_vars: list[str]) -> bool:
    return all(os.environ.get(env_var) for env_var in env_vars)


def get_adapter(name: str, model: str | None = None, azure: bool = False) -> BaseAdapter:
    """Instantiate an adapter by logical name."""
    if name == "mock":
        from mtp_run.adapters.mock import MockAdapter
        return MockAdapter(seed=42)

    if name == "anthropic":
        from mtp_run.adapters.anthropic import AnthropicAdapter
        return AnthropicAdapter(model=model or "claude-sonnet-4-20250514")

    if name == "openai":
        from mtp_run.adapters.openai import OpenAIAdapter
        return OpenAIAdapter(model=model or "gpt-4o", azure=azure)

    raise ValueError(f"Unknown adapter '{name}'. Supported: mock, anthropic, openai.")


def list_adapter_statuses() -> list[AdapterStatus]:
    """Report readiness of all supported adapters."""
    statuses = [
        AdapterStatus(
            name="mock",
            variant="default",
            status="ready",
            platform="mock-adapter-v0.4",
            notes="Deterministic local adapter. No API key required.",
        )
    ]

    anthropic_sdk = _sdk_available("anthropic")
    anthropic_configured = _configured(["ANTHROPIC_API_KEY"])
    statuses.append(
        AdapterStatus(
            name="anthropic",
            variant="claude",
            status="ready" if anthropic_sdk and anthropic_configured else (
                "missing_dependency" if not anthropic_sdk else "not_configured"
            ),
            platform="anthropic/<model>",
            notes="Requires `pip install -e \".[anthropic]\"` and `ANTHROPIC_API_KEY`.",
        )
    )

    openai_sdk = _sdk_available("openai")
    openai_configured = _configured(["OPENAI_API_KEY"])
    statuses.append(
        AdapterStatus(
            name="openai",
            variant="default",
            status="ready" if openai_sdk and openai_configured else (
                "missing_dependency" if not openai_sdk else "not_configured"
            ),
            platform="openai/<model>",
            notes="Requires `pip install -e \".[openai]\"` and `OPENAI_API_KEY`.",
        )
    )

    azure_configured = _configured(["AZURE_OPENAI_API_KEY", "AZURE_OPENAI_ENDPOINT"])
    statuses.append(
        AdapterStatus(
            name="openai",
            variant="azure",
            status="ready" if openai_sdk and azure_configured else (
                "missing_dependency" if not openai_sdk else "not_configured"
            ),
            platform="azure-openai/<deployment>",
            notes="Requires `pip install -e \".[openai]\"`, `AZURE_OPENAI_API_KEY`, and `AZURE_OPENAI_ENDPOINT`.",
        )
    )

    return statuses
