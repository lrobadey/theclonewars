# The Clone Wars

See `CLONE_WARS_WAR_SIM_MVP.md` for the finalized, agent-ready MVP scope and intended design.

## Scaffolding (Python + Textual)

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

Scenario data:
- `src/clone_wars/data/scenario.json`
