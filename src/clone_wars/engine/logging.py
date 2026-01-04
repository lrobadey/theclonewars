from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class Event:
    name: str
    phase: str
    value: float
    delta: str
    why: str


@dataclass(frozen=True, slots=True)
class TopFactor:
    name: str
    value: float
    delta: str
    why: str
