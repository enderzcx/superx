#!/usr/bin/env python3
"""Thin launcher for the repository-level superx.py implementation.

The source repo keeps one implementation at ../../../superx.py so the skill copy
cannot drift from the package entrypoint.
"""

import runpy
import sys
from pathlib import Path


def main() -> None:
    source = Path(__file__).resolve().parents[3] / "superx.py"
    if not source.exists():
        print(f"Error: canonical superx.py not found: {source}", file=sys.stderr)
        sys.exit(127)
    runpy.run_path(str(source), run_name="__main__")


if __name__ == "__main__":
    main()
