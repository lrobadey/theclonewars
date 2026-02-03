from __future__ import annotations

from random import Random

from hypothesis import given, settings
from hypothesis import strategies as st

from war_sim.domain.types import EnemyForce, LocationId, Objectives, ObjectiveStatus, PlanetState, Supplies, UnitStock
from war_sim.systems.logistics import LogisticsService, LogisticsState
from tests.helpers.invariants import assert_supplies_non_negative, assert_units_non_negative, total_supplies, total_units


def _dummy_planet() -> PlanetState:
    return PlanetState(
        objectives=Objectives(
            foundry=ObjectiveStatus.ENEMY,
            comms=ObjectiveStatus.ENEMY,
            power=ObjectiveStatus.ENEMY,
        ),
        enemy=EnemyForce(
            infantry=100,
            walkers=2,
            support=1,
            cohesion=1.0,
            fortification=1.0,
            reinforcement_rate=0.0,
            intel_confidence=0.7,
        ),
        control=0.3,
    )


def _total_system_supplies(state: LogisticsState) -> int:
    depot_total = sum(total_supplies(s) for s in state.depot_stocks.values())
    order_total = sum(total_supplies(o.supplies) for o in state.active_orders)
    return depot_total + order_total


def _total_system_units(state: LogisticsState) -> int:
    depot_total = sum(total_units(u) for u in state.depot_units.values())
    order_total = sum(total_units(o.units) for o in state.active_orders)
    return depot_total + order_total


@given(
    ammo=st.integers(min_value=1, max_value=100),
    fuel=st.integers(min_value=0, max_value=50),
    med=st.integers(min_value=0, max_value=30),
)
@settings(max_examples=25)
def test_logistics_conservation_under_transit(ammo: int, fuel: int, med: int) -> None:
    state = LogisticsState.new()
    service = LogisticsService()
    rng = Random(1)
    planet = _dummy_planet()

    state.depot_stocks[LocationId.CONTESTED_MID_DEPOT] = Supplies(
        ammo=ammo + 200, fuel=fuel + 200, med_spares=med + 200
    )

    service.create_shipment(
        state,
        LocationId.CONTESTED_MID_DEPOT,
        LocationId.CONTESTED_FRONT,
        Supplies(ammo=ammo, fuel=fuel, med_spares=med),
        None,
        rng,
    )

    initial_supplies = _total_system_supplies(state)
    initial_units = _total_system_units(state)

    for _ in range(3):
        service.tick(state, planet, rng)
        assert _total_system_supplies(state) <= initial_supplies
        assert _total_system_units(state) <= initial_units
        for stock in state.depot_stocks.values():
            assert_supplies_non_negative(stock)
        for stock in state.depot_units.values():
            assert_units_non_negative(stock)


def test_logistics_route_legality() -> None:
    state = LogisticsState.new()
    service = LogisticsService()
    rng = Random(2)

    state.depot_stocks[LocationId.CONTESTED_SPACEPORT] = Supplies(ammo=200, fuel=0, med_spares=0)
    service.create_shipment(
        state,
        LocationId.CONTESTED_SPACEPORT,
        LocationId.CONTESTED_MID_DEPOT,
        Supplies(ammo=100, fuel=0, med_spares=0),
        None,
        rng,
    )

    assert state.shipments
    shipment = state.shipments[0]
    for i in range(len(shipment.path) - 1):
        origin = shipment.path[i]
        dest = shipment.path[i + 1]
        assert any(r.origin == origin and r.destination == dest for r in state.routes)


def test_logistics_interdiction_extremes() -> None:
    base = LogisticsState.new()
    service = LogisticsService()
    planet = _dummy_planet()

    route = next(
        r for r in base.routes
        if r.origin == LocationId.CONTESTED_MID_DEPOT and r.destination == LocationId.CONTESTED_FRONT
    )

    def run_with_risk(risk: float) -> int:
        interdicted = 0
        for seed in range(20):
            state = LogisticsState.new()
            state.depot_stocks[LocationId.CONTESTED_MID_DEPOT] = Supplies(ammo=200, fuel=0, med_spares=0)
            for r in state.routes:
                if r.origin == route.origin and r.destination == route.destination:
                    r.interdiction_risk = risk
            rng = Random(seed)
            service.create_shipment(
                state,
                LocationId.CONTESTED_MID_DEPOT,
                LocationId.CONTESTED_FRONT,
                Supplies(ammo=100, fuel=0, med_spares=0),
                None,
                rng,
            )
            service.tick(state, planet, rng)
            if any(e.event_type == "interdicted" for e in state.transit_log):
                interdicted += 1
        return interdicted

    assert run_with_risk(0.0) <= run_with_risk(1.0)


def test_logistics_space_capacity_blocks_overload() -> None:
    state = LogisticsState.new()
    service = LogisticsService()
    rng = Random(3)

    state.depot_stocks[LocationId.NEW_SYSTEM_CORE] = Supplies(ammo=1000, fuel=1000, med_spares=1000)

    over_capacity = Supplies(
        ammo=state.ships["1"].CAPACITY_AMMO + 1,
        fuel=0,
        med_spares=0,
    )

    raised = False
    try:
        service.create_shipment(
            state,
            LocationId.NEW_SYSTEM_CORE,
            LocationId.CONTESTED_SPACEPORT,
            over_capacity,
            UnitStock(0, 0, 0),
            rng,
        )
    except ValueError:
        raised = True

    assert raised is True
