#!/usr/bin/env python3
"""beforeShellExecution: track memory retrieve / web fetch for triangulation."""
from __future__ import annotations

import json
import os
import sys

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.insert(0, os.path.join(REPO_ROOT, "scripts"))

from gate_lib import load_state, record_shell_command, save_state, DEFAULT_STATE_PATH  # noqa: E402


def main() -> None:
    payload = json.loads(sys.stdin.read() or "{}")
    command = payload.get("command") or ""

    state = load_state(DEFAULT_STATE_PATH)
    state = record_shell_command(state, command)
    save_state(state)

    sys.stdout.write(json.dumps({"permission": "allow"}))
    sys.stdout.flush()


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        sys.stderr.write(f"before_shell hook error: {exc}\n")
        sys.stdout.write(json.dumps({"permission": "allow"}))
        sys.stdout.flush()
