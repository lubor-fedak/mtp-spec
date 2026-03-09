"""Conversation loaders for mtp-extract."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml


ROLE_RE = re.compile(r"^\s*(user|assistant|system|human|ai)\s*[:>-]\s*(.*)$", re.IGNORECASE)


@dataclass
class Message:
    role: str
    content: str
    source_ref: str


def load_conversation(path: str | Path) -> list[Message]:
    conversation_path = Path(path)
    if conversation_path.suffix.lower() in {".txt", ".md"}:
        return _parse_plaintext(conversation_path.read_text(encoding="utf-8"), conversation_path.name)

    with open(conversation_path, encoding="utf-8") as handle:
        if conversation_path.suffix.lower() in {".yaml", ".yml"}:
            data = yaml.safe_load(handle)
        else:
            data = json.load(handle)
    return _parse_structured(data, conversation_path.name)


def _parse_plaintext(text: str, source_name: str) -> list[Message]:
    messages: list[Message] = []
    current_role: str | None = None
    current_lines: list[str] = []
    counter = 0

    def flush() -> None:
        nonlocal counter, current_role, current_lines
        if current_role and current_lines:
            counter += 1
            content = "\n".join(line.rstrip() for line in current_lines).strip()
            if content:
                messages.append(
                    Message(
                        role=_normalize_role(current_role),
                        content=content,
                        source_ref=f"{source_name}:msg-{counter}",
                    )
                )
        current_lines = []

    for raw_line in text.splitlines():
        match = ROLE_RE.match(raw_line)
        if match:
            flush()
            current_role = match.group(1)
            first_line = match.group(2).strip()
            current_lines = [first_line] if first_line else []
            continue
        if current_role:
            current_lines.append(raw_line)

    flush()

    if messages:
        return messages

    stripped = text.strip()
    if not stripped:
        raise ValueError("Conversation file is empty.")
    return [Message(role="conversation", content=stripped, source_ref=f"{source_name}:msg-1")]


def _parse_structured(data: Any, source_name: str) -> list[Message]:
    if isinstance(data, dict):
        for key in ("messages", "conversation", "chat_messages", "items"):
            if key in data:
                return _parse_message_list(data[key], source_name)
        if {"role", "content"} <= set(data.keys()):
            return _parse_message_list([data], source_name)
        raise ValueError("Unsupported conversation export shape.")
    if isinstance(data, list):
        return _parse_message_list(data, source_name)
    raise ValueError(f"Unsupported conversation payload type: {type(data).__name__}.")


def _parse_message_list(items: Any, source_name: str) -> list[Message]:
    if not isinstance(items, list):
        raise ValueError("Conversation export does not contain a message list.")

    messages: list[Message] = []
    for index, item in enumerate(items, start=1):
        if not isinstance(item, dict):
            continue
        role = _extract_role(item)
        content = _extract_text(item)
        if not content.strip():
            continue
        source_ref = str(item.get("id") or item.get("uuid") or f"{source_name}:msg-{index}")
        messages.append(
            Message(
                role=role,
                content=content.strip(),
                source_ref=source_ref,
            )
        )
    if not messages:
        raise ValueError("No usable messages found in conversation export.")
    return messages


def _extract_role(item: dict[str, Any]) -> str:
    if isinstance(item.get("role"), str):
        return _normalize_role(item["role"])
    author = item.get("author")
    if isinstance(author, dict) and isinstance(author.get("role"), str):
        return _normalize_role(author["role"])
    if isinstance(author, str):
        return _normalize_role(author)
    if isinstance(item.get("speaker"), str):
        return _normalize_role(item["speaker"])
    return "assistant"


def _extract_text(item: Any) -> str:
    if item is None:
        return ""
    if isinstance(item, str):
        return item
    if isinstance(item, list):
        parts = [_extract_text(part) for part in item]
        return "\n".join(part for part in parts if part.strip())
    if isinstance(item, dict):
        if isinstance(item.get("content"), str):
            return item["content"]
        if isinstance(item.get("text"), str):
            return item["text"]
        if "parts" in item:
            return _extract_text(item["parts"])
        if "content" in item and not isinstance(item["content"], str):
            return _extract_text(item["content"])
        if "message" in item:
            return _extract_text(item["message"])
        if "value" in item:
            return _extract_text(item["value"])
    return ""


def _normalize_role(role: str) -> str:
    normalized = role.strip().lower()
    mapping = {
        "human": "user",
        "ai": "assistant",
    }
    return mapping.get(normalized, normalized)
