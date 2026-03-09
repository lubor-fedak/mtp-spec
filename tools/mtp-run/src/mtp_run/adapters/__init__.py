"""Abstract base adapter for LLM connections."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any


@dataclass
class StepResult:
    """Structured result from executing a single MTP step."""
    state: str  # success | partial | deviation | failure | escalated
    validation_result: str  # pass | fail | not_applicable
    output: str  # the actual output/work product of the step
    deviation_description: str = ""
    deviation_reason: str = ""
    failure_reason: str = ""
    notes: str = ""
    edge_cases_encountered: list[dict] = field(default_factory=list)
    novel_situations: list[dict] = field(default_factory=list)
    dead_ends_considered: list[str] = field(default_factory=list)
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
