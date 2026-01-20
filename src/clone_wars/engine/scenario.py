from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from clone_wars.engine.logistics import DepotNode
from clone_wars.engine.production import ProductionJobType
from clone_wars.engine.state import GameState
from clone_wars.engine.types import Supplies


@dataclass(frozen=True)
class ScenarioData:
    seed: int
    enemy_infantry: int
    enemy_walkers: int
    enemy_support: int
    enemy_cohesion: float
    fortification: float
    reinforcement_rate: float
    intel_confidence: float


class ScenarioError(ValueError):
    pass


def load_game_state(path: Path) -> GameState:
    data = _load_json(path)
    scenario = _parse_scenario(data)
    data_dir = path.parent
    state = GameState.new(seed=scenario.seed, data_dir=data_dir)
    state.planet.enemy.infantry = scenario.enemy_infantry
    state.planet.enemy.walkers = scenario.enemy_walkers
    state.planet.enemy.support = scenario.enemy_support
    state.planet.enemy.cohesion = scenario.enemy_cohesion
    state.planet.enemy.fortification = scenario.fortification
    state.planet.enemy.reinforcement_rate = scenario.reinforcement_rate
    state.planet.enemy.intel_confidence = scenario.intel_confidence

    # Optional: planet control
    if "control" in data.get("planet", {}):
        state.planet.control = float(data["planet"]["control"])

    # Optional: logistics initial stocks
    if "logistics" in data:
        logistics_data = data["logistics"]
        if "depot_stocks" in logistics_data:
            stocks = logistics_data["depot_stocks"]
            for depot_name, stock_dict in stocks.items():
                try:
                    depot = DepotNode[depot_name.upper().replace(" ", "_")]
                    state.logistics.depot_stocks[depot] = Supplies(
                        ammo=int(stock_dict.get("ammo", 0)),
                        fuel=int(stock_dict.get("fuel", 0)),
                        med_spares=int(stock_dict.get("med_spares", 0)),
                    )
                except (KeyError, ValueError):
                    pass  # Skip invalid depot names

    # Optional: production capacity/factories
    if "production" in data:
        prod_data = data["production"]
        if "factories" in prod_data:
            state.production.factories = int(prod_data["factories"])
        elif "capacity" in prod_data:
            state.production.factories = int(prod_data["capacity"])

    return state


def _load_json(path: Path) -> dict:
    try:
        with path.open("r", encoding="utf-8") as handle:
            return json.load(handle)
    except FileNotFoundError as exc:
        raise ScenarioError(f"Scenario not found: {path}") from exc
    except json.JSONDecodeError as exc:
        raise ScenarioError(f"Invalid JSON in scenario: {exc}") from exc


def _parse_scenario(data: dict) -> ScenarioData:
    if not isinstance(data, dict):
        raise ScenarioError("Scenario root must be an object")
    seed = _require_int(data, "seed")
    planet = _require_dict(data, "planet")
    objectives = _require_list(planet, "objectives")
    _validate_objectives(objectives)
    enemy = _require_dict(planet, "enemy")
    infantry = _require_int(enemy, "infantry")
    walkers = _require_int(enemy, "walkers")
    support = _require_int(enemy, "support")
    if infantry < 0 or walkers < 0 or support < 0:
        raise ScenarioError("enemy troop counts must be non-negative")

    cohesion = _require_number(enemy, "cohesion")
    if not (0.0 <= cohesion <= 1.0):
        raise ScenarioError("enemy.cohesion must be between 0 and 1")

    confidence = _require_number(enemy, "intel_confidence")
    if not (0.0 <= confidence <= 1.0):
        raise ScenarioError("enemy.intel_confidence must be between 0 and 1")

    fortification = _require_number(enemy, "fortification")
    reinforcement_rate = _require_number(enemy, "reinforcement_rate")

    return ScenarioData(
        seed=seed,
        enemy_infantry=infantry,
        enemy_walkers=walkers,
        enemy_support=support,
        enemy_cohesion=float(cohesion),
        fortification=float(fortification),
        reinforcement_rate=float(reinforcement_rate),
        intel_confidence=float(confidence),
    )


def _validate_objectives(objectives: list) -> None:
    ids = set()
    for obj in objectives:
        if not isinstance(obj, dict):
            raise ScenarioError("planet.objectives entries must be objects")
        obj_id = obj.get("id")
        if not isinstance(obj_id, str):
            raise ScenarioError("planet.objectives.id must be a string")
        ids.add(obj_id)
    required = {"foundry", "comms", "power"}
    if ids != required:
        missing = required - ids
        extra = ids - required
        details = []
        if missing:
            details.append(f"missing: {sorted(missing)}")
        if extra:
            details.append(f"extra: {sorted(extra)}")
        detail_text = ", ".join(details)
        raise ScenarioError(f"planet.objectives ids must be {sorted(required)} ({detail_text})")


def _require_dict(data: dict, key: str) -> dict:
    value = data.get(key)
    if not isinstance(value, dict):
        raise ScenarioError(f"{key} must be an object")
    return value


def _require_list(data: dict, key: str) -> list:
    value = data.get(key)
    if not isinstance(value, list):
        raise ScenarioError(f"{key} must be an array")
    return value


def _require_int(data: dict, key: str) -> int:
    value = data.get(key)
    if not isinstance(value, int):
        raise ScenarioError(f"{key} must be an integer")
    return value


def _require_number(data: dict, key: str) -> float:
    value = data.get(key)
    return float(_require_number_value(value, key))


def _require_number_value(value: object, key: str) -> float:
    if not isinstance(value, (int, float)):
        raise ScenarioError(f"{key} must be a number")
    return float(value)
