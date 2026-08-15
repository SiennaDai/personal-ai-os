"""Stable Obsidian Integration errors."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class IntegrationError(Exception):
    """An expected failure safe to return through the MCP contract."""

    code: str
    message: str
    retryable: bool = False
    details: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        super().__init__(self.message)

    def as_dict(self) -> dict[str, Any]:
        result: dict[str, Any] = {
            "code": self.code,
            "message": self.message,
            "retryable": self.retryable,
        }
        if self.details:
            result["details"] = self.details
        return result
