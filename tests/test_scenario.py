"""Tests for scenario loading and validation."""

from pathlib import Path

import pytest

from clone_wars.engine.scenario import ScenarioError, load_game_state


def test_load_valid_scenario() -> None:
    """Test loading a valid scenario."""
    data_dir = Path(__file__).resolve().parents[1] / "src" / "clone_wars" / "data"
    scenario_path = data_dir / "scenario.json"
    state = load_game_state(scenario_path)
    assert state.day == 1
    enemy = state.contested_planet.enemy
    assert enemy.infantry >= 0
    assert enemy.walkers >= 0
    assert enemy.support >= 0
    assert 0.0 <= enemy.cohesion <= 1.0
    assert enemy.fortification > 0
    assert enemy.reinforcement_rate >= 0.0
    assert 0.0 <= enemy.intel_confidence <= 1.0


def test_scenario_backward_compatibility() -> None:
    """Test that scenario loading works with minimal required fields."""
    data_dir = Path(__file__).resolve().parents[1] / "src" / "clone_wars" / "data"
    scenario_path = data_dir / "scenario.json"
    # Should load without errors even if optional fields are missing
    state = load_game_state(scenario_path)
    assert state.logistics is not None
    assert state.production is not None
    assert state.barracks is not None
    assert state.rules is not None


def test_scenario_missing_required_field() -> None:
    """Test that missing required fields raise errors."""
    import json
    import tempfile

    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
        json.dump({"seed": 1}, f)
        temp_path = Path(f.name)

    try:
        with pytest.raises(ScenarioError):
            load_game_state(temp_path)
    finally:
        temp_path.unlink()
