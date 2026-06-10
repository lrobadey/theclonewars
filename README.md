# The Schism (Legacy: The Clone Wars)

See `CLONE_WARS_WAR_SIM_MVP.md` for the finalized, agent-ready MVP scope and intended design.

## Active App: V2 Web UI

The active product path is the v2 web UI backed by the shared engine in `src/war_sim`.
It is the smaller playable slice: produce resources, move them through logistics, run one
operation, and read the after-action report.

Install and launch from repo root:

- `python3.11 -m venv .venv`
- `source .venv/bin/activate`
- `pip install -e ".[dev]"`
- `cd sim-v2/client && npm install && npm run build && cd ../..`
- `python3.11 sim-v2/run_server.py` (recommended; or run from an activated `.venv`)
- The launcher builds the v2 client if missing, auto-selects `8001+` if `8000` is taken, and opens your browser.
- Root helper scripts `./clone` and `./clone-react` now delegate to this same v2 launcher.

Scenario data (v2):
- `sim-v2/data/scenarios/default.json`

## Archived Legacy Scaffolding

The older `src/clone_wars` TUI, web, and prototype surfaces remain in the repository as
archived scaffolding only. They are not the active app path, not the default install target,
and not the launch surface for new feature work.

Archived code and data:
- `src/clone_wars/`
- `src/clone_wars/data/scenario.json`

Archived entrypoints:
- `python -m clone_wars`
- `python -m clone_wars.dev`
- the old `clone_wars.web.run_react` FastAPI app

These entrypoints require explicit legacy setup and are preserved for reference, not for the
live product boundary. The default package install includes `src/war_sim` for v2; it does not
publish `src/clone_wars` as a primary package.

Prereqs for legacy exploration: Python 3.11+

Install:
- `python3.11 -m venv .venv`
- `source .venv/bin/activate`
- `pip install -e ".[legacy]"`

Dev install (adds hot-reload + pytest):
- `pip install -e ".[dev,legacy]"`

Run:
- legacy package discovery is disabled by default, so run archived entrypoints only from
  an explicit local reference checkout with `PYTHONPATH=src` and the legacy extra installed.

Do not use `./clone` or `./clone-react` for legacy exploration. They intentionally launch v2.
