#!/usr/bin/env python3
"""
Launch Schism Sim v2 from repo root:

    python sim-v2/run_server.py

This launcher can:
- build the v2 client (if missing, or forced)
- auto-select a free port if the requested one is taken
- start the FastAPI server
- open the browser to the correct URL
"""
from __future__ import annotations

import argparse
import shutil
import socket
import subprocess
import sys
import threading
import webbrowser
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = REPO_ROOT / "src"
SIM_V2_DIR = REPO_ROOT / "sim-v2"
CLIENT_DIR = SIM_V2_DIR / "client"
CLIENT_DIST_INDEX = CLIENT_DIR / "dist" / "index.html"


def _add_repo_paths() -> None:
    # Ensure shared engine + v2 server are importable when running as a script.
    src = str(SRC_DIR)
    sim_v2 = str(SIM_V2_DIR)
    if src not in sys.path:
        sys.path.insert(0, src)
    if sim_v2 not in sys.path:
        sys.path.insert(0, sim_v2)


def _browser_host(host: str) -> str:
    # If we bind 0.0.0.0/::, open a loopback URL that works locally.
    if host in ("0.0.0.0", "::"):
        return "127.0.0.1"
    return host


def find_available_port(host: str, start_port: int, *, max_tries: int = 50) -> tuple[int, bool]:
    """
    Probe sequential ports starting from start_port.
    Returns (port, did_fallback).
    """
    if max_tries < 1:
        raise ValueError("max_tries must be >= 1")

    last_error: OSError | None = None
    for offset in range(max_tries):
        port = start_port + offset
        try:
            with socket.create_server((host, port), reuse_port=False):
                return port, offset != 0
        except OSError as exc:
            last_error = exc
            continue

    msg = f"No available port found starting at {start_port} after {max_tries} attempts"
    if last_error is not None:
        msg = f"{msg} (last error: {last_error})"
    raise RuntimeError(msg)


def _run(cmd: list[str], *, cwd: Path) -> None:
    subprocess.run(cmd, cwd=str(cwd), check=True)


def build_client_if_needed(*, force: bool, enabled: bool) -> None:
    if not enabled:
        return

    if not force and CLIENT_DIST_INDEX.exists():
        return

    npm = shutil.which("npm")
    if npm is None:
        raise RuntimeError("npm was not found on PATH. Install Node.js (includes npm) and re-run.")

    if not CLIENT_DIR.exists():
        raise RuntimeError(f"Client directory not found: {CLIENT_DIR}")

    node_modules = CLIENT_DIR / "node_modules"
    if not node_modules.exists():
        _run([npm, "install"], cwd=CLIENT_DIR)

    _run([npm, "run", "build"], cwd=CLIENT_DIR)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="python sim-v2/run_server.py",
        description="Launch Schism Sim v2 (build client if needed, run API, open browser).",
    )
    parser.add_argument("--host", default="127.0.0.1", help="Host to listen on (default: %(default)s).")
    parser.add_argument("--port", type=int, default=8000, help="Starting port (default: %(default)s).")
    parser.add_argument("--no-reload", action="store_true", help="Disable uvicorn --reload.")
    parser.add_argument("--no-open", action="store_true", help="Skip opening the browser automatically.")
    parser.add_argument("--build", action="store_true", help="Force rebuilding the v2 client.")
    parser.add_argument("--no-build", action="store_true", help="Never build the v2 client.")
    args = parser.parse_args(argv)

    try:
        build_client_if_needed(force=args.build, enabled=not args.no_build)
    except (RuntimeError, subprocess.CalledProcessError) as exc:
        print(f"[v2] Client build failed: {exc}", file=sys.stderr)
        return 2

    try:
        chosen_port, did_fallback = find_available_port(args.host, args.port, max_tries=50)
    except Exception as exc:
        print(f"[v2] Failed to select a free port: {exc}", file=sys.stderr)
        return 2

    url_host = _browser_host(args.host)
    url = f"http://{url_host}:{chosen_port}"
    if did_fallback:
        print(f"[v2] Serving on {url} (selected because {args.port} was in use).")
    else:
        print(f"[v2] Serving on {url}.")

    if not args.no_open:
        threading.Timer(1.0, webbrowser.open, args=(url,)).start()

    _add_repo_paths()

    try:
        import uvicorn  # type: ignore
    except Exception as exc:
        print(
            "[v2] Missing Python dependencies. Activate your venv and run:\n"
            "  python -m pip install -r requirements.txt\n"
            f"Details: {exc}",
            file=sys.stderr,
        )
        return 2

    try:
        uvicorn.run(
            "server.main:app",
            host=args.host,
            port=chosen_port,
            reload=not args.no_reload,
        )
    except KeyboardInterrupt:
        return 0
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
