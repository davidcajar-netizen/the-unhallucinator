#!/usr/bin/env python3
"""beforeShellExecution: triangulation witness via engine.py (parallel state update)."""
from __future__ import annotations

import json
import sys

from hook_lib import run_engine_observe, write_output


def main() -> None:
    payload = json.loads(sys.stdin.read() or "{}")
    command = payload.get("command") or ""
    run_engine_observe("", shell_command=command, shell_only=True)
    write_output({"permission": "allow"})


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        sys.stderr.write(f"before_shell hook error: {exc}\n")
        write_output({"permission": "allow"})
