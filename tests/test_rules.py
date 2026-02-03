"""Comprehensive tests for rules system."""

from pathlib import Path

import pytest

from clone_wars.engine.rules import RulesError, Ruleset


def test_load_ruleset() -> None:
    """Test loading complete ruleset."""
    data_dir = Path(__file__).resolve().parents[1] / "src" / "clone_wars" / "data"
    rules = Ruleset.load(data_dir)

    # Verify all rule types loaded
    assert rules.supply_classes
    assert rules.unit_roles
    assert rules.operation_types
    assert rules.objectives

    # Verify supply classes
    assert "ammo" in rules.supply_classes
    assert "fuel" in rules.supply_classes
    assert "med_spares" in rules.supply_classes

    # Verify unit roles
    assert "infantry" in rules.unit_roles
    assert "walkers" in rules.unit_roles
    assert "support" in rules.unit_roles

    # Verify operation decision rules
    assert "direct" in rules.approach_axes
    assert "conserve" in rules.fire_support_prep
    assert "shock" in rules.engagement_postures
    assert "low" in rules.risk_tolerances
    assert "push" in rules.exploit_vs_secure
    assert "capture" in rules.end_states


def test_supply_class_structure() -> None:
    """Test supply class structure and effects."""
    data_dir = Path(__file__).resolve().parents[1] / "src" / "clone_wars" / "data"
    rules = Ruleset.load(data_dir)

    ammo = rules.supply_classes["ammo"]
    assert ammo.id == "ammo"
    assert isinstance(ammo.name, str) and ammo.name.strip()
    assert "progress_penalty" in ammo.shortage_effects
    assert "loss_multiplier" in ammo.shortage_effects
    assert isinstance(ammo.shortage_effects["progress_penalty"], float)


def test_unit_role_capabilities() -> None:
    """Test unit role capabilities and interactions."""
    data_dir = Path(__file__).resolve().parents[1] / "src" / "clone_wars" / "data"
    rules = Ruleset.load(data_dir)

    # Test infantry
    infantry = rules.unit_roles["infantry"]
    assert "combat" in infantry.capabilities
    assert infantry.transport_protection is not None
    assert infantry.transport_protection["can_be_protected"] is True

    # Test walkers
    walkers = rules.unit_roles["walkers"]
    assert "combat" in walkers.capabilities
    assert "transport" in walkers.capabilities
    assert walkers.transport_protection is not None
    assert walkers.transport_protection["can_protect"] is True

    # Test support
    support = rules.unit_roles["support"]
    assert "recon" in support.capabilities
    assert "medical" in support.capabilities
    assert support.recon is not None
    assert support.sustainment is not None


def test_operation_type_duration() -> None:
    """Test operation type duration ranges."""
    data_dir = Path(__file__).resolve().parents[1] / "src" / "clone_wars" / "data"
    rules = Ruleset.load(data_dir)

    raid = rules.operation_types["raid"]
    assert raid.base_duration_days >= 1
    assert raid.duration_range[0] <= raid.duration_range[1]
    assert raid.required_progress > 0

    campaign = rules.operation_types["campaign"]
    assert campaign.base_duration_days >= raid.base_duration_days


def test_operation_decision_modifiers() -> None:
    """Test operation decision modifiers."""
    data_dir = Path(__file__).resolve().parents[1] / "src" / "clone_wars" / "data"
    rules = Ruleset.load(data_dir)

    # Test approach axes
    direct = rules.approach_axes["direct"]
    assert "progress_mod" in direct
    assert "loss_mod" in direct

    # Test risk tolerances
    high = rules.risk_tolerances["high"]
    assert "variance_multiplier" in high


def test_rules_missing_file() -> None:
    """Test error handling for missing rules file."""
    data_dir = Path(__file__).resolve().parents[0] / "nonexistent"

    with pytest.raises(RulesError):
        Ruleset.load(data_dir)


def test_rules_invalid_json() -> None:
    """Test error handling for invalid JSON."""
    import json
    import tempfile

    with tempfile.TemporaryDirectory() as tmpdir:
        invalid_file = Path(tmpdir) / "supplies.json"
        invalid_file.write_text("{ invalid json }")

        with pytest.raises(RulesError):
            Ruleset.load(Path(tmpdir))


def test_objective_definitions() -> None:
    """Test objective definitions."""
    data_dir = Path(__file__).resolve().parents[1] / "src" / "clone_wars" / "data"
    rules = Ruleset.load(data_dir)

    foundry = rules.objectives["foundry"]
    assert foundry.id == "foundry"
    assert isinstance(foundry.name, str) and foundry.name.strip()
    assert foundry.base_difficulty > 0
    assert isinstance(foundry.description, str)
    assert len(foundry.description.strip()) > 0

    # All three objectives should exist
    assert "foundry" in rules.objectives
    assert "comms" in rules.objectives
    assert "power" in rules.objectives
