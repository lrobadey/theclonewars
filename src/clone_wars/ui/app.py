from __future__ import annotations

from pathlib import Path

from textual.app import App, ComposeResult
from textual.binding import Binding

from clone_wars.engine.scenario import ScenarioError, load_game_state
from clone_wars.engine.state import GameState
from clone_wars.ui.dashboard import DashboardScreen


class CloneWarsApp(App[None]):
    CSS_PATH = "app.tcss"

    BINDINGS = [
        Binding("n", "next_day", "Next Day"),
        Binding("q", "quit", "Quit"),
    ]

    def __init__(self) -> None:
        super().__init__()
        self.state = self._load_state()

    def _load_state(self) -> GameState:
        data_path = Path(__file__).resolve().parents[1] / "data" / "scenario.json"
        try:
            return load_game_state(data_path)
        except ScenarioError as exc:
            raise RuntimeError(f"Failed to load scenario: {exc}") from exc

    def on_mount(self) -> None:
        self.install_screen(DashboardScreen(self.state), name="dashboard")
        self.push_screen("dashboard")

    def compose(self) -> ComposeResult:
        return []

    def action_next_day(self) -> None:
        if self.state.raid_session is not None:
            return
        self.state.advance_day()
        if isinstance(self.screen, DashboardScreen):
            self.screen.refresh_dashboard()
