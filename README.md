# The Schism

A turn-based strategic war simulation: manage industrial throughput, route-based
logistics, and multi-phase operations, then read the after-action report that explains
the outcome. See `THE_SCHISM_WAR_SIM_MVP.md` for the MVP scope and intended design.

## Layout

- `src/war_sim/` — shared simulation engine (domain, rules, systems, reducer)
- `sim-v2/server/` — FastAPI server exposing the engine
- `sim-v2/client/` — React web UI
- `sim-v2/data/` — scenario and rules data (`scenarios/default.json`, `rules/*.json`)
- `tests/war_sim/` — engine tests; `sim-v2/server/tests/` — API tests

## Setup and launch

```sh
python3.11 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
cd sim-v2/client && npm install && npm run build && cd ../..
./schism            # or: python sim-v2/run_server.py
```

The launcher builds the v2 client if missing, auto-selects port `8001+` if `8000` is
taken, and opens your browser.

## Tests

```sh
pytest
```
