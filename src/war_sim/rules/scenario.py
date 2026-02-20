from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from war_sim.domain.ops_models import OperationTarget
from war_sim.domain.types import (
    EnemyForce,
    FactionId,
    LocationId,
    ObjectiveStatus,
    Objectives,
    PlanetState,
    Supplies,
    TaskForceState,
    UnitComposition,
)
from war_sim.rules.ruleset import RulesError, Ruleset
from typing import TYPE_CHECKING
from war_sim.systems.barracks import BarracksState
from war_sim.systems.logistics import LogisticsState
from war_sim.systems.production import ProductionState

if TYPE_CHECKING:
    from war_sim.sim.state import GameState


@dataclass(frozen=True)
class ScenarioMapNode:
    id: str
    label: str
    kind: str
    description: str
    x: float
    y: float


@dataclass(frozen=True)
class ScenarioMapGroup:
    id: str
    node_ids: list[str]
    label: str
    kind: str


@dataclass(frozen=True)
class ScenarioMap:
    nodes: list[ScenarioMapNode]
    groups: list[ScenarioMapGroup]


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
    control: float | None
    map: ScenarioMap | None
    task_force_start: "TaskForceStartConfig"
    foundry_mvp: "FoundryMvpConfig | None"


@dataclass(frozen=True)
class TaskForceStartConfig:
    infantry: int
    walkers: int
    support: int
    readiness: float
    cohesion: float


@dataclass(frozen=True)
class FoundryMvpEnemyForce:
    infantry: int
    walkers: int
    support: int
    cohesion: float
    fortification: float


@dataclass(frozen=True)
class FoundryMvpConfig:
    enemy_force: FoundryMvpEnemyForce


class ScenarioError(ValueError):
    pass


def load_game_state(path: Path) -> "GameState":
    from war_sim.sim.state import GameState
    data = _load_json(path)
    scenario = _parse_scenario(data)
    # Scenarios live in data/scenarios (v2) or data/ (legacy).
    rules_dir = path.parent.parent / "rules"
    if not rules_dir.exists():
        rules_dir = path.parent
    try:
        rules = Ruleset.load(rules_dir)
    except RulesError as exc:
        raise ScenarioError(str(exc)) from exc

    prod_cfg = rules.production
    barracks_cfg = rules.barracks

    contested_planet = PlanetState(
        objectives=Objectives(
            foundry=ObjectiveStatus.ENEMY,
            comms=ObjectiveStatus.ENEMY,
            power=ObjectiveStatus.ENEMY,
        ),
        enemy=EnemyForce(
            infantry=scenario.enemy_infantry,
            walkers=scenario.enemy_walkers,
            support=scenario.enemy_support,
            cohesion=scenario.enemy_cohesion,
            fortification=scenario.fortification,
            reinforcement_rate=scenario.reinforcement_rate,
            intel_confidence=scenario.intel_confidence,
        ),
        control=scenario.control if scenario.control is not None else 0.3,
    )

    logistics = LogisticsState.new()
    front_supplies = logistics.depot_stocks[LocationId.CONTESTED_FRONT]

    state = GameState(
        day=1,
        rng_seed=scenario.seed,
        action_seq=0,
        planets={LocationId.CONTESTED_SPACEPORT: contested_planet},
        production=ProductionState.new(
            factories=3,
            slots_per_factory=prod_cfg.slots_per_factory,
            max_factories=prod_cfg.max_factories,
            queue_policy=prod_cfg.queue_policy,
            costs=prod_cfg.costs,
        ),
        barracks=BarracksState.new(
            barracks=2,
            slots_per_barracks=barracks_cfg.slots_per_barracks,
            max_barracks=barracks_cfg.max_barracks,
            queue_policy=barracks_cfg.queue_policy,
            costs=barracks_cfg.costs,
        ),
        logistics=logistics,
        task_force=TaskForceState(
            composition=UnitComposition(
                infantry=scenario.task_force_start.infantry,
                walkers=scenario.task_force_start.walkers,
                support=scenario.task_force_start.support,
            ),
            readiness=scenario.task_force_start.readiness,
            cohesion=scenario.task_force_start.cohesion,
            supplies=front_supplies,
            location=LocationId.CONTESTED_SPACEPORT,
        ),
        rules=rules,
        scenario=scenario,
        action_points=3,
        faction_turn=FactionId.NEW_SYSTEM,
        raid_session=None,
        raid_target=None,
        raid_id=None,
        operation=None,
        last_aar=None,
    )

    # Apply scenario overrides
    if "logistics" in data:
        _apply_logistics_overrides(state, data["logistics"])
    if "production" in data:
        _apply_production_overrides(state, data["production"])
    if "barracks" in data:
        _apply_barracks_overrides(state, data["barracks"])
    _sync_front_supplies(state)

    return state


def _apply_logistics_overrides(state: GameState, logistics_data: dict) -> None:
    if not isinstance(logistics_data, dict):
        return
    if "depot_stocks" in logistics_data:
        stocks = logistics_data["depot_stocks"]
        for depot_name, stock_dict in stocks.items():
            try:
                legacy_map = {
                    "CORE": LocationId.NEW_SYSTEM_CORE,
                    "MID": LocationId.CONTESTED_MID_DEPOT,
                    "MID_DEPOT": LocationId.CONTESTED_MID_DEPOT,
                    "SPACEPORT": LocationId.CONTESTED_SPACEPORT,
                    "DEEP": LocationId.DEEP_SPACE,
                    "FRONT": LocationId.CONTESTED_FRONT,
                }
                normalized_name = depot_name.upper().replace(" ", "_")
                depot = legacy_map.get(normalized_name) or LocationId(normalized_name.lower())
                state.logistics.depot_stocks[depot] = Supplies(
                    ammo=int(stock_dict.get("ammo", 0)),
                    fuel=int(stock_dict.get("fuel", 0)),
                    med_spares=int(stock_dict.get("med_spares", 0)),
                )
            except (KeyError, ValueError):
                pass


def _apply_production_overrides(state: GameState, prod_data: dict) -> None:
    if not isinstance(prod_data, dict):
        return
    if "factories" in prod_data:
        state.production.factories = int(prod_data["factories"])
    elif "capacity" in prod_data:
        state.production.factories = int(prod_data["capacity"])


def _apply_barracks_overrides(state: GameState, barracks_data: dict) -> None:
    if not isinstance(barracks_data, dict):
        return
    if "barracks" in barracks_data:
        state.barracks.barracks = int(barracks_data["barracks"])


def _sync_front_supplies(state: GameState) -> None:
    state.task_force.supplies = state.logistics.depot_stocks[LocationId.CONTESTED_FRONT]


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
    control = None
    if "control" in planet:
        try:
            control = float(planet.get("control"))
        except (TypeError, ValueError):
            control = None

    scenario_map = _parse_map(data.get("map"))
    task_force_start = _parse_task_force_start(data.get("task_force_start"))
    foundry_mvp = _parse_foundry_mvp(data.get("foundry_mvp"))

    return ScenarioData(
        seed=seed,
        enemy_infantry=infantry,
        enemy_walkers=walkers,
        enemy_support=support,
        enemy_cohesion=float(cohesion),
        fortification=float(fortification),
        reinforcement_rate=float(reinforcement_rate),
        intel_confidence=float(confidence),
        control=control,
        map=scenario_map,
        task_force_start=task_force_start,
        foundry_mvp=foundry_mvp,
    )


def _parse_task_force_start(data: object) -> TaskForceStartConfig:
    if not isinstance(data, dict):
        return TaskForceStartConfig(
            infantry=120,
            walkers=2,
            support=1,
            readiness=1.0,
            cohesion=1.0,
        )
    infantry = int(data.get("infantry", 120))
    walkers = int(data.get("walkers", 2))
    support = int(data.get("support", 1))
    readiness = float(data.get("readiness", 1.0))
    cohesion = float(data.get("cohesion", 1.0))
    return TaskForceStartConfig(
        infantry=max(0, infantry),
        walkers=max(0, walkers),
        support=max(0, support),
        readiness=max(0.0, min(1.0, readiness)),
        cohesion=max(0.0, min(1.0, cohesion)),
    )


def _parse_foundry_mvp(data: object) -> FoundryMvpConfig | None:
    if not isinstance(data, dict):
        return None
    enemy_force_data = data.get("enemy_force")
    if not isinstance(enemy_force_data, dict):
        return None
    infantry = int(enemy_force_data.get("infantry", 12000))
    walkers = int(enemy_force_data.get("walkers", 180))
    support = int(enemy_force_data.get("support", 1200))
    cohesion = float(enemy_force_data.get("cohesion", 0.92))
    fortification = float(enemy_force_data.get("fortification", 1.35))
    return FoundryMvpConfig(
        enemy_force=FoundryMvpEnemyForce(
            infantry=max(0, infantry),
            walkers=max(0, walkers),
            support=max(0, support),
            cohesion=max(0.0, min(1.0, cohesion)),
            fortification=max(0.5, fortification),
        )
    )


def _parse_map(data: object) -> ScenarioMap | None:
    if not isinstance(data, dict):
        return None
    nodes_raw = data.get("nodes", [])
    groups_raw = data.get("strategicGroups", [])
    nodes: list[ScenarioMapNode] = []
    for item in nodes_raw:
        if not isinstance(item, dict):
            continue
        pos = item.get("position", {})
        nodes.append(
            ScenarioMapNode(
                id=str(item.get("id", "")),
                label=str(item.get("label", "")),
                kind=str(item.get("kind", "tactical")),
                description=str(item.get("description", "")),
                x=float(pos.get("x", 0)),
                y=float(pos.get("y", 0)),
            )
        )
    groups: list[ScenarioMapGroup] = []
    for item in groups_raw:
        if not isinstance(item, dict):
            continue
        group_nodes = item.get("nodeIds", [])
        if not isinstance(group_nodes, list):
            group_nodes = []
        groups.append(
            ScenarioMapGroup(
                id=str(item.get("id", "")),
                node_ids=[str(n) for n in group_nodes],
                label=str(item.get("label", "")),
                kind=str(item.get("kind", "contested")),
            )
        )
    if not nodes:
        return None
    return ScenarioMap(nodes=nodes, groups=groups)


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
        raise ScenarioError(
            f"planet.objectives ids must be {sorted(required)} ({detail_text})"
        )


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
