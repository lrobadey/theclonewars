from __future__ import annotations

import json
from pathlib import Path

from war_sim.domain.types import LocationId
from war_sim.rules.ruleset import _load_production_config
from war_sim.rules.ruleset import Ruleset
from war_sim.rules.scenario import load_game_state


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


def test_scenario_front_supply_override_syncs_task_force(tmp_path) -> None:
    scenario_src = Path(__file__).resolve().parents[2] / "sim-v2" / "data" / "scenarios" / "default.json"
    rules_src = Path(__file__).resolve().parents[2] / "sim-v2" / "data" / "rules"

    scenario_data = json.loads(scenario_src.read_text(encoding="utf-8"))
    scenario_data["logistics"] = {
        "depot_stocks": {
            "front": {"ammo": 777, "fuel": 666, "med_spares": 555},
        }
    }

    scenario_path = tmp_path / "scenario.json"
    scenario_path.write_text(json.dumps(scenario_data), encoding="utf-8")
    for rules_file in rules_src.glob("*.json"):
        (tmp_path / rules_file.name).write_text(rules_file.read_text(encoding="utf-8"), encoding="utf-8")

    state = load_game_state(scenario_path)

    assert state.logistics.depot_stocks[LocationId.CONTESTED_FRONT].ammo == 777
    assert state.logistics.depot_stocks[LocationId.CONTESTED_FRONT].fuel == 666
    assert state.logistics.depot_stocks[LocationId.CONTESTED_FRONT].med_spares == 555
    assert state.task_force.supplies == state.logistics.depot_stocks[LocationId.CONTESTED_FRONT]


def test_load_production_config_prefers_production_block_over_factory(tmp_path) -> None:
    production_path = tmp_path / "production.json"
    production_path.write_text(
        json.dumps(
            {
                "production": {
                    "slots_per_factory": 31,
                    "max_factories": 9,
                    "queue_policy": "parallel",
                    "costs": {"ammo": 11},
                },
                "factory": {
                    "slots_per_factory": 12,
                    "max_factories": 3,
                    "queue_policy": "parallel",
                    "costs": {"ammo": 99},
                },
                "barracks": {
                    "slots_per_barracks": 22,
                    "max_barracks": 7,
                    "queue_policy": "parallel",
                    "costs": {"infantry": 2},
                },
            }
        ),
        encoding="utf-8",
    )

    prod, barracks = _load_production_config(production_path)

    assert prod.slots_per_factory == 31
    assert prod.max_factories == 9
    assert prod.costs["ammo"] == 11
    assert barracks.slots_per_barracks == 22
