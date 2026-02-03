"""Explainability + UI events."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class FactorScope:
    kind: str  # "operation" | "raid" | "logistics" | ...
    id: str


@dataclass(frozen=True)
class FactorEvent:
    name: str
    phase: str
    value: float
    delta: str
    why: str
    scope: FactorScope


@dataclass(frozen=True)
class UiEvent:
    kind: str
    message: str
    data: dict[str, Any] | None = None
