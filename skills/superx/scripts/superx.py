#!/usr/bin/env python3
"""Thin launcher for the local canonical superx.py implementation."""

import os
import runpy
import sys
from pathlib import Path


def candidate_sources():
    env_source = os.environ.get("SUPERX_SOURCE")
    if env_source:
        yield Path(env_source).expanduser()
    yield Path.home() / "Work" / "CODEX" / "grok" / "superx.py"
    yield Path(__file__).resolve().parents[3] / "superx.py"


def main() -> None:
    this_file = Path(__file__).resolve()
    for source in candidate_sources():
        try:
            resolved = source.resolve()
        except FileNotFoundError:
            continue
        if resolved.exists() and resolved != this_file:
            runpy.run_path(str(resolved), run_name="__main__")
            return
    print("Error: canonical superx.py not found. Set SUPERX_SOURCE=/path/to/superx.py.", file=sys.stderr)
    sys.exit(127)


if __name__ == "__main__":
    main()
