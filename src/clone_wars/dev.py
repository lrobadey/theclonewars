from __future__ import annotations

import argparse
import shlex
import signal
import subprocess
import sys
from pathlib import Path


def _find_repo_root(start: Path) -> Path:
    for parent in (start, *start.parents):
        if (parent / "pyproject.toml").exists():
            return parent
    return start


def _terminate(proc: subprocess.Popen[object]) -> None:
    if proc.poll() is not None:
        return
    try:
        proc.send_signal(signal.SIGINT)
        proc.wait(timeout=2)
        return
    except Exception:
        pass
    try:
        proc.terminate()
        proc.wait(timeout=2)
        return
    except Exception:
        pass
    try:
        proc.kill()
    except Exception:
        pass


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="python -m clone_wars.dev",
        description="Dev runner that restarts the game when files change.",
    )
    parser.add_argument(
        "--paths",
        nargs="*",
        default=None,
        help="Paths to watch (default: repo src/ and tests/ when present).",
    )
    parser.add_argument(
        "--cmd",
        default=None,
        help="Command to run (default: python -m clone_wars).",
    )
    args = parser.parse_args(argv)

    try:
        from watchfiles import DefaultFilter, watch  # type: ignore[import-not-found]
    except Exception:
        print(
            "Missing dependency: watchfiles\n"
            "Install with: pip install -e '.[dev]'\n"
            "Or:           pip install watchfiles",
            file=sys.stderr,
        )
        return 2

    repo_root = _find_repo_root(Path.cwd().resolve())
    default_watch_paths = [repo_root / "src"]
    if (repo_root / "tests").exists():
        default_watch_paths.append(repo_root / "tests")
    watch_paths = [Path(p).resolve() for p in (args.paths or default_watch_paths)]

    watch_filter = DefaultFilter(
        ignore_dirs=["__pycache__", ".pytest_cache"],
        ignore_entity_patterns=["*.pyc", "*.pyo", "*.pyd"],
    )

    cmd = (
        [sys.executable, "-m", "clone_wars"]
        if args.cmd is None
        else shlex.split(args.cmd)
    )

    proc: subprocess.Popen[object] | None = None
    try:
        proc = subprocess.Popen(cmd)
        for _changes in watch(*watch_paths, watch_filter=watch_filter):
            _terminate(proc)
            proc = subprocess.Popen(cmd)
    except KeyboardInterrupt:
        return 0
    finally:
        if proc is not None:
            _terminate(proc)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
