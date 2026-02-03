"""Data-driven rules engine."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from war_sim.domain.types import LocationId


class RulesError(ValueError):
    """Error loading or validating rules."""


@dataclass(frozen=True)
class SupplyClass:
    """A supply class definition."""

    id: str
    name: str
    shortage_effects: dict[str, float]


@dataclass(frozen=True)
class UnitRole:
    """A unit role definition."""

    id: str
    name: str
    base_power: float
    capabilities: list[str]
    transport_protection: dict[str, Any] | None = None
    sustainment: dict[str, float] | None = None
    recon: dict[str, float] | None = None


@dataclass(frozen=True)
class OperationType:
    """An operation type definition."""

    id: str
    name: str
    base_duration_days: int
    duration_range: tuple[int, int]
    required_progress: float
    supply_cost_multiplier: float


@dataclass(frozen=True)
class ObjectiveDef:
    """An objective definition."""

    id: str
    name: str
    type: str
    base_difficulty: float
    description: str = ""


@dataclass(frozen=True)
class GlobalConfig:
    raid_max_ticks: int
    raid_ammo_cost: int
    raid_fuel_cost: int
    raid_med_cost: int
    raid_base_damage_rate: float
    raid_casualty_rate: float
    ammo_pinch_threshold: float
    walker_screen_infantry_protect: float
    storage_risk_per_day: dict[LocationId, float]
    storage_loss_pct_range: dict[LocationId, tuple[float, float]]


@dataclass(frozen=True)
class ProductionConfig:
    slots_per_factory: int
    max_factories: int
    queue_policy: str
    costs: dict[str, int]


@dataclass(frozen=True)
class BarracksConfig:
    slots_per_barracks: int
    max_barracks: int
    queue_policy: str
    costs: dict[str, int]


@dataclass(frozen=True)
class Ruleset:
    """Loaded and validated ruleset."""

    supply_classes: dict[str, SupplyClass]
    unit_roles: dict[str, UnitRole]
    operation_types: dict[str, OperationType]
    objectives: dict[str, ObjectiveDef]
    approach_axes: dict[str, dict[str, float]]
    fire_support_prep: dict[str, dict[str, float]]
    engagement_postures: dict[str, dict[str, float]]
    risk_tolerances: dict[str, dict[str, float]]
    exploit_vs_secure: dict[str, dict[str, float]]
    end_states: dict[str, dict[str, float]]
    globals: GlobalConfig
    production: ProductionConfig
    barracks: BarracksConfig

    @staticmethod
    def load(data_dir: Path) -> "Ruleset":
        """Load ruleset from JSON files in data directory."""
        supply_classes = _load_supplies(data_dir / "supplies.json")
        unit_roles = _load_unit_roles(data_dir / "unit_roles.json")
        operation_types = _load_operation_types(data_dir / "operation_types.json")
        objectives = _load_objectives(data_dir / "objectives.json")
        operation_rules = _load_operation_rules(data_dir / "operation_types.json")
        global_config = _load_globals(data_dir / "globals.json")
        production_config, barracks_config = _load_production_config(data_dir / "production.json")

        return Ruleset(
            supply_classes=supply_classes,
            unit_roles=unit_roles,
            operation_types=operation_types,
            objectives=objectives,
            approach_axes=operation_rules["approach_axes"],
            fire_support_prep=operation_rules["fire_support_prep"],
            engagement_postures=operation_rules["engagement_postures"],
            risk_tolerances=operation_rules["risk_tolerances"],
            exploit_vs_secure=operation_rules["exploit_vs_secure"],
            end_states=operation_rules["end_states"],
            globals=global_config,
            production=production_config,
            barracks=barracks_config,
        )


def _load_json(path: Path) -> dict[str, Any]:
    """Load JSON file."""
    try:
        with path.open("r", encoding="utf-8") as handle:
            return json.load(handle)
    except FileNotFoundError as exc:
        raise RulesError(f"Rules file not found: {path}") from exc
    except json.JSONDecodeError as exc:
        raise RulesError(f"Invalid JSON in {path}: {exc}") from exc


def _load_supplies(path: Path) -> dict[str, SupplyClass]:
    """Load supply classes."""
    data = _load_json(path)
    if "classes" not in data:
        raise RulesError(f"{path}: missing 'classes' key")
    classes: dict[str, SupplyClass] = {}
    for item in data["classes"]:
        if not isinstance(item, dict):
            raise RulesError(f"{path}: class entry must be object")
        class_id = item.get("id")
        if not isinstance(class_id, str):
            raise RulesError(f"{path}: class.id must be string")
        name = item.get("name", class_id)
        shortage_effects = item.get("shortage_effects", {})
        if not isinstance(shortage_effects, dict):
            raise RulesError(f"{path}: class.shortage_effects must be object")
        classes[class_id] = SupplyClass(
            id=class_id,
            name=str(name),
            shortage_effects={k: float(v) for k, v in shortage_effects.items()},
        )
    return classes


def _load_unit_roles(path: Path) -> dict[str, UnitRole]:
    """Load unit roles."""
    data = _load_json(path)
    if "roles" not in data:
        raise RulesError(f"{path}: missing 'roles' key")
    roles: dict[str, UnitRole] = {}
    for item in data["roles"]:
        if not isinstance(item, dict):
            raise RulesError(f"{path}: role entry must be object")
        role_id = item.get("id")
        if not isinstance(role_id, str):
            raise RulesError(f"{path}: role.id must be string")
        name = item.get("name", role_id)
        base_power = float(item.get("base_power", 1.0))
        capabilities = item.get("capabilities", [])
        if not isinstance(capabilities, list):
            raise RulesError(f"{path}: role.capabilities must be array")
        transport_protection = item.get("transport_protection")
        sustainment = item.get("sustainment")
        recon = item.get("recon")
        roles[role_id] = UnitRole(
            id=role_id,
            name=str(name),
            base_power=base_power,
            capabilities=[str(c) for c in capabilities],
            transport_protection=transport_protection if isinstance(transport_protection, dict) else None,
            sustainment={k: float(v) for k, v in sustainment.items()} if isinstance(sustainment, dict) else None,
            recon={k: float(v) for k, v in recon.items()} if isinstance(recon, dict) else None,
        )
    return roles


def _load_operation_types(path: Path) -> dict[str, OperationType]:
    """Load operation types."""
    data = _load_json(path)
    if "types" not in data:
        raise RulesError(f"{path}: missing 'types' key")
    types: dict[str, OperationType] = {}
    for item in data["types"]:
        if not isinstance(item, dict):
            raise RulesError(f"{path}: type entry must be object")
        type_id = item.get("id")
        if not isinstance(type_id, str):
            raise RulesError(f"{path}: type.id must be string")
        name = item.get("name", type_id)
        base_duration = int(item.get("base_duration_days", 1))
        duration_range = item.get("duration_range", [1, 1])
        if not isinstance(duration_range, list) or len(duration_range) != 2:
            raise RulesError(f"{path}: type.duration_range must be [min, max]")
        required_progress = float(item.get("required_progress", 0.75))
        supply_cost_multiplier = float(item.get("supply_cost_multiplier", 1.0))
        types[type_id] = OperationType(
            id=type_id,
            name=str(name),
            base_duration_days=base_duration,
            duration_range=(int(duration_range[0]), int(duration_range[1])),
            required_progress=required_progress,
            supply_cost_multiplier=supply_cost_multiplier,
        )
    return types


def _load_objectives(path: Path) -> dict[str, ObjectiveDef]:
    """Load objectives."""
    data = _load_json(path)
    if "objectives" not in data:
        raise RulesError(f"{path}: missing 'objectives' key")
    objectives: dict[str, ObjectiveDef] = {}
    for item in data["objectives"]:
        if not isinstance(item, dict):
            raise RulesError(f"{path}: objective entry must be object")
        obj_id = item.get("id")
        if not isinstance(obj_id, str):
            raise RulesError(f"{path}: objective.id must be string")
        name = item.get("name", obj_id)
        obj_type = item.get("type", "strategic")
        base_difficulty = float(item.get("base_difficulty", 1.0))
        description = item.get("description", "")
        if description is None:
            description = ""
        if not isinstance(description, str):
            raise RulesError(f"{path}: objective.description must be string")
        objectives[obj_id] = ObjectiveDef(
            id=obj_id,
            name=str(name),
            type=str(obj_type),
            base_difficulty=base_difficulty,
            description=str(description),
        )
    return objectives


def _load_operation_rules(path: Path) -> dict[str, Any]:
    data = _load_json(path)
    return {
        "approach_axes": data.get("approach_axes", {}),
        "fire_support_prep": data.get("fire_support_prep", {}),
        "engagement_postures": data.get("engagement_postures", {}),
        "risk_tolerances": data.get("risk_tolerances", {}),
        "exploit_vs_secure": data.get("exploit_vs_secure", {}),
        "end_states": data.get("end_states", {}),
    }


def _load_globals(path: Path) -> GlobalConfig:
    data = _load_json(path)
    storage_risk_raw = data.get("storage_risk_per_day", {})
    storage_loss_raw = data.get("storage_loss_pct_range", {})
    return GlobalConfig(
        raid_max_ticks=int(data.get("raid_max_ticks", 12)),
        raid_ammo_cost=int(data.get("raid_ammo_cost", 2)),
        raid_fuel_cost=int(data.get("raid_fuel_cost", 2)),
        raid_med_cost=int(data.get("raid_med_cost", 1)),
        raid_base_damage_rate=float(data.get("raid_base_damage_rate", 0.12)),
        raid_casualty_rate=float(data.get("raid_casualty_rate", 0.02)),
        ammo_pinch_threshold=float(data.get("ammo_pinch_threshold", 0.35)),
        walker_screen_infantry_protect=float(data.get("walker_screen_infantry_protect", 0.65)),
        storage_risk_per_day={LocationId(k): float(v) for k, v in storage_risk_raw.items()},
        storage_loss_pct_range={
            LocationId(k): (float(v[0]), float(v[1])) for k, v in storage_loss_raw.items()
        },
    )


def _load_production_config(path: Path) -> tuple[ProductionConfig, BarracksConfig]:
    data = _load_json(path)
    production_data = data.get("production", data)
    barracks_data = data.get("barracks", data)

    production = ProductionConfig(
        slots_per_factory=int(production_data.get("slots_per_factory", 20)),
        max_factories=int(production_data.get("max_factories", 6)),
        queue_policy=str(production_data.get("queue_policy", "parallel")),
        costs={k: int(v) for k, v in production_data.get("costs", {}).items()},
    )
    barracks = BarracksConfig(
        slots_per_barracks=int(barracks_data.get("slots_per_barracks", 20)),
        max_barracks=int(barracks_data.get("max_barracks", 6)),
        queue_policy=str(barracks_data.get("queue_policy", "parallel")),
        costs={k: int(v) for k, v in barracks_data.get("costs", {}).items()},
    )
    return production, barracks
