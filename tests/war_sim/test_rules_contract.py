from __future__ import annotations

from pathlib import Path

from war_sim.rules.ruleset import Ruleset


def test_ruleset_contracts() -> None:
    data_dir = Path(__file__).resolve().parents[2] / "src" / "clone_wars" / "data"
    rules = Ruleset.load(data_dir)

    assert rules.supply_classes
    assert rules.unit_roles
    assert rules.operation_types
    assert rules.objectives

    for supply_id, supply in rules.supply_classes.items():
        assert supply.id == supply_id
        assert isinstance(supply.name, str) and supply.name.strip()
        for value in supply.shortage_effects.values():
            assert isinstance(value, (int, float))

    for role_id, role in rules.unit_roles.items():
        assert role.id == role_id
        assert role.name
        assert role.base_power >= 0
        assert isinstance(role.capabilities, list)

    for op_id, op in rules.operation_types.items():
        assert op.id == op_id
        assert op.base_duration_days > 0
        assert op.required_progress > 0
        assert op.duration_range[0] > 0
        assert op.duration_range[0] <= op.duration_range[1]

    for obj_id, obj in rules.objectives.items():
        assert obj.id == obj_id
        assert obj.name
        assert obj.base_difficulty > 0
