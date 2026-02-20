from __future__ import annotations

from fastapi import APIRouter, Request, Response

from war_sim.domain.actions import (
    AcknowledgeAar,
    AcknowledgePhaseReport,
    AdvanceDay,
    DispatchShipment,
    QueueBarracks,
    QueueProduction,
    StartOperation,
    SubmitPhaseDecisions,
    UpgradeBarracks,
    UpgradeFactory,
)
from war_sim.domain.ops_models import (
    OperationIntent,
    OperationTarget,
    OperationTypeId,
    Phase1Decisions,
    Phase2Decisions,
    Phase3Decisions,
)
from war_sim.domain.types import LocationId, Supplies, UnitStock
from war_sim.sim.reducer import apply_action
from war_sim.view.catalog import build_catalog
from server.api import mappers, schemas
from server.session import get_or_create_session

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
    lowered = value.lower().replace(" ", "_")
    if lowered in ("foundry", "comms", "power"):
        return OperationTarget[lowered.upper()]
    raise ValueError(f"Unknown target: {value}")


def _parse_op_type(value: str) -> OperationTypeId:
    try:
        return OperationTypeId(value)
    except ValueError as exc:
        raise ValueError(f"Unknown operation type: {value}") from exc


def _build_response(
    state, *, ok: bool, message: str | None = None, kind: str = "info"
) -> schemas.ApiResponse:
    payload = schemas.ApiResponse(ok=ok, message=message, message_kind=kind)
    if state is not None:
        payload.state = mappers.build_state_response(state)
    return payload


def _from_result(result) -> schemas.ApiResponse:
    payload = schemas.ApiResponse(
        ok=result.ok,
        message=result.message,
        message_kind=result.message_kind,
    )
    if result.state is not None:
        payload.state = mappers.build_state_response(result.state)
    return payload


@router.get("/health")
async def health():
    return {"status": "ok"}


@router.get("/state", response_model=schemas.GameStateResponse)
async def get_state(request: Request, response: Response):
    session_id, session = get_or_create_session(request.cookies.get("session_id"))
    async with session.lock:
        data = mappers.build_state_response(session.state)
    response.set_cookie("session_id", session_id, httponly=True)
    return data


@router.get("/catalog", response_model=schemas.CatalogResponse)
async def get_catalog(request: Request, response: Response):
    session_id, session = get_or_create_session(request.cookies.get("session_id"))
    async with session.lock:
        data = build_catalog(session.state.rules, session.state.scenario)
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
            result = apply_action(
                session.state,
                DispatchShipment(origin=origin, destination=destination, supplies=supplies, units=units),
            )
            return _from_result(result)
        except ValueError as exc:
            return _build_response(session.state, ok=False, message=str(exc), kind="error")


@router.post("/actions/production", response_model=schemas.ApiResponse)
async def queue_production(payload: schemas.ProductionRequest, request: Request, response: Response):
    session_id, session = get_or_create_session(request.cookies.get("session_id"))
    response.set_cookie("session_id", session_id, httponly=True)
    async with session.lock:
        result = apply_action(
            session.state,
            QueueProduction(job_type=payload.job_type, quantity=payload.quantity, stop_at=LocationId.NEW_SYSTEM_CORE),
        )
        return _from_result(result)


@router.post("/actions/barracks", response_model=schemas.ApiResponse)
async def queue_barracks(payload: schemas.ProductionRequest, request: Request, response: Response):
    session_id, session = get_or_create_session(request.cookies.get("session_id"))
    response.set_cookie("session_id", session_id, httponly=True)
    async with session.lock:
        result = apply_action(
            session.state,
            QueueBarracks(job_type=payload.job_type, quantity=payload.quantity, stop_at=LocationId.NEW_SYSTEM_CORE),
        )
        return _from_result(result)


@router.post("/actions/upgrade-factory", response_model=schemas.ApiResponse)
async def upgrade_factory(request: Request, response: Response):
    session_id, session = get_or_create_session(request.cookies.get("session_id"))
    response.set_cookie("session_id", session_id, httponly=True)
    async with session.lock:
        result = apply_action(session.state, UpgradeFactory())
        return _from_result(result)


@router.post("/actions/upgrade-barracks", response_model=schemas.ApiResponse)
async def upgrade_barracks(request: Request, response: Response):
    session_id, session = get_or_create_session(request.cookies.get("session_id"))
    response.set_cookie("session_id", session_id, httponly=True)
    async with session.lock:
        result = apply_action(session.state, UpgradeBarracks())
        return _from_result(result)


@router.post("/actions/advance-day", response_model=schemas.ApiResponse)
async def advance_day(request: Request, response: Response):
    session_id, session = get_or_create_session(request.cookies.get("session_id"))
    response.set_cookie("session_id", session_id, httponly=True)
    async with session.lock:
        result = apply_action(session.state, AdvanceDay())
        return _from_result(result)


@router.post("/actions/operation/start", response_model=schemas.ApiResponse)
async def start_operation(payload: schemas.OperationStartRequest, request: Request, response: Response):
    session_id, session = get_or_create_session(request.cookies.get("session_id"))
    response.set_cookie("session_id", session_id, httponly=True)
    async with session.lock:
        try:
            target = _parse_target(payload.target)
            op_type = _parse_op_type(payload.op_type)
            intent = OperationIntent(target=target, op_type=op_type)
            result = apply_action(session.state, StartOperation(intent=intent))
            return _from_result(result)
        except ValueError as exc:
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
            result = apply_action(session.state, SubmitPhaseDecisions(decisions=decisions))
            return _from_result(result)
        except (ValueError, RuntimeError, TypeError) as exc:
            return _build_response(state, ok=False, message=str(exc), kind="error")


@router.post("/actions/operation/ack-phase", response_model=schemas.ApiResponse)
async def acknowledge_phase(request: Request, response: Response):
    session_id, session = get_or_create_session(request.cookies.get("session_id"))
    response.set_cookie("session_id", session_id, httponly=True)
    async with session.lock:
        result = apply_action(session.state, AcknowledgePhaseReport())
        return _from_result(result)


@router.post("/actions/ack-aar", response_model=schemas.ApiResponse)
async def acknowledge_aar(request: Request, response: Response):
    session_id, session = get_or_create_session(request.cookies.get("session_id"))
    response.set_cookie("session_id", session_id, httponly=True)
    async with session.lock:
        result = apply_action(session.state, AcknowledgeAar())
        return _from_result(result)
