"""Shared types for the CLI package.

These types are used across multiple modules and cannot live in any single
one without creating circular imports.
"""

from __future__ import annotations

from dataclasses import dataclass

__all__ = ["ToolResult", "Ok", "Err"]


@dataclass(frozen=True)
class ToolResult:
    """Discriminated result from a tool execution.

    Use ``isinstance(result, Ok)`` or ``isinstance(result, Err)`` to branch.
    """

    message: str


class Ok(ToolResult):
    """Tool succeeded."""


class Err(ToolResult):
    """Tool failed with an error message."""
