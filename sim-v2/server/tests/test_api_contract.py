from __future__ import annotations

from fastapi.testclient import TestClient

from server.main import create_app
from server.session import get_session


def test_get_state_contract_smoke():
    app = create_app()
    client = TestClient(app)

    res = client.get("/api/state")
    assert res.status_code == 200
    data = res.json()

    # Core shape
    assert isinstance(data.get("day"), int)
    assert isinstance(data.get("actionPoints"), int)
    assert isinstance(data.get("factionTurn"), str)
    assert isinstance(data.get("systemNodes"), list)
    assert isinstance(data.get("contestedPlanet"), dict)
    assert isinstance(data.get("logistics"), dict)
    assert isinstance(data.get("mapView"), dict)

    # Map needs these IDs to exist
    ids = {n["id"] for n in data["systemNodes"]}
    assert "new_system_core" in ids
    assert "deep_space" in ids
    assert "contested_front" in ids

    map_ids = {n["id"] for n in data["mapView"]["nodes"]}
    assert "new_system_core" in map_ids
    assert "deep_space" in map_ids
    assert "contested_front" in map_ids


def test_catalog_contract_smoke():
    app = create_app()
    client = TestClient(app)

    res = client.get("/api/catalog")
    assert res.status_code == 200
    data = res.json()

    assert isinstance(data.get("operationTargets"), list)
    assert [item["id"] for item in data["operationTargets"]] == ["foundry", "comms", "power"]
    assert isinstance(data.get("operationTypes"), list)
    assert [item["id"] for item in data["operationTypes"]] == ["raid", "campaign", "siege"]
    assert isinstance(data.get("decisions"), dict)


def test_action_advance_day_smoke():
    app = create_app()
    client = TestClient(app)

    before = client.get("/api/state").json()["day"]
    res = client.post("/api/actions/advance-day")
    assert res.status_code == 200
    payload = res.json()
    assert payload["ok"] is True
    assert payload["state"]["day"] == before + 1


def test_invalid_operation_target_returns_structured_error():
    app = create_app()
    client = TestClient(app)

    res = client.post("/api/actions/operation/start", json={"target": "bad_target", "opType": "campaign"})
    assert res.status_code == 200
    payload = res.json()
    assert payload["ok"] is False
    assert "Unknown target" in (payload.get("message") or "")


def test_invalid_dispatch_location_returns_structured_error():
    app = create_app()
    client = TestClient(app)

    res = client.post(
        "/api/actions/dispatch",
        json={
            "origin": "bad_location",
            "destination": "deep_space",
            "supplies": {"ammo": 1, "fuel": 0, "medSpares": 0},
            "units": {"infantry": 0, "walkers": 0, "support": 0},
        },
    )
    assert res.status_code == 200
    payload = res.json()
    assert payload["ok"] is False
    assert "Unknown location" in (payload.get("message") or "")


def test_queue_job_visible_when_eta_unknown_capacity_zero():
    app = create_app()
    client = TestClient(app)

    client.get("/api/state")
    session_id = client.cookies.get("session_id")
    assert session_id is not None
    session = get_session(session_id)
    assert session is not None
    session.state.production.factories = 0

    res = client.post("/api/actions/production", json={"jobType": "ammo", "quantity": 5})
    assert res.status_code == 200
    payload = res.json()
    assert payload["ok"] is True
    jobs = payload["state"]["production"]["jobs"]
    assert len(jobs) == 1
    assert jobs[0]["etaDays"] == -1


def test_production_quantity_validation():
    app = create_app()
    client = TestClient(app)

    res = client.post("/api/actions/production", json={"jobType": "ammo", "quantity": 0})
    assert res.status_code == 422


def test_non_foundry_operation_allowed():
    app = create_app()
    client = TestClient(app)

    allowed = client.post("/api/actions/operation/start", json={"target": "comms", "opType": "campaign"})
    assert allowed.status_code == 200
    allowed_payload = allowed.json()
    assert allowed_payload["ok"] is True


def test_non_campaign_operation_allowed():
    app = create_app()
    client = TestClient(app)

    allowed = client.post("/api/actions/operation/start", json={"target": "foundry", "opType": "raid"})
    assert allowed.status_code == 200
    allowed_payload = allowed.json()
    assert allowed_payload["ok"] is True


def test_latest_battle_day_contains_vic3_fields():
    app = create_app()
    client = TestClient(app)

    start = client.post("/api/actions/operation/start", json={"target": "foundry", "opType": "campaign"})
    assert start.status_code == 200
    assert start.json()["ok"] is True

    decisions = client.post("/api/actions/operation/decisions", json={"axis": "direct", "fire": "preparatory"})
    assert decisions.status_code == 200
    assert decisions.json()["ok"] is True

    tick = client.post("/api/actions/advance-day")
    assert tick.status_code == 200
    payload = tick.json()
    assert payload["ok"] is True

    battle_day = payload["state"]["operation"]["latestBattleDay"]
    assert isinstance(battle_day["terrainId"], str)
    assert isinstance(battle_day["forceLimitBattalions"], int)
    assert isinstance(battle_day["engagementCapManpower"], int)
    assert isinstance(battle_day["attackerEligibleManpower"], int)
    assert isinstance(battle_day["defenderEligibleManpower"], int)
    assert isinstance(battle_day["attackerEngagedManpower"], int)
    assert isinstance(battle_day["defenderEngagedManpower"], int)
    assert isinstance(battle_day["attackerEngagementRatio"], float)
    assert isinstance(battle_day["defenderEngagementRatio"], float)
    assert isinstance(battle_day["attackerAdvantageExpansion"], float)
    assert isinstance(battle_day["defenderAdvantageExpansion"], float)
