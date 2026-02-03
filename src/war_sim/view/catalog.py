from __future__ import annotations

from war_sim.rules.ruleset import Ruleset
from war_sim.rules.scenario import ScenarioData


def build_catalog(rules: Ruleset, scenario: ScenarioData) -> dict:
    def labelize(value: str) -> str:
        return value.replace("_", " ").title()

    operation_targets = [
        {"id": "foundry", "label": "Droid Foundry"},
        {"id": "comms", "label": "Communications Array"},
        {"id": "power", "label": "Power Plant"},
    ]

    operation_types = [
        {"id": op.id, "label": op.name} for op in rules.operation_types.values()
    ]

    return {
        "operationTargets": operation_targets,
        "operationTypes": operation_types,
        "decisions": {
            "phase1": {
                "approachAxis": [
                    {"id": key, "label": labelize(key)}
                    for key in rules.approach_axes.keys()
                ],
                "fireSupportPrep": [
                    {"id": key, "label": labelize(key)}
                    for key in rules.fire_support_prep.keys()
                ],
            },
            "phase2": {
                "engagementPosture": [
                    {"id": key, "label": labelize(key)}
                    for key in rules.engagement_postures.keys()
                ],
                "riskTolerance": [
                    {"id": key, "label": labelize(key)}
                    for key in rules.risk_tolerances.keys()
                ],
            },
            "phase3": {
                "exploitVsSecure": [
                    {"id": key, "label": labelize(key)}
                    for key in rules.exploit_vs_secure.keys()
                ],
                "endState": [
                    {"id": key, "label": labelize(key)} for key in rules.end_states.keys()
                ],
            },
        },
        "objectives": [
            {"id": obj.id, "label": obj.name, "description": obj.description}
            for obj in rules.objectives.values()
        ],
    }
