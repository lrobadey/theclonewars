from __future__ import annotations

from war_sim.rules.ruleset import Ruleset
from war_sim.rules.scenario import ScenarioData


def build_catalog(rules: Ruleset, scenario: ScenarioData) -> dict:
    def labelize(value: str) -> str:
        return value.replace("_", " ").title()

    def availability_for_operation(op_id: str) -> dict:
        if op_id == "campaign":
            return {"enabled": True}
        return {
            "enabled": False,
            "reason": "MVP currently supports Campaign operations only.",
        }

    def compute_impact(values: dict[str, float]) -> dict:
        progress = float(values.get("progress_mod", values.get("progress_mult", 1.0) - 1.0))
        if "required_progress" in values:
            progress = float(values["required_progress"]) - 0.7
        losses = float(values.get("loss_mod", 0.0))
        if "readiness_delta" in values:
            losses = float(values["readiness_delta"]) * -1.0
        variance_base = values.get("variance_mult", values.get("variance_multiplier", 1.0))
        variance = float(variance_base - 1.0)
        ammo_mult = float(values.get("ammo_mult", 1.0))
        fuel_mult = float(values.get("fuel_mult", 1.0))
        med_mult = float(values.get("med_mult", 1.0))
        supplies = ((ammo_mult + fuel_mult + med_mult) / 3.0) - 1.0
        fortification = float(values.get("fort_erosion_mult", 1.0) - 1.0)
        if "fortification_reduction" in values:
            fortification = float(values["fortification_reduction"])
        return {
            "progress": round(progress, 3),
            "losses": round(losses, 3),
            "variance": round(variance, 3),
            "supplies": round(supplies, 3),
            "fortification": round(fortification, 3),
        }

    def describe_impact(impact: dict) -> str:
        progress = impact.get("progress", 0.0)
        losses = impact.get("losses", 0.0)
        variance = impact.get("variance", 0.0)
        progress_phrase = "higher progress pressure" if progress > 0 else "lower progress pressure" if progress < 0 else "neutral progress pressure"
        losses_phrase = "higher expected losses" if losses > 0 else "lower expected losses" if losses < 0 else "neutral loss profile"
        variance_phrase = "higher volatility" if variance > 0 else "lower volatility" if variance < 0 else "steady volatility"
        return f"{progress_phrase}; {losses_phrase}; {variance_phrase}."

    def decision_options(group: dict[str, dict[str, float]]) -> list[dict]:
        options = []
        for key, values in group.items():
            impact = compute_impact(values)
            options.append(
                {
                    "id": key,
                    "label": labelize(key),
                    "description": describe_impact(impact),
                    "impact": impact,
                }
            )
        return options

    operation_targets = [
        {"id": obj.id, "label": obj.name}
        for obj in rules.objectives.values()
    ]
    operation_types = [
        {
            "id": op.id,
            "label": op.name,
            "description": (
                f"{op.base_duration_days}d base duration, progress target {op.required_progress:.0%}, "
                f"supply multiplier {op.supply_cost_multiplier:.2f}x"
            ),
            "availability": availability_for_operation(op.id),
        }
        for op in rules.operation_types.values()
    ]

    return {
        "operationTargets": operation_targets,
        "operationTypes": operation_types,
        "decisions": {
            "phase1": {
                "approachAxis": decision_options(rules.approach_axes),
                "fireSupportPrep": decision_options(rules.fire_support_prep),
            },
            "phase2": {
                "engagementPosture": decision_options(rules.engagement_postures),
                "riskTolerance": decision_options(rules.risk_tolerances),
            },
            "phase3": {
                "exploitVsSecure": decision_options(rules.exploit_vs_secure),
                "endState": decision_options(rules.end_states),
            },
        },
        "objectives": [
            {"id": obj.id, "label": obj.name, "description": obj.description}
            for obj in rules.objectives.values()
        ],
    }
