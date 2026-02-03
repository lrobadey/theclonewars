# Schism Sim (v2)

Turn-based strategic sim for the Schism setting (New System vs Human Collective). Uses the shared engine in `src/war_sim`, with v2 data and the map UI as the core interface.

## Prerequisites

- Python (same as main project; use repo venv)
- Node (for building the client)

## Quick start

From the repo root:

```bash
python sim-v2/run_server.py
```

- Use `python3` if `python` isn’t available.
- The launcher builds the client if `sim-v2/client/dist/index.html` is missing.
- If port `8000` is already in use, it auto-selects `8001+` and prints the URL.

Useful flags:
- `--no-open` (don’t open a browser tab)
- `--no-build` (skip client build)
- `--build` (force client rebuild)
- `--port 8005` (start scanning from a different port)

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

3. **Open** the URL printed by the launcher (usually `http://127.0.0.1:8000`).

## Layout

- **server/** — FastAPI app + API (`GET /api/state`, `GET /api/catalog`, `GET /api/health`)
- **client/** — Map SPA (React + Vite); served from `client/dist` after `npm run build`
- **data/** — v2 scenario and objectives (Schism-themed); rules data copied from main project

`/api/state` now returns `mapView`, and `/api/catalog` supplies operation/decision options for a fully data-driven UI.

## Tests

From the repo root with the project venv activated:

```bash
python -m pip install -e ".[dev]"
pytest sim-v2/server/tests
```

## Running without the run script

From repo root with the project venv activated:

```bash
PYTHONPATH=sim-v2:src uv run uvicorn server.main:app --reload --host 0.0.0.0 --port 8000
```

The app is run with the root project’s virtualenv; `sim-v2` is not a separate installable package.
