from __future__ import annotations

from dataclasses import dataclass, field

from clone_wars.engine.types import LocationId, Supplies, UnitStock
from clone_wars.engine.ops import (
    OperationIntent,
    OperationPhase,
    OperationTarget,
    OperationTypeId,
    Phase1Decisions,
    Phase2Decisions,
    Phase3Decisions,
)
from clone_wars.engine.barracks import BarracksJobType
from clone_wars.engine.production import ProductionJobType
from clone_wars.engine.state import GameState
 


def _ui_dirty_for_action(action_id: str) -> set[str]:
    """
    Returns the set of web dashboard panels that should be re-rendered after an action.

    The new layout renders a single viewport plus the global header and navigator.
    """
    dirty: set[str] = {"viewport"}

    if action_id.startswith("view-"):
        dirty.add("navigator")
        return dirty

    if action_id.startswith("focus-"):
        return dirty

    if action_id.startswith("map-select-"):
        return dirty

    # Most stateful actions should refresh header + viewport.
    dirty.add("header")
    return dirty


@dataclass
class ConsoleController:
    mode: str = "menu"
    target: OperationTarget | None = None
    op_type: OperationTypeId = OperationTypeId.CAMPAIGN
    plan_draft: dict[str, str] = field(default_factory=dict)
    pending_route: tuple[LocationId, LocationId] | None = None
    prod_category: str | None = None
    prod_job_type: ProductionJobType | None = None
    prod_quantity: int = 0
    barracks_job_type: BarracksJobType | None = None
    barracks_quantity: int = 0
    message: str | None = None
    message_kind: str = "info"
    raid_auto: bool = False
    view_mode: str = "core"
    selected_node: LocationId | None = LocationId.CONTESTED_FRONT

    def _reset_production_state(self) -> None:
        self.prod_category = None
        self.prod_job_type = None
        self.prod_quantity = 0

    def _reset_barracks_state(self) -> None:
        self.barracks_job_type = None
        self.barracks_quantity = 0

    def _reset_logistics_state(self) -> None:
        self.pending_route = None

    def _set_message(self, text: str | None, kind: str = "info") -> None:
        self.message = text
        self.message_kind = kind

    def _set_phase_decision_mode(self, phase: OperationPhase) -> None:
        if phase == OperationPhase.CONTACT_SHAPING:
            if "approach_axis" in self.plan_draft:
                self.mode = "plan:prep"
            else:
                self.mode = "plan:axis"
        elif phase == OperationPhase.ENGAGEMENT:
            if "engagement_posture" in self.plan_draft:
                self.mode = "plan:risk"
            else:
                self.mode = "plan:posture"
        elif phase == OperationPhase.EXPLOIT_CONSOLIDATE:
            if "exploit_vs_secure" in self.plan_draft:
                self.mode = "plan:end"
            else:
                self.mode = "plan:exploit"

    def _start_operation(self, state: GameState, op_type: OperationTypeId) -> None:
        if self.target is None:
            self._set_message("NO TARGET SELECTED", "error")
            self.mode = "menu"
            return
        if op_type == OperationTypeId.RAID:
            self._set_message("USE RAID ACTION FOR RAIDS", "error")
            self.mode = "sector"
            return
        if state.operation is not None or state.raid_session is not None:
            self._set_message("OPERATION ALREADY ACTIVE", "error")
            self.mode = "menu"
            return
        if state.action_points < 1:
            self._set_message("NOT ENOUGH ACTION POINTS (NEED 1)", "error")
            self.mode = "menu"
            return
        intent = OperationIntent(target=self.target, op_type=op_type)
        try:
            state.start_operation_phased(intent)
        except RuntimeError as exc:
            self._set_message(str(exc).upper(), "error")
            self.mode = "menu"
            return
        state.action_points -= 1
        self.op_type = op_type
        self.plan_draft.clear()
        self._set_message("OPERATION LAUNCHED", "accent")
        self.mode = "plan:axis"

    def _ensure_phase(self, state: GameState, phase: OperationPhase) -> bool:
        op = state.operation
        if op is None:
            self._set_message("NO ACTIVE OPERATION", "error")
            self.mode = "menu"
            return False
        if op.pending_phase_record is not None:
            self._set_message("ACKNOWLEDGE PHASE REPORT", "error")
            self.mode = "op:report"
            return False
        if not op.awaiting_player_decision:
            self._set_message("PHASE IN PROGRESS", "error")
            self.mode = "menu"
            return False
        if op.current_phase != phase:
            self._set_message("WRONG PHASE", "error")
            self._set_phase_decision_mode(op.current_phase)
            return False
        return True

    def sync_with_state(self, state: GameState) -> None:
        if state.last_aar is not None and self.mode != "aar":
            self.mode = "aar"
        if state.raid_session is not None and self.mode != "raid":
            self.mode = "raid"
        if self.mode == "aar" and state.last_aar is None:
            self.mode = "menu"
        if self.mode == "raid" and state.raid_session is None and state.last_aar is None:
            self.mode = "menu"
        if state.raid_session is None:
            self.raid_auto = False
        if self.mode == "logistics:package" and self.pending_route is None:
            self.mode = "logistics"
        if self.mode == "sector" and self.target is None:
            self.mode = "menu"
        if (
            self.mode.startswith("plan:")
            and self.target is None
            and self.mode != "plan:target"
            and state.operation is None
        ):
            self.mode = "plan:target"
        if self.mode == "production:item" and self.prod_category is None:
            self.mode = "production"
        if self.mode in {"production:quantity", "production:stop"} and self.prod_job_type is None:
            self.mode = "production"
        if self.mode in {"barracks:quantity", "barracks:stop"} and self.barracks_job_type is None:
            self.mode = "barracks"
        if state.operation is not None:
            op = state.operation
            if op.pending_phase_record is not None:
                self.mode = "op:report"
            elif op.awaiting_player_decision:
                self._set_phase_decision_mode(op.current_phase)
            elif self.mode in {
                "plan:axis",
                "plan:prep",
                "plan:posture",
                "plan:risk",
                "plan:exploit",
                "plan:end",
                "op:report",
            }:
                self.mode = "menu"
        elif self.mode in {
            "plan:axis",
            "plan:prep",
            "plan:posture",
            "plan:risk",
            "plan:exploit",
            "plan:end",
            "op:report",
        }:
            self.mode = "menu"

        # Sync viewport mode with active interaction flows.
        if self.mode.startswith("production") or self.mode.startswith("barracks"):
            self.view_mode = "core"
        elif self.mode.startswith("logistics"):
            self.view_mode = "deep"
        elif self.mode in {"sector", "raid", "aar", "op:report"} or self.mode.startswith("plan:"):
            self.view_mode = "tactical"

    def open_sector(self, target: OperationTarget, state: GameState) -> None:
        if state.operation is not None or state.raid_session is not None:
            self._set_message("OPERATION ALREADY ACTIVE", "error")
            self.mode = "menu"
            return
        self.target = target
        self.op_type = OperationTypeId.CAMPAIGN
        self.mode = "sector"

    def dispatch(self, action_id: str, payload: dict[str, str], state: GameState) -> set[str]:
        if not action_id:
            return {"viewport"}

        dirty = _ui_dirty_for_action(action_id)

        if action_id == "view-core":
            self.view_mode = "core"
            if self.mode.startswith("logistics"):
                self._reset_logistics_state()
                self.mode = "menu"
            dirty.add("navigator")
            return dirty
        if action_id == "view-deep":
            self.view_mode = "deep"
            if self.mode.startswith("production"):
                self._reset_production_state()
                self.mode = "menu"
            if self.mode.startswith("barracks"):
                self._reset_barracks_state()
                self.mode = "menu"
            dirty.add("navigator")
            return dirty
        if action_id == "view-tactical":
            self.view_mode = "tactical"
            if self.mode.startswith("production"):
                self._reset_production_state()
                self.mode = "menu"
            if self.mode.startswith("barracks"):
                self._reset_barracks_state()
                self.mode = "menu"
            elif self.mode.startswith("logistics"):
                self._reset_logistics_state()
                self.mode = "menu"
            dirty.add("navigator")
            return dirty

        if action_id == "focus-spaceport":
            self.selected_node = LocationId.CONTESTED_SPACEPORT
            self.view_mode = "tactical"
            return dirty
        if action_id == "focus-mid":
            self.selected_node = LocationId.CONTESTED_MID_DEPOT
            self.view_mode = "tactical"
            return dirty
        if action_id == "focus-front":
            self.selected_node = LocationId.CONTESTED_FRONT
            self.view_mode = "tactical"
            return dirty

        if action_id == "btn-plan":
            self.mode = "plan:target"
            self.view_mode = "tactical"
        elif action_id == "btn-next":
            if state.raid_session is not None:
                self._set_message("RAID IN PROGRESS", "error")
                self.mode = "raid"
                return dirty
            if state.operation is not None:
                op = state.operation
                if op.pending_phase_record is not None:
                    self._set_message("ACKNOWLEDGE PHASE REPORT", "error")
                    self.mode = "op:report"
                    return dirty
                if op.awaiting_player_decision:
                    self._set_message("AWAITING PHASE ORDERS", "error")
                    self._set_phase_decision_mode(op.current_phase)
                    return dirty
            state.advance_day()
            state.action_points = 3
            self._set_message("DAY ADVANCED", "info")
        elif action_id == "btn-sector-back":
            self.target = None
            self.op_type = OperationTypeId.CAMPAIGN
            self.mode = "menu"
        elif action_id == "btn-cancel":
            self._reset_logistics_state()
            if self.mode.startswith("plan:"):
                self.plan_draft.clear()
                self.target = None
                self.op_type = OperationTypeId.CAMPAIGN
            self._reset_production_state()
            self._reset_barracks_state()
            self.mode = "menu"
        elif action_id == "btn-ack":
            state.last_aar = None
            self.mode = "menu"
            self.raid_auto = False
        elif action_id == "btn-phase-ack":
            if state.operation is None or state.operation.pending_phase_record is None:
                self._set_message("NO PHASE REPORT", "error")
                self.mode = "menu"
            else:
                state.acknowledge_phase_result()
                self.plan_draft.clear()
                if state.operation is None and state.last_aar is not None:
                    self.mode = "aar"
                elif state.operation is not None:
                    self._set_phase_decision_mode(state.operation.current_phase)
                else:
                    self.mode = "menu"
        elif action_id == "btn-production":
            self.prod_category = None
            self.prod_job_type = None
            self.prod_quantity = 0
            self.mode = "production"
            self.view_mode = "core"
            dirty.add("navigator")
        elif action_id == "btn-barracks":
            self._reset_barracks_state()
            self.mode = "barracks"
            self.view_mode = "core"
            dirty.add("navigator")
        elif action_id == "btn-logistics":
            self.mode = "logistics"
            self.view_mode = "deep"
            dirty.add("navigator")

        elif action_id.startswith("map-"):
            target_map = {
                "map-foundry": OperationTarget.FOUNDRY,
                "map-comms": OperationTarget.COMMS,
                "map-power": OperationTarget.POWER,
            }
            target = target_map.get(action_id)
            if target is not None:
                self.open_sector(target, state)
                self.view_mode = "tactical"

        elif action_id == "btn-raid":
            if self.target is None:
                self._set_message("NO TARGET SELECTED", "error")
                self.mode = "menu"
            else:
                if state.action_points < 1:
                    self._set_message("NOT ENOUGH ACTION POINTS (NEED 1)", "error")
                    self.mode = "menu"
                    return dirty

                try:
                    self.raid_auto = False
                    state.start_raid(self.target)
                except RuntimeError as exc:
                    self._set_message(str(exc).upper(), "error")
                    self.mode = "menu"
                else:
                    state.action_points -= 1
                    self._set_message("RAID STARTED", "accent")
                    self.mode = "raid"
                    self.view_mode = "tactical"

        elif action_id == "btn-raid-tick":
            try:
                state.advance_raid_tick()
            except RuntimeError as exc:
                self._set_message(str(exc).upper(), "error")
                self.mode = "menu"
            else:
                if state.raid_session is None and state.last_aar is not None:
                    self.mode = "aar"
                else:
                    self.mode = "raid"
                self.view_mode = "tactical"

        elif action_id == "btn-raid-resolve":
            try:
                self.raid_auto = False
                state.resolve_active_raid()
            except RuntimeError as exc:
                self._set_message(str(exc).upper(), "error")
                self.mode = "menu"
            else:
                self._set_message("RAID RESOLVED", "accent")
                self.mode = "aar"
                self.view_mode = "tactical"
        elif action_id == "btn-raid-auto":
            if state.raid_session is None:
                self._set_message("NO ACTIVE RAID", "error")
                self.mode = "menu"
            else:
                self.raid_auto = not self.raid_auto
                self._set_message("AUTO ADVANCE ON" if self.raid_auto else "AUTO ADVANCE OFF", "info")
                self.mode = "raid"
                self.view_mode = "tactical"

        elif action_id.startswith("sector-"):
            op_map = {
                "sector-raid": OperationTypeId.RAID,
                "sector-campaign": OperationTypeId.CAMPAIGN,
                "sector-siege": OperationTypeId.SIEGE,
            }
            chosen = op_map.get(action_id)
            if chosen is None or self.target is None:
                return dirty
            if chosen == OperationTypeId.RAID:
                if state.action_points < 1:
                    self._set_message("NOT ENOUGH ACTION POINTS (NEED 1)", "error")
                    self.mode = "sector"
                    return dirty
                try:
                    self.raid_auto = False
                    state.start_raid(self.target)
                except RuntimeError as exc:
                    self._set_message(str(exc).upper(), "error")
                    self.mode = "menu"
                else:
                    state.action_points -= 1
                    self._set_message("RAID STARTED", "accent")
                    self.mode = "raid"
                    self.view_mode = "tactical"
            else:
                self._start_operation(state, chosen)
                self.view_mode = "tactical"

        elif action_id.startswith("target-"):
            t_map = {
                "target-foundry": OperationTarget.FOUNDRY,
                "target-comms": OperationTarget.COMMS,
                "target-power": OperationTarget.POWER,
            }
            self.target = t_map.get(action_id)
            self.mode = "plan:type"

        elif action_id.startswith("optype-"):
            op_map = {
                "optype-raid": OperationTypeId.RAID,
                "optype-campaign": OperationTypeId.CAMPAIGN,
                "optype-siege": OperationTypeId.SIEGE,
            }
            chosen = op_map.get(action_id)
            if chosen is None:
                return dirty
            self._start_operation(state, chosen)
            self.view_mode = "tactical"

        elif action_id.startswith("axis-"):
            if not self._ensure_phase(state, OperationPhase.CONTACT_SHAPING):
                return dirty
            self.plan_draft["approach_axis"] = action_id.split("-")[1]
            self.mode = "plan:prep"
            self.view_mode = "tactical"

        elif action_id.startswith("prep-"):
            if not self._ensure_phase(state, OperationPhase.CONTACT_SHAPING):
                return dirty
            self.plan_draft["fire_support_prep"] = action_id.split("-")[1]
            if "approach_axis" not in self.plan_draft:
                self._set_message("SELECT APPROACH AXIS FIRST", "error")
                self.mode = "plan:axis"
                return dirty
            decisions = Phase1Decisions(
                approach_axis=self.plan_draft["approach_axis"],
                fire_support_prep=self.plan_draft["fire_support_prep"],
            )
            try:
                state.submit_phase_decisions(decisions)
            except RuntimeError as exc:
                self._set_message(str(exc).upper(), "error")
                self.mode = "menu"
            else:
                self.plan_draft.clear()
                self._set_message("PHASE 1 ORDERS SUBMITTED", "accent")
                self.mode = "menu"
            self.view_mode = "tactical"

        elif action_id.startswith("posture-"):
            if not self._ensure_phase(state, OperationPhase.ENGAGEMENT):
                return dirty
            self.plan_draft["engagement_posture"] = action_id.split("-")[1]
            self.mode = "plan:risk"
            self.view_mode = "tactical"

        elif action_id.startswith("risk-"):
            if not self._ensure_phase(state, OperationPhase.ENGAGEMENT):
                return dirty
            self.plan_draft["risk_tolerance"] = action_id.split("-")[1]
            if "engagement_posture" not in self.plan_draft:
                self._set_message("SELECT POSTURE FIRST", "error")
                self.mode = "plan:posture"
                return dirty
            decisions = Phase2Decisions(
                engagement_posture=self.plan_draft["engagement_posture"],
                risk_tolerance=self.plan_draft["risk_tolerance"],
            )
            try:
                state.submit_phase_decisions(decisions)
            except RuntimeError as exc:
                self._set_message(str(exc).upper(), "error")
                self.mode = "menu"
            else:
                self.plan_draft.clear()
                self._set_message("PHASE 2 ORDERS SUBMITTED", "accent")
                self.mode = "menu"
            self.view_mode = "tactical"

        elif action_id.startswith("exploit-"):
            if not self._ensure_phase(state, OperationPhase.EXPLOIT_CONSOLIDATE):
                return dirty
            self.plan_draft["exploit_vs_secure"] = action_id.split("-")[1]
            self.mode = "plan:end"
            self.view_mode = "tactical"

        elif action_id.startswith("end-"):
            if not self._ensure_phase(state, OperationPhase.EXPLOIT_CONSOLIDATE):
                return dirty
            self.plan_draft["end_state"] = action_id.split("-")[1]
            if "exploit_vs_secure" not in self.plan_draft:
                self._set_message("SELECT EXPLOIT VS SECURE FIRST", "error")
                self.mode = "plan:exploit"
                return dirty
            decisions = Phase3Decisions(
                exploit_vs_secure=self.plan_draft["exploit_vs_secure"],
                end_state=self.plan_draft["end_state"],
            )
            try:
                state.submit_phase_decisions(decisions)
            except RuntimeError as exc:
                self._set_message(str(exc).upper(), "error")
                self.mode = "menu"
            else:
                self.plan_draft.clear()
                self._set_message("PHASE 3 ORDERS SUBMITTED", "accent")
                self.mode = "menu"
            self.view_mode = "tactical"

        elif action_id == "prod-upgrade-factory":
            if state.action_points < 1:
                self._set_message("NOT ENOUGH ACTION POINTS (NEED 1)", "error")
                return dirty
            try:
                state.production.add_factory()
            except ValueError as exc:
                self._set_message(str(exc).upper(), "error")
                return dirty
            state.action_points -= 1
            self._set_message(
                f"FACTORY UPGRADE COMPLETE (+{state.production.slots_per_factory} SLOTS/DAY)",
                "accent",
            )
            self.mode = "menu"

        elif action_id.startswith("prod-cat-"):
            self.prod_category = "supplies" if action_id == "prod-cat-supplies" else "vehicles"
            self.prod_job_type = None
            self.prod_quantity = 0
            self.mode = "production:item"
            self.view_mode = "core"
            dirty.add("navigator")

        elif action_id.startswith("prod-item-"):
            job_map = {
                "prod-item-ammo": ProductionJobType.AMMO,
                "prod-item-fuel": ProductionJobType.FUEL,
                "prod-item-med": ProductionJobType.MED_SPARES,
                "prod-item-walkers": ProductionJobType.WALKERS,
            }
            job_type = job_map.get(action_id)
            if job_type is None:
                return dirty
            self.prod_job_type = job_type
            self.prod_quantity = 0
            self.mode = "production:quantity"
            self.view_mode = "core"
            dirty.add("navigator")

        elif action_id.startswith("prod-qty-"):
            delta_map = {
                "prod-qty-minus-50": -50,
                "prod-qty-minus-10": -10,
                "prod-qty-minus-1": -1,
                "prod-qty-plus-1": 1,
                "prod-qty-plus-10": 10,
                "prod-qty-plus-50": 50,
            }
            if action_id == "prod-qty-reset":
                self.prod_quantity = 0
                return dirty
            if action_id == "prod-qty-next":
                if self.prod_quantity <= 0:
                    self._set_message("SET A QUANTITY BEFORE CONTINUING", "error")
                    return dirty
                self.mode = "production:stop"
                return dirty
            delta = delta_map.get(action_id)
            if delta is None:
                return dirty
            self.prod_quantity = max(0, self.prod_quantity + delta)
            self.view_mode = "core"
            dirty.add("navigator")

        elif action_id.startswith("prod-stop-"):
            if self.prod_job_type is None:
                return dirty
            if self.prod_quantity <= 0:
                self._set_message("SET A QUANTITY BEFORE QUEUING", "error")
                self.mode = "production:quantity"
                return dirty
            if state.action_points < 1:
                self._set_message("NOT ENOUGH ACTION POINTS (NEED 1)", "error")
                return dirty
            stop_map = {
                "prod-stop-core": LocationId.NEW_SYSTEM_CORE,
                "prod-stop-spaceport": LocationId.CONTESTED_SPACEPORT,
                "prod-stop-mid": LocationId.CONTESTED_MID_DEPOT,
                "prod-stop-front": LocationId.CONTESTED_FRONT,
            }
            stop_at = stop_map.get(action_id)
            if stop_at is None:
                return dirty
            state.production.queue_job(self.prod_job_type, self.prod_quantity, stop_at)
            state.action_points -= 1
            self._set_message(
                f"QUEUED {self.prod_job_type.value.upper()} x{self.prod_quantity:,} -> {stop_at.value.replace('_', ' ').upper()}",
                "info",
            )
            self.prod_category = None
            self.prod_job_type = None
            self.prod_quantity = 0
            self.mode = "menu"
            self.view_mode = "core"
            dirty.add("navigator")

        elif action_id == "prod-back-category":
            self.prod_category = None
            self.prod_job_type = None
            self.prod_quantity = 0
            self.mode = "production"
            self.view_mode = "core"
            dirty.add("navigator")

        elif action_id == "prod-back-item":
            self.prod_job_type = None
            self.prod_quantity = 0
            self.mode = "production:item"
            self.view_mode = "core"
            dirty.add("navigator")

        elif action_id == "prod-back-qty":
            self.mode = "production:quantity"
            self.view_mode = "core"
            dirty.add("navigator")

        elif action_id == "barracks-upgrade":
            if state.action_points < 1:
                self._set_message("NOT ENOUGH ACTION POINTS (NEED 1)", "error")
                return dirty
            try:
                state.barracks.add_barracks()
            except ValueError as exc:
                self._set_message(str(exc).upper(), "error")
                return dirty
            state.action_points -= 1
            self._set_message(
                f"BARRACKS UPGRADE COMPLETE (+{state.barracks.slots_per_barracks} SLOTS/DAY)",
                "accent",
            )
            self.mode = "menu"

        elif action_id.startswith("barracks-item-"):
            job_map = {
                "barracks-item-inf": BarracksJobType.INFANTRY,
                "barracks-item-support": BarracksJobType.SUPPORT,
            }
            job_type = job_map.get(action_id)
            if job_type is None:
                return dirty
            self.barracks_job_type = job_type
            self.barracks_quantity = 0
            self.mode = "barracks:quantity"
            self.view_mode = "core"
            dirty.add("navigator")

        elif action_id.startswith("barracks-qty-"):
            delta_map = {
                "barracks-qty-minus-50": -50,
                "barracks-qty-minus-10": -10,
                "barracks-qty-minus-1": -1,
                "barracks-qty-plus-1": 1,
                "barracks-qty-plus-10": 10,
                "barracks-qty-plus-50": 50,
            }
            if action_id == "barracks-qty-reset":
                self.barracks_quantity = 0
                return dirty
            if action_id == "barracks-qty-next":
                if self.barracks_quantity <= 0:
                    self._set_message("SET A QUANTITY BEFORE CONTINUING", "error")
                    return dirty
                self.mode = "barracks:stop"
                return dirty
            delta = delta_map.get(action_id)
            if delta is None:
                return dirty
            self.barracks_quantity = max(0, self.barracks_quantity + delta)
            self.view_mode = "core"
            dirty.add("navigator")

        elif action_id.startswith("barracks-stop-"):
            if self.barracks_job_type is None:
                return dirty
            if self.barracks_quantity <= 0:
                self._set_message("SET A QUANTITY BEFORE QUEUING", "error")
                self.mode = "barracks:quantity"
                return dirty
            if state.action_points < 1:
                self._set_message("NOT ENOUGH ACTION POINTS (NEED 1)", "error")
                return dirty
            stop_map = {
                "barracks-stop-core": LocationId.NEW_SYSTEM_CORE,
                "barracks-stop-spaceport": LocationId.CONTESTED_SPACEPORT,
                "barracks-stop-mid": LocationId.CONTESTED_MID_DEPOT,
                "barracks-stop-front": LocationId.CONTESTED_FRONT,
            }
            stop_at = stop_map.get(action_id)
            if stop_at is None:
                return dirty
            state.barracks.queue_job(self.barracks_job_type, self.barracks_quantity, stop_at)
            state.action_points -= 1
            self._set_message(
                f"QUEUED {self.barracks_job_type.value.upper()} x{self.barracks_quantity:,} -> {stop_at.value.replace('_', ' ').upper()}",
                "info",
            )
            self._reset_barracks_state()
            self.mode = "menu"
            self.view_mode = "core"
            dirty.add("navigator")

        elif action_id == "barracks-back-item":
            self.barracks_job_type = None
            self.barracks_quantity = 0
            self.mode = "barracks"
            self.view_mode = "core"
            dirty.add("navigator")

        elif action_id == "barracks-back-qty":
            self.mode = "barracks:quantity"
            self.view_mode = "core"
            dirty.add("navigator")

        elif action_id.startswith("route-"):
            route_map = {
                "route-core-spaceport": (LocationId.NEW_SYSTEM_CORE, LocationId.CONTESTED_SPACEPORT),
                "route-core-mid": (LocationId.NEW_SYSTEM_CORE, LocationId.CONTESTED_MID_DEPOT),
                "route-core-front": (LocationId.NEW_SYSTEM_CORE, LocationId.CONTESTED_FRONT),
            }
            route = route_map.get(action_id)
            if route:
                self.pending_route = route
                self.mode = "logistics:package"
                self.view_mode = "deep"
                dirty.add("navigator")

        elif action_id.startswith("ship-"):
            package_map = {
                "ship-mixed-1": (Supplies(ammo=40, fuel=30, med_spares=15), UnitStock(0, 0, 0)),
                "ship-ammo-1": (Supplies(ammo=60, fuel=0, med_spares=0), UnitStock(0, 0, 0)),
                "ship-fuel-1": (Supplies(ammo=0, fuel=50, med_spares=0), UnitStock(0, 0, 0)),
                "ship-med-1": (Supplies(ammo=0, fuel=0, med_spares=30), UnitStock(0, 0, 0)),
                "ship-inf-1": (Supplies(ammo=0, fuel=0, med_spares=0), UnitStock(80, 0, 0)),
                "ship-walk-1": (Supplies(ammo=0, fuel=0, med_spares=0), UnitStock(0, 2, 0)),
                "ship-sup-1": (Supplies(ammo=0, fuel=0, med_spares=0), UnitStock(0, 0, 3)),
                "ship-units-1": (Supplies(ammo=0, fuel=0, med_spares=0), UnitStock(80, 1, 2)),
            }
            package = package_map.get(action_id)
            if package and self.pending_route:
                if state.action_points < 1:
                     self._set_message("NOT ENOUGH ACTION POINTS (NEED 1)", "error")
                     self.mode = "logistics"
                     self.view_mode = "deep"
                     return dirty

                supplies, units = package
                origin, destination = self.pending_route
                try:
                    state.logistics_service.create_shipment(state.logistics, origin, destination, supplies, units, state.rng, current_day=state.day)
                    state.action_points -= 1
                except ValueError as exc:
                    self._set_message(str(exc), "error")
                    self.mode = "logistics"
                    self.view_mode = "deep"
                else:
                    self._set_message(
                        f"SHIPMENT DISPATCHED: {origin.value} -> {destination.value}",
                        "info",
                    )
                    self.pending_route = None
                    self.mode = "menu"
                    self.view_mode = "deep"

        elif action_id == "btn-logistics-back":
            self.pending_route = None
            self.mode = "logistics"
            self.view_mode = "deep"
            dirty.add("navigator")

        elif action_id.startswith("map-select-"):
            node_map = {
                "map-select-core": LocationId.NEW_SYSTEM_CORE,
                "map-select-deep": LocationId.DEEP_SPACE,
                "map-select-spaceport": LocationId.CONTESTED_SPACEPORT,
                "map-select-mid": LocationId.CONTESTED_MID_DEPOT,
                "map-select-front": LocationId.CONTESTED_FRONT,
            }
            node = node_map.get(action_id)
            if node:
                self.selected_node = node
                self.view_mode = "tactical"
                dirty.add("map")

        else:
            self._set_message(f"UNKNOWN ACTION: {action_id}", "error")

        self.sync_with_state(state)
        return dirty
