#!/usr/bin/env python3
"""sessionStart: inject Observer context from engine.py state."""
from __future__ import annotations

import json
import os
import subprocess
import sys

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
ENGINE_PATH = os.path.join(REPO_ROOT, "engine.py")
CONSTITUTION = os.path.join(REPO_ROOT, "doubt_by_design2.md")


def main() -> None:
    context_parts = [
        "Scepticism Engine Observer (engine.py) is ACTIVE.",
        "Parallel Θ: python3 engine.py --gate \"<query>\"",
        "Memory: scripts/memory.py retrieve (invoked inside engine in parallel).",
    ]

    proc = subprocess.run(
        ["python3", ENGINE_PATH, "--gate", "session", "--json"],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        timeout=60,
        check=False,
    )
    if proc.stdout.strip():
        try:
            data = json.loads(proc.stdout)
            ctx = data.get("context")
            if ctx:
                context_parts.append(ctx)
        except json.JSONDecodeError:
            pass

    if os.path.isfile(CONSTITUTION):
        context_parts.append("Constitution: doubt_by_design2.md")

    out = {"additional_context": "\n\n".join(context_parts)}
    sys.stdout.write(json.dumps(out))
    sys.stdout.flush()


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        sys.stderr.write(f"session_start hook error: {exc}\n")
        sys.stdout.write("{}")
        sys.stdout.flush()
