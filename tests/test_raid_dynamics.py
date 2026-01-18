"""Tests for the new raid dynamics: initiative, walker screen, ammo pinch, and beat system."""

from clone_wars.engine.ops import OperationTarget
from clone_wars.engine.state import GameState
from clone_wars.engine.types import Supplies


def test_walker_screen_reduces_infantry_casualties() -> None:
    """Walkers should absorb casualties that would otherwise hit infantry."""
    # Run raid WITH walkers
    state_with = GameState.new(seed=42)
    state_with.task_force.composition.infantry = 100
    state_with.task_force.composition.walkers = 10
    state_with.task_force.composition.support = 0
    state_with.planet.enemy.infantry = 100
    state_with.planet.enemy.walkers = 0
    state_with.planet.enemy.support = 0
    state_with.planet.enemy.fortification = 1.2
    report_with = state_with.raid(OperationTarget.FOUNDRY)

    # Run raid WITHOUT walkers (same seed)
    state_without = GameState.new(seed=42)
    state_without.task_force.composition.infantry = 100
    state_without.task_force.composition.walkers = 0
    state_without.task_force.composition.support = 0
    state_without.planet.enemy.infantry = 100
    state_without.planet.enemy.walkers = 0
    state_without.planet.enemy.support = 0
    state_without.planet.enemy.fortification = 1.2
    report_without = state_without.raid(OperationTarget.FOUNDRY)

    # With walkers, infantry losses should be reduced (walkers absorb some)
    inf_losses_with = 100 - report_with.your_remaining["infantry"]
    inf_losses_without = 100 - report_without.your_remaining["infantry"]

    # The force with walkers should have proportionally fewer infantry losses
    # because walkers absorb 40% of infantry's casualty weight
    assert inf_losses_with < inf_losses_without, (
        f"Infantry losses with walkers ({inf_losses_with}) should be less than "
        f"without walkers ({inf_losses_without})"
    )


def test_low_ammo_increases_defeat_likelihood_or_casualties() -> None:
    """Low ammo state should reduce firepower and increase casualties."""
    # Run with full ammo
    state_full = GameState.new(seed=100)
    state_full.task_force.composition.infantry = 50
    state_full.task_force.composition.walkers = 0
    state_full.task_force.composition.support = 0
    state_full.task_force.supplies = Supplies(ammo=100, fuel=90, med_spares=40)
    state_full.planet.enemy.infantry = 50
    state_full.planet.enemy.fortification = 1.0
    report_full = state_full.raid(OperationTarget.FOUNDRY)

    # Run with critically low ammo (same seed)
    state_low = GameState.new(seed=100)
    state_low.task_force.composition.infantry = 50
    state_low.task_force.composition.walkers = 0
    state_low.task_force.composition.support = 0
    state_low.task_force.supplies = Supplies(ammo=20, fuel=90, med_spares=40)
    state_low.planet.enemy.infantry = 50
    state_low.planet.enemy.fortification = 1.0
    report_low = state_low.raid(OperationTarget.FOUNDRY)

    # Low ammo should result in worse outcome or more casualties
    # Check if either outcome is worse or casualties are higher
    outcome_worse = (
        (report_full.outcome == "VICTORY" and report_low.outcome != "VICTORY")
        or report_low.your_casualties > report_full.your_casualties
    )
    assert outcome_worse, (
        f"Low ammo should worsen outcome or increase casualties. "
        f"Full: {report_full.outcome}/{report_full.your_casualties} vs "
        f"Low: {report_low.outcome}/{report_low.your_casualties}"
    )


def test_tick_log_includes_beat_prefixes() -> None:
    """Tick log events should include beat prefixes (INFILTRATION/BREACH/EXFIL)."""
    state = GameState.new(seed=77)
    report = state.raid(OperationTarget.FOUNDRY)

    # Check that we have events from different beats
    infiltration_events = [t for t in report.tick_log if t.beat == "INFILTRATION"]
    breach_events = [t for t in report.tick_log if t.beat == "BREACH"]
    exfil_events = [t for t in report.tick_log if t.beat == "EXFIL"]

    # Should have at least some infiltration and breach events
    assert len(infiltration_events) > 0, "Should have INFILTRATION beat ticks"
    assert len(breach_events) > 0 or len(exfil_events) > 0, (
        "Should reach BREACH or EXFIL phase if combat continues"
    )

    # Check that event strings include beat prefix
    for tick in report.tick_log:
        assert tick.beat in tick.event, f"Event '{tick.event}' should contain beat '{tick.beat}'"


def test_tick_log_includes_event_tags() -> None:
    """Tick log should include specific event tags under relevant conditions."""
    state = GameState.new(seed=42)
    state.task_force.composition.walkers = 5
    state.task_force.supplies = Supplies(ammo=20, fuel=90, med_spares=40)
    state.planet.enemy.fortification = 1.3  # High to trigger fortification events
    report = state.raid(OperationTarget.FOUNDRY)

    all_events = " ".join(t.event for t in report.tick_log)

    # Should see at least one of these event tags
    expected_tags = ["INITIATIVE", "AMMO PINCH", "WALKER SCREEN", "FORTIFICATION"]
    found_any = any(tag in all_events for tag in expected_tags)
    assert found_any, f"Expected at least one of {expected_tags} in events: {all_events}"


def test_top_factors_populated_on_raid_report() -> None:
    """RaidReport should include top_factors with meaningful entries."""
    state = GameState.new(seed=42)
    state.task_force.composition.walkers = 5
    report = state.raid(OperationTarget.FOUNDRY)

    # Should have at least one top factor
    assert len(report.top_factors) > 0, "RaidReport should have top_factors"

    # Each factor should have required fields
    for factor in report.top_factors:
        assert factor.name, "Factor should have a name"
        assert factor.why, "Factor should have a why explanation"
        assert isinstance(factor.value, float), "Factor value should be float"
