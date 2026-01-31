from __future__ import annotations

from fastapi.testclient import TestClient

from server.main import create_app


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

    # Map needs these IDs to exist
    ids = {n["id"] for n in data["systemNodes"]}
    assert "new_system_core" in ids
    assert "deep_space" in ids
    assert "contested_front" in ids


def test_action_advance_day_smoke():
    app = create_app()
    client = TestClient(app)

    before = client.get("/api/state").json()["day"]
    res = client.post("/api/actions/advance-day")
    assert res.status_code == 200
    payload = res.json()
    assert payload["ok"] is True
    assert payload["state"]["day"] == before + 1

