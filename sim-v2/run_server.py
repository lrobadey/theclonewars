#!/usr/bin/env python3
"""
Run the Schism Sim v2 server from repo root:

    python sim-v2/run_server.py

Or from sim-v2 with the repo venv:

    cd sim-v2 && PYTHONPATH=../src:. uv run uvicorn server.main:app --reload
"""
from __future__ import annotations

import sys
from pathlib import Path

# Add repo src and sim-v2 so clone_wars and server are importable
_repo_root = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_repo_root / "src"))
sys.path.insert(0, str(_repo_root / "sim-v2"))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "server.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
    )
