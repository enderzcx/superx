#!/usr/bin/env python3
"""Smoke-check the local superx skill wrapper surface."""

from __future__ import annotations

import shutil
import subprocess
import sys


REQUIRED_COMMANDS = {"user", "semantic", "keyword", "thread", "article", "research"}


def main() -> int:
    superx = shutil.which("superx")
    if not superx:
        print("ERROR: superx is not on PATH")
        return 1

    result = subprocess.run(
        [superx, "--help"],
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        check=False,
    )
    if result.returncode != 0:
        print(result.stdout)
        print(f"ERROR: superx --help exited {result.returncode}")
        return result.returncode

    missing = sorted(cmd for cmd in REQUIRED_COMMANDS if cmd not in result.stdout)
    if missing:
        print(result.stdout)
        print("ERROR: missing subcommands: " + ", ".join(missing))
        return 1

    print("OK: superx help surface exposes required subcommands")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
