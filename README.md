# The Schism (Legacy: The Clone Wars)

See `CLONE_WARS_WAR_SIM_MVP.md` for the finalized, agent-ready MVP scope and intended design.

## V2 Web UI (Primary)

The primary interface is the v2 web UI backed by the shared engine in `src/war_sim`.

Run from repo root:

- `python3.11 sim-v2/run_server.py` (recommended; or run from an activated `.venv`)
- The launcher builds the v2 client if missing, auto-selects `8001+` if `8000` is taken, and opens your browser.

Scenario data (v2):
- `sim-v2/data/scenarios/default.json`

## Legacy Scaffolding (Python + Textual)

Prereqs: Python 3.11+

Install:
- `python3.11 -m venv .venv`
- `source .venv/bin/activate`
- `pip install -e .`

Dev install (adds hot-reload + pytest):
- `pip install -e ".[dev]"`

Run:
- `python -m clone_wars` (after activating `.venv`)

Hot reload (restarts on file changes):
- `python -m clone_wars.dev` (after activating `.venv`)

Browser dev server:
- `python3.11 clone` (or `python3 clone` after activating `.venv`; macOS system `python3` may be 3.9) starts the FastAPI dev server for the browser UI (default host `127.0.0.1`, port `8000`, uvicorn `--reload` on, browser auto-opens). Use `--no-reload` to disable hot reload or `--no-browser` to skip the automatic browser tab.

Scenario data:
- `src/clone_wars/data/scenario.json`
