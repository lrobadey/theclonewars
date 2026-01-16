from __future__ import annotations

import asyncio
from dataclasses import dataclass, field

from clone_wars.engine.state import GameState
from clone_wars.web.console_controller import ConsoleController


@dataclass
class WebSession:
    state: GameState
    controller: ConsoleController = field(default_factory=ConsoleController)
    lock: asyncio.Lock = field(default_factory=asyncio.Lock)
