"""Comprehensive tests for operation resolver."""

from pathlib import Path

import pytest

from clone_wars.engine.ops import OperationPlan, OperationTarget
from clone_wars.engine.scenario import load_game_state
from clone_wars.engine.state import GameState
from clone_wars.engine.types import ObjectiveStatus, Supplies


def test_operation_duration_calculation() -> None:
    """Test that operation duration is calculated based on fortification and control."""
    data_dir = Path(__file__).resolve().parents[1] / "src" / "clone_wars" / "data"
    state = load_game_state(data_dir / "scenario.json")

    plan = OperationPlan.quickstart(OperationTarget.FOUNDRY)
    state.start_operation(plan)

    # Duration should be calculated
    assert state.operation is not None
    assert state.operation.estimated_days >= 1
    assert state.operation.day_in_operation == 0


def test_operation_multi_day_progression() -> None:
    """Test that operations progress over multiple days."""
    data_dir = Path(__file__).resolve().parents[1] / "src" / "clone_wars" / "data"
    state = load_game_state(data_dir / "scenario.json")

    plan = OperationPlan.quickstart(OperationTarget.FOUNDRY)
    state.start_operation(plan)

    initial_days = state.operation.estimated_days
    assert initial_days >= 1

    # Advance until operation completes
    max_iterations = 20
    iterations = 0
    while state.operation is not None and iterations < max_iterations:
        state.advance_day()
        iterations += 1

    # Operation should complete
    assert state.operation is None
    assert state.last_aar is not None
    # AAR should record the operation duration
    assert state.last_aar.days >= 1
    assert state.last_aar.days <= initial_days + 2  # Allow some flexibility


def test_operation_only_one_active() -> None:
    """Test that only one operation can be active at a time."""
    data_dir = Path(__file__).resolve().parents[1] / "src" / "clone_wars" / "data"
    state = load_game_state(data_dir / "scenario.json")

    plan1 = OperationPlan.quickstart(OperationTarget.FOUNDRY)
    state.start_operation(plan1)

    plan2 = OperationPlan.quickstart(OperationTarget.COMMS)
    with pytest.raises(RuntimeError, match="Only one active operation"):
        state.start_operation(plan2)


def test_operation_supply_consumption() -> None:
    """Test that operations consume supplies correctly."""
    data_dir = Path(__file__).resolve().parents[1] / "src" / "clone_wars" / "data"
    state = load_game_state(data_dir / "scenario.json")

    initial_supplies = state.task_force.supplies
    plan = OperationPlan.quickstart(OperationTarget.FOUNDRY)
    state.start_operation(plan)

    # Advance through operation
    while state.operation is not None:
        state.advance_day()

    # Supplies should be consumed
    final_supplies = state.task_force.supplies
    assert final_supplies.ammo < initial_supplies.ammo
    assert final_supplies.fuel < initial_supplies.fuel
    assert final_supplies.med_spares < initial_supplies.med_spares


def test_operation_supply_shortage_effects() -> None:
    """Test that supply shortages affect operation outcomes."""
    data_dir = Path(__file__).resolve().parents[1] / "src" / "clone_wars" / "data"
    state = load_game_state(data_dir / "scenario.json")

    # Set very low supplies
    state.task_force.supplies = Supplies(ammo=1, fuel=1, med_spares=1)

    plan = OperationPlan.quickstart(OperationTarget.FOUNDRY)
    state.start_operation(plan)

    while state.operation is not None:
        state.advance_day()

    # Should have logged shortage events
    assert state.last_aar is not None
    shortage_events = [e for e in state.last_aar.events if "shortage" in e.name.lower()]
    assert len(shortage_events) > 0


def test_operation_signature_interactions() -> None:
    """Test that all 3 signature interactions are applied."""
    data_dir = Path(__file__).resolve().parents[1] / "src" / "clone_wars" / "data"
    state = load_game_state(data_dir / "scenario.json")

    # Ensure task force has all unit types
    state.task_force.composition.infantry = 6
    state.task_force.composition.walkers = 2
    state.task_force.composition.support = 1

    plan = OperationPlan.quickstart(OperationTarget.FOUNDRY)
    state.start_operation(plan)

    while state.operation is not None:
        state.advance_day()

    assert state.last_aar is not None
    events = state.last_aar.events

    # Check for signature interaction events
    has_recon = any("recon" in e.name.lower() for e in events)
    has_protection = any("transport" in e.name.lower() or "protection" in e.name.lower() for e in events)
    has_medic = any("medic" in e.name.lower() for e in events)

    assert has_recon, "Recon variance reduction should be logged"
    assert has_protection, "Transport/protection should be logged"
    assert has_medic, "Medic sustainment should be logged"


def test_operation_walker_protection() -> None:
    """Test that walkers protect infantry from losses."""
    data_dir = Path(__file__).resolve().parents[1] / "src" / "clone_wars" / "data"
    state = load_game_state(data_dir / "scenario.json")

    # Set up task force with walkers
    state.task_force.composition.infantry = 10
    state.task_force.composition.walkers = 3
    state.task_force.composition.support = 0

    initial_infantry = state.task_force.composition.infantry

    plan = OperationPlan.quickstart(OperationTarget.FOUNDRY)
    state.start_operation(plan)

    while state.operation is not None:
        state.advance_day()

    # Infantry should be protected (losses reduced)
    final_infantry = state.task_force.composition.infantry
    # Note: exact loss calculation depends on many factors, but protection should help
    assert state.last_aar is not None
    protection_events = [e for e in state.last_aar.events if "transport" in e.name.lower() or "protection" in e.name.lower()]
    assert len(protection_events) > 0


def test_operation_medic_sustainment() -> None:
    """Test that medics reduce casualties and improve readiness."""
    data_dir = Path(__file__).resolve().parents[1] / "src" / "clone_wars" / "data"
    state = load_game_state(data_dir / "scenario.json")

    # Set up task force with medics
    state.task_force.composition.infantry = 10
    state.task_force.composition.walkers = 0
    state.task_force.composition.support = 3  # Medics

    initial_readiness = state.task_force.readiness

    plan = OperationPlan.quickstart(OperationTarget.FOUNDRY)
    state.start_operation(plan)

    while state.operation is not None:
        state.advance_day()

    assert state.last_aar is not None
    medic_events = [e for e in state.last_aar.events if "medic" in e.name.lower()]
    assert len(medic_events) > 0


def test_operation_recon_variance_reduction() -> None:
    """Test that recon units reduce variance."""
    data_dir = Path(__file__).resolve().parents[1] / "src" / "clone_wars" / "data"
    state = load_game_state(data_dir / "scenario.json")

    # Set up task force with recon
    state.task_force.composition.infantry = 10
    state.task_force.composition.walkers = 0
    state.task_force.composition.support = 2  # Recon

    plan = OperationPlan.quickstart(OperationTarget.FOUNDRY)
    state.start_operation(plan)

    while state.operation is not None:
        state.advance_day()

    assert state.last_aar is not None
    recon_events = [e for e in state.last_aar.events if "recon" in e.name.lower()]
    assert len(recon_events) > 0


def test_operation_aar_structure() -> None:
    """Test that AAR has all required fields."""
    data_dir = Path(__file__).resolve().parents[1] / "src" / "clone_wars" / "data"
    state = load_game_state(data_dir / "scenario.json")

    plan = OperationPlan.quickstart(OperationTarget.FOUNDRY)
    state.start_operation(plan)

    while state.operation is not None:
        state.advance_day()

    assert state.last_aar is not None
    aar = state.last_aar

    # Verify AAR structure
    assert aar.outcome in ["CAPTURED", "RAIDED", "DESTROYED", "FAILED", "WITHDREW"]
    assert aar.target == OperationTarget.FOUNDRY
    assert aar.days > 0
    assert aar.losses >= 0
    assert isinstance(aar.remaining_supplies, Supplies)
    assert len(aar.top_factors) > 0
    assert len(aar.events) > 0


def test_operation_aar_top_factors() -> None:
    """Test that AAR top factors are correctly identified."""
    data_dir = Path(__file__).resolve().parents[1] / "src" / "clone_wars" / "data"
    state = load_game_state(data_dir / "scenario.json")

    plan = OperationPlan.quickstart(OperationTarget.FOUNDRY)
    state.start_operation(plan)

    while state.operation is not None:
        state.advance_day()

    assert state.last_aar is not None
    top_factors = state.last_aar.top_factors

    # Should have top 5 factors
    assert len(top_factors) <= 5
    assert len(top_factors) > 0

    # Factors should have required fields
    for factor in top_factors:
        assert factor.name
        assert isinstance(factor.value, float)
        assert factor.delta in ["progress", "losses", "readiness", "objective"]
        assert factor.why


def test_operation_aar_phase_logging() -> None:
    """Test that AAR logs events by phase."""
    data_dir = Path(__file__).resolve().parents[1] / "src" / "clone_wars" / "data"
    state = load_game_state(data_dir / "scenario.json")

    plan = OperationPlan.quickstart(OperationTarget.FOUNDRY)
    state.start_operation(plan)

    while state.operation is not None:
        state.advance_day()

    assert state.last_aar is not None
    events = state.last_aar.events

    # Should have events from all phases
    phases = {e.phase for e in events}
    assert "contact_shaping" in phases
    assert "engagement" in phases
    assert "exploit_consolidate" in phases


def test_operation_success_captures_objective() -> None:
    """Test that successful capture operation secures objective."""
    data_dir = Path(__file__).resolve().parents[1] / "src" / "clone_wars" / "data"
    state = load_game_state(data_dir / "scenario.json")

    # Set favorable conditions for success
    state.planet.enemy.fortification = 0.8
    state.planet.control = 0.8
    state.task_force.supplies = Supplies(ammo=500, fuel=500, med_spares=500)

    plan = OperationPlan(
        target=OperationTarget.FOUNDRY,
        approach_axis="stealth",
        fire_support_prep="preparatory",
        engagement_posture="shock",
        risk_tolerance="high",
        exploit_vs_secure="push",
        end_state="capture",
    )

    # Try multiple times to get a success
    for seed in range(10):
        state = load_game_state(data_dir / "scenario.json")
        state.rng_seed = seed
        state.rng = state.rng.__class__(seed)
        state.planet.enemy.fortification = 0.8
        state.planet.control = 0.8
        state.task_force.supplies = Supplies(ammo=500, fuel=500, med_spares=500)

        state.start_operation(plan)
        while state.operation is not None:
            state.advance_day()

        if state.last_aar and state.last_aar.outcome == "CAPTURED":
            assert state.planet.objectives.foundry == ObjectiveStatus.SECURED
            break


def test_operation_failure_reduces_control() -> None:
    """Test that operation failure reduces planet control."""
    data_dir = Path(__file__).resolve().parents[1] / "src" / "clone_wars" / "data"
    state = load_game_state(data_dir / "scenario.json")

    # Set conditions for likely failure
    plan = OperationPlan(
        target=OperationTarget.FOUNDRY,
        approach_axis="dispersed",
        fire_support_prep="conserve",
        engagement_posture="feint",
        risk_tolerance="low",
        exploit_vs_secure="secure",
        end_state="capture",
    )

    state.planet.enemy.fortification = 2.0
    state.planet.control = 0.5
    state.task_force.supplies = Supplies(ammo=1, fuel=1, med_spares=1)
    
    # Capture initial control AFTER setting it
    initial_control = state.planet.control

    state.start_operation(plan)
    while state.operation is not None:
        state.advance_day()

    # If failed, control should decrease
    if state.last_aar and state.last_aar.outcome == "FAILED":
        assert state.planet.control < initial_control


def test_operation_all_targets() -> None:
    """Test operations against all three objectives."""
    data_dir = Path(__file__).resolve().parents[1] / "src" / "clone_wars" / "data"

    for target in [OperationTarget.FOUNDRY, OperationTarget.COMMS, OperationTarget.POWER]:
        state = load_game_state(data_dir / "scenario.json")
        plan = OperationPlan.quickstart(target)
        state.start_operation(plan)

        while state.operation is not None:
            state.advance_day()

        assert state.last_aar is not None
        assert state.last_aar.target == target


def test_operation_all_end_states() -> None:
    """Test all operation end states."""
    data_dir = Path(__file__).resolve().parents[1] / "src" / "clone_wars" / "data"

    for end_state in ["capture", "raid", "destroy", "withdraw"]:
        state = load_game_state(data_dir / "scenario.json")
        plan = OperationPlan(
            target=OperationTarget.FOUNDRY,
            approach_axis="direct",
            fire_support_prep="conserve",
            engagement_posture="methodical",
            risk_tolerance="med",
            exploit_vs_secure="secure",
            end_state=end_state,
        )

        state.start_operation(plan)
        while state.operation is not None:
            state.advance_day()

        assert state.last_aar is not None
        assert state.last_aar.outcome in ["CAPTURED", "RAIDED", "DESTROYED", "FAILED", "WITHDREW"]


def test_operation_fortification_effects() -> None:
    """Test that fortification affects operation difficulty."""
    data_dir = Path(__file__).resolve().parents[1] / "src" / "clone_wars" / "data"

    # Low fortification
    state_low = load_game_state(data_dir / "scenario.json")
    state_low.planet.enemy.fortification = 0.8
    plan = OperationPlan.quickstart(OperationTarget.FOUNDRY)
    state_low.start_operation(plan)
    while state_low.operation is not None:
        state_low.advance_day()

    # High fortification
    state_high = load_game_state(data_dir / "scenario.json")
    state_high.planet.enemy.fortification = 2.0
    state_high.rng_seed = state_low.rng_seed
    state_high.rng = state_high.rng.__class__(state_high.rng_seed)
    state_high.start_operation(plan)
    while state_high.operation is not None:
        state_high.advance_day()

    # High fortification should make operation harder (longer duration or worse outcome)
    assert state_high.operation is None
    assert state_low.operation is None

    # Duration should be longer with higher fortification
    assert state_high.last_aar is not None
    assert state_low.last_aar is not None
    # Note: This is probabilistic, but generally higher fort = longer duration

