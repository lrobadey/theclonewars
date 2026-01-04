from __future__ import annotations

from textual.app import ComposeResult
from textual.containers import Container, Vertical
from textual.screen import Screen

from clone_wars.engine.state import GameState
from clone_wars.ui.console import CommandConsole
from clone_wars.ui.widgets import EnemyIntel, HeaderBar, LogisticsPanel, ProductionPanel, SituationMap, TaskForcePanel


class DashboardScreen(Screen):
    """
    The master screen that holds the tactical dashboard.
    Replaces the old multi-screen navigation model.
    """

    CSS_PATH = "app.tcss"

    def __init__(self, state: GameState) -> None:
        super().__init__()
        self.state = state

    def compose(self) -> ComposeResult:
        yield HeaderBar(self.state, classes="header-bar")

        with Container(id="dashboard-grid"):
            with Vertical(classes="box", id="map-panel"):
                yield SituationMap(self.state)

            with Vertical(classes="box", id="enemy-panel"):
                yield EnemyIntel(self.state)

            with Vertical(classes="box", id="task-force-panel"):
                yield TaskForcePanel(self.state)

            with Vertical(classes="box", id="production-panel"):
                yield ProductionPanel(self.state)

            with Vertical(classes="box", id="logistics-panel"):
                yield LogisticsPanel(self.state)

        yield CommandConsole(self.state, classes="command-console")

    def on_mount(self) -> None:
        self.set_interval(0.5, self.refresh_dashboard)

    def refresh_dashboard(self) -> None:
        """Force a repaint of passive widgets to reflect game state changes."""
        self.query_one(HeaderBar).refresh()
        self.query_one(SituationMap).refresh_status()
        self.query_one(TaskForcePanel).refresh()
        self.query_one(EnemyIntel).refresh()
        self.query_one(ProductionPanel).refresh()
        self.query_one(LogisticsPanel).refresh()
        self.query_one(CommandConsole).update_view()
