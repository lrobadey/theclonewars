from __future__ import annotations

from clone_wars.engine.types import ObjectiveStatus, SQUAD_SIZE, Supplies, UnitStock


def pct(value: float) -> int:
    return int(max(0.0, min(1.0, value)) * 100)


def fmt_int(value: int) -> str:
    return f"{value:,}"


def fmt_squads(squads: int) -> str:
    troops = squads * SQUAD_SIZE
    return f"{fmt_int(squads)} sq ({fmt_int(troops)})"


def bar(value: int, max_value: int, width: int = 18) -> str:
    if max_value <= 0:
        max_value = 1
    value = max(0, value)
    filled = int(min(1.0, value / max_value) * width)
    return "[" + ("=" * filled) + ("." * (width - filled)) + "]"


def status_label(status: ObjectiveStatus) -> str:
    if status == ObjectiveStatus.ENEMY:
        return "ENEMY HELD"
    if status == ObjectiveStatus.CONTESTED:
        return "CONTESTED"
    return "FRIENDLY"


def status_class(status: ObjectiveStatus) -> str:
    if status == ObjectiveStatus.ENEMY:
        return "status-enemy"
    if status == ObjectiveStatus.CONTESTED:
        return "status-contested"
    return "status-secured"


def risk_label(risk: float) -> str:
    if risk <= 0.0:
        return "SECURE"
    if risk <= 0.015:
        return "LOW"
    if risk <= 0.04:
        return "ELEVATED"
    return "HIGH"


def sum_supplies(stocks: dict[object, Supplies]) -> Supplies:
    ammo = sum(s.ammo for s in stocks.values())
    fuel = sum(s.fuel for s in stocks.values())
    med = sum(s.med_spares for s in stocks.values())
    return Supplies(ammo=ammo, fuel=fuel, med_spares=med)


def sum_units(units: dict[object, UnitStock]) -> UnitStock:
    infantry = sum(u.infantry for u in units.values())
    walkers = sum(u.walkers for u in units.values())
    support = sum(u.support for u in units.values())
    return UnitStock(infantry=infantry, walkers=walkers, support=support)
