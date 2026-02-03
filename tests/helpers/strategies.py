from __future__ import annotations

from hypothesis import strategies as st

from war_sim.domain.ops_models import (
    OperationIntent,
    OperationTarget,
    OperationTypeId,
    Phase1Decisions,
    Phase2Decisions,
    Phase3Decisions,
)
from war_sim.domain.types import Supplies, UnitStock
from war_sim.rules.ruleset import Ruleset


def supplies_strategy(min_val: int = 0, max_val: int = 500) -> st.SearchStrategy[Supplies]:
    return st.builds(
        Supplies,
        ammo=st.integers(min_value=min_val, max_value=max_val),
        fuel=st.integers(min_value=min_val, max_value=max_val),
        med_spares=st.integers(min_value=min_val, max_value=max_val),
    )


def unit_stock_strategy(min_val: int = 0, max_val: int = 200) -> st.SearchStrategy[UnitStock]:
    return st.builds(
        UnitStock,
        infantry=st.integers(min_value=min_val, max_value=max_val),
        walkers=st.integers(min_value=min_val, max_value=max_val),
        support=st.integers(min_value=min_val, max_value=max_val),
    )


def phase1_strategy(rules: Ruleset) -> st.SearchStrategy[Phase1Decisions]:
    return st.builds(
        Phase1Decisions,
        approach_axis=st.sampled_from(sorted(rules.approach_axes.keys())),
        fire_support_prep=st.sampled_from(sorted(rules.fire_support_prep.keys())),
    )


def phase2_strategy(rules: Ruleset) -> st.SearchStrategy[Phase2Decisions]:
    return st.builds(
        Phase2Decisions,
        engagement_posture=st.sampled_from(sorted(rules.engagement_postures.keys())),
        risk_tolerance=st.sampled_from(sorted(rules.risk_tolerances.keys())),
    )


def phase3_strategy(rules: Ruleset) -> st.SearchStrategy[Phase3Decisions]:
    return st.builds(
        Phase3Decisions,
        exploit_vs_secure=st.sampled_from(sorted(rules.exploit_vs_secure.keys())),
        end_state=st.sampled_from(sorted(rules.end_states.keys())),
    )


def operation_intent_strategy(rules: Ruleset) -> st.SearchStrategy[OperationIntent]:
    return st.builds(
        OperationIntent,
        target=st.sampled_from(list(OperationTarget)),
        op_type=st.sampled_from([OperationTypeId(op_id) for op_id in rules.operation_types.keys()]),
    )
