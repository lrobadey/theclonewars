# The Schism (Legacy: The Clone Wars)

See `CLONE_WARS_WAR_SIM_MVP.md` for the finalized, agent-ready MVP scope and intended design.

## V2 Web UI (Primary)

The primary interface is the v2 web UI backed by the shared engine in `src/war_sim`.

Run from repo root:

- `cd sim-v2/client && npm install && npm run build`
- `python sim-v2/run_server.py`
- Open `http://127.0.0.1:8000`

Scenario data (v2):
- `sim-v2/data/scenarios/default.json`

## Legacy Scaffolding (Python + Textual)

Prereqs: Python 3.11+

Install:
- `python -m venv .venv`
- `source .venv/bin/activate`
- `pip install -e .`

Dev install (adds hot-reload + pytest):
- `pip install -e ".[dev]"`

Run:
- `python -m clone_wars`

Hot reload (restarts on file changes):
- `python -m clone_wars.dev`

Browser dev server:
- `python3 clone` starts the FastAPI dev server for the browser UI (default host `127.0.0.1`, port `8000`, uvicorn `--reload` on, browser auto-opens). Use `--no-reload` to disable hot reload or `--no-browser` to skip the automatic browser tab.

Scenario data:
- `src/clone_wars/data/scenario.json`
