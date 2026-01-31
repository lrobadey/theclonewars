# Schism Sim (v2)

Turn-based strategic sim for the Schism setting (New System vs Human Collective). Uses the same engine as the main project, with v2 data and the map prototype as the core UI.

## Prerequisites

- Python (same as main project; use repo venv)
- Node (for building the client)

## Quick start

1. **Install client dependencies and build** (first time only):

   ```bash
   cd sim-v2/client
   npm install
   npm run build
   ```

2. **Start the server** from the repo root:

   ```bash
   python sim-v2/run_server.py
   ```

   Or from `sim-v2`:

   ```bash
   cd sim-v2
PYTHONPATH=. uv run uvicorn server.main:app --reload
   ```

3. **Open** [http://127.0.0.1:8000](http://127.0.0.1:8000).

## Layout

- **server/** — FastAPI app, session, API router (`GET /api/state`, `GET /api/health`)
- **client/** — Map prototype SPA (React + Vite); served from `client/dist` after `npm run build`
- **data/** — v2 scenario and objectives (Schism-themed); rules data copied from main project

The UI currently shows **mock map data**. Live game state will be wired in a follow-up (swap mock for `getState()` and map response to `MapState` when `/api/state` is extended or `/api/map` exists).

## Running without the run script

From repo root with the project venv activated:

```bash
PYTHONPATH=sim-v2 uv run uvicorn server.main:app --reload --host 0.0.0.0 --port 8000
```

The app is run with the root project’s virtualenv; `sim-v2` is not a separate installable package.
