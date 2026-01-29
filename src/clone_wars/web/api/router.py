from __future__ import annotations

from fastapi import APIRouter, Request, Response

from clone_wars.engine.actions import ActionError, ActionManager, ActionType, PlayerAction, ShipmentPayload
from clone_wars.engine.barracks import BarracksJobType
from clone_wars.engine.ops import (
    OperationIntent,
    OperationTarget,
    OperationTypeId,
    Phase1Decisions,
    Phase2Decisions,
    Phase3Decisions,
)
from clone_wars.engine.production import ProductionJobType
from clone_wars.engine.types import LocationId, Supplies, UnitStock
from clone_wars.web.api import mappers, schemas
from clone_wars.web.session import get_or_create_session

router = APIRouter(prefix="/api")


def _parse_location(value: str) -> LocationId:
    try:
        return LocationId(value)
    except ValueError as exc:
        raise ValueError(f"Unknown location: {value}") from exc


def _parse_target(value: str) -> OperationTarget:
    for target in OperationTarget:
        if target.value == value:
            return target
    raise ValueError(f"Unknown target: {value}")


def _parse_op_type(value: str) -> OperationTypeId:
    try:
        return OperationTypeId(value)
    except ValueError as exc:
        raise ValueError(f"Unknown operation type: {value}") from exc


def _build_response(state, *, ok: bool, message: str | None = None, kind: str = "info") -> schemas.ApiResponse:
    payload = schemas.ApiResponse(ok=ok, message=message, message_kind=kind)
    if state is not None:
        payload.state = mappers.build_state_response(state)
    return payload


@router.get("/state", response_model=schemas.GameStateResponse)
async def get_state(request: Request, response: Response):
    session_id, session = get_or_create_session(request.cookies.get("session_id"))
    async with session.lock:
        data = mappers.build_state_response(session.state)
    response.set_cookie("session_id", session_id, httponly=True)
    return data


@router.post("/nav", response_model=schemas.ApiResponse)
async def set_nav(request: Request, response: Response):
    session_id, session = get_or_create_session(request.cookies.get("session_id"))
    response.set_cookie("session_id", session_id, httponly=True)
    async with session.lock:
        return _build_response(session.state, ok=True, message="Navigation updated", kind="info")


@router.post("/actions/dispatch", response_model=schemas.ApiResponse)
async def dispatch_shipment(payload: schemas.DispatchRequest, request: Request, response: Response):
    session_id, session = get_or_create_session(request.cookies.get("session_id"))
    response.set_cookie("session_id", session_id, httponly=True)
    async with session.lock:
        try:
            origin = _parse_location(payload.origin)
            destination = _parse_location(payload.destination)
            supplies = Supplies(
                ammo=payload.supplies.ammo,
                fuel=payload.supplies.fuel,
                med_spares=payload.supplies.med_spares,
            )
            units = UnitStock(
                infantry=payload.units.infantry,
                walkers=payload.units.walkers,
                support=payload.units.support,
            )
            mgr = ActionManager(session.state)
            mgr.perform_action(
                PlayerAction(
                    ActionType.DISPATCH_SHIPMENT,
                    payload=ShipmentPayload(origin=origin, destination=destination, supplies=supplies, units=units),
                )
            )
            return _build_response(session.state, ok=True, message="Shipment dispatched", kind="accent")
        except (ActionError, ValueError) as exc:
            return _build_response(session.state, ok=False, message=str(exc), kind="error")


@router.post("/actions/production", response_model=schemas.ApiResponse)
async def queue_production(payload: schemas.ProductionRequest, request: Request, response: Response):
    session_id, session = get_or_create_session(request.cookies.get("session_id"))
    response.set_cookie("session_id", session_id, httponly=True)
    async with session.lock:
        try:
            job_type = ProductionJobType(payload.job_type)
            session.state.production.queue_job(job_type, payload.quantity)
            return _build_response(session.state, ok=True, message="Factory job queued", kind="accent")
        except ValueError as exc:
            return _build_response(session.state, ok=False, message=str(exc), kind="error")


@router.post("/actions/barracks", response_model=schemas.ApiResponse)
async def queue_barracks(payload: schemas.ProductionRequest, request: Request, response: Response):
    session_id, session = get_or_create_session(request.cookies.get("session_id"))
    response.set_cookie("session_id", session_id, httponly=True)
    async with session.lock:
        try:
            job_type = BarracksJobType(payload.job_type)
            session.state.barracks.queue_job(job_type, payload.quantity)
            return _build_response(session.state, ok=True, message="Barracks job queued", kind="accent")
        except ValueError as exc:
            return _build_response(session.state, ok=False, message=str(exc), kind="error")


@router.post("/actions/upgrade-factory", response_model=schemas.ApiResponse)
async def upgrade_factory(request: Request, response: Response):
    session_id, session = get_or_create_session(request.cookies.get("session_id"))
    response.set_cookie("session_id", session_id, httponly=True)
    async with session.lock:
        try:
            mgr = ActionManager(session.state)
            mgr.perform_action(PlayerAction(ActionType.UPGRADE_FACTORY))
            return _build_response(session.state, ok=True, message="Factory upgraded", kind="accent")
        except (ActionError, ValueError) as exc:
            return _build_response(session.state, ok=False, message=str(exc), kind="error")


@router.post("/actions/upgrade-barracks", response_model=schemas.ApiResponse)
async def upgrade_barracks(request: Request, response: Response):
    session_id, session = get_or_create_session(request.cookies.get("session_id"))
    response.set_cookie("session_id", session_id, httponly=True)
    async with session.lock:
        try:
            mgr = ActionManager(session.state)
            mgr.perform_action(PlayerAction(ActionType.UPGRADE_BARRACKS))
            return _build_response(session.state, ok=True, message="Barracks upgraded", kind="accent")
        except (ActionError, ValueError) as exc:
            return _build_response(session.state, ok=False, message=str(exc), kind="error")


@router.post("/actions/advance-day", response_model=schemas.ApiResponse)
async def advance_day(request: Request, response: Response):
    session_id, session = get_or_create_session(request.cookies.get("session_id"))
    response.set_cookie("session_id", session_id, httponly=True)
    async with session.lock:
        state = session.state
        if state.raid_session is not None:
            return _build_response(state, ok=False, message="Raid in progress", kind="error")
        if state.operation is not None:
            op = state.operation
            if op.pending_phase_record is not None:
                return _build_response(state, ok=False, message="Acknowledge phase report", kind="error")
            if op.awaiting_player_decision:
                return _build_response(state, ok=False, message="Awaiting phase orders", kind="error")
        state.advance_day()
        state.action_points = 3
        return _build_response(state, ok=True, message="Day advanced", kind="info")


@router.post("/actions/operation/start", response_model=schemas.ApiResponse)
async def start_operation(payload: schemas.OperationStartRequest, request: Request, response: Response):
    session_id, session = get_or_create_session(request.cookies.get("session_id"))
    response.set_cookie("session_id", session_id, httponly=True)
    async with session.lock:
        try:
            target = _parse_target(payload.target)
            op_type = _parse_op_type(payload.op_type)
            mgr = ActionManager(session.state)
            if op_type == OperationTypeId.RAID:
                mgr.perform_action(PlayerAction(ActionType.START_RAID, payload=target))
                return _build_response(session.state, ok=True, message="Raid launched", kind="accent")
            intent = OperationIntent(target=target, op_type=op_type)
            mgr.perform_action(PlayerAction(ActionType.START_OPERATION, payload=intent))
            return _build_response(session.state, ok=True, message="Operation launched", kind="accent")
        except (ActionError, ValueError, RuntimeError) as exc:
            return _build_response(session.state, ok=False, message=str(exc), kind="error")


@router.post("/actions/operation/decisions", response_model=schemas.ApiResponse)
async def submit_phase_decisions(payload: schemas.PhaseDecisionRequest, request: Request, response: Response):
    session_id, session = get_or_create_session(request.cookies.get("session_id"))
    response.set_cookie("session_id", session_id, httponly=True)
    async with session.lock:
        state = session.state
        if state.operation is None:
            return _build_response(state, ok=False, message="No active operation", kind="error")
        try:
            phase = state.operation.current_phase
            if phase.value == "contact_shaping":
                if not payload.axis or not payload.fire:
                    raise ValueError("Missing phase 1 decisions")
                decisions = Phase1Decisions(approach_axis=payload.axis, fire_support_prep=payload.fire)
            elif phase.value == "engagement":
                if not payload.posture or not payload.risk:
                    raise ValueError("Missing phase 2 decisions")
                decisions = Phase2Decisions(engagement_posture=payload.posture, risk_tolerance=payload.risk)
            else:
                if not payload.focus or not payload.end_state:
                    raise ValueError("Missing phase 3 decisions")
                decisions = Phase3Decisions(exploit_vs_secure=payload.focus, end_state=payload.end_state)
            state.submit_phase_decisions(decisions)
            return _build_response(state, ok=True, message="Phase orders submitted", kind="accent")
        except (ValueError, RuntimeError, TypeError) as exc:
            return _build_response(state, ok=False, message=str(exc), kind="error")


@router.post("/actions/operation/ack-phase", response_model=schemas.ApiResponse)
async def acknowledge_phase(request: Request, response: Response):
    session_id, session = get_or_create_session(request.cookies.get("session_id"))
    response.set_cookie("session_id", session_id, httponly=True)
    async with session.lock:
        state = session.state
        if state.operation is None or state.operation.pending_phase_record is None:
            return _build_response(state, ok=False, message="No phase report", kind="error")
        state.acknowledge_phase_result()
        return _build_response(state, ok=True, message="Phase acknowledged", kind="info")


@router.post("/actions/raid/tick", response_model=schemas.ApiResponse)
async def raid_tick(request: Request, response: Response):
    session_id, session = get_or_create_session(request.cookies.get("session_id"))
    response.set_cookie("session_id", session_id, httponly=True)
    async with session.lock:
        try:
            session.state.advance_raid_tick()
            return _build_response(session.state, ok=True, message="Raid tick advanced", kind="info")
        except RuntimeError as exc:
            return _build_response(session.state, ok=False, message=str(exc), kind="error")


@router.post("/actions/raid/resolve", response_model=schemas.ApiResponse)
async def raid_resolve(request: Request, response: Response):
    session_id, session = get_or_create_session(request.cookies.get("session_id"))
    response.set_cookie("session_id", session_id, httponly=True)
    async with session.lock:
        try:
            session.state.resolve_active_raid()
            return _build_response(session.state, ok=True, message="Raid resolved", kind="accent")
        except RuntimeError as exc:
            return _build_response(session.state, ok=False, message=str(exc), kind="error")


@router.post("/actions/raid/start", response_model=schemas.ApiResponse)
async def raid_start(payload: schemas.OperationStartRequest, request: Request, response: Response):
    session_id, session = get_or_create_session(request.cookies.get("session_id"))
    response.set_cookie("session_id", session_id, httponly=True)
    async with session.lock:
        try:
            target = _parse_target(payload.target)
            mgr = ActionManager(session.state)
            mgr.perform_action(PlayerAction(ActionType.START_RAID, payload=target))
            return _build_response(session.state, ok=True, message="Raid launched", kind="accent")
        except (ActionError, ValueError, RuntimeError) as exc:
            return _build_response(session.state, ok=False, message=str(exc), kind="error")


@router.post("/actions/ack-aar", response_model=schemas.ApiResponse)
async def acknowledge_aar(request: Request, response: Response):
    session_id, session = get_or_create_session(request.cookies.get("session_id"))
    response.set_cookie("session_id", session_id, httponly=True)
    async with session.lock:
        session.state.last_aar = None
        return _build_response(session.state, ok=True, message="AAR acknowledged", kind="info")
