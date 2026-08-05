#!/usr/bin/env python3
"""sessionStart (IDE): inject gate context + engine constitution reference."""
from __future__ import annotations

import json
import os
import subprocess
import sys

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
CONSTITUTION = os.path.join(REPO_ROOT, "doubt_by_design2.md")


def main() -> None:
    context_parts = [
        "Scepticism Engine gate layer is ACTIVE for this repository.",
        "Execute parallel L_2 before collapse: python3 engine.py --gate \"<query>\"",
        "Memory: python3 scripts/memory.py retrieve \"<query>\" --json",
    ]

    proc = subprocess.run(
        ["python3", os.path.join(REPO_ROOT, "scripts", "gate.py"), "context"],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        timeout=15,
        check=False,
    )
    if proc.stdout.strip():
        context_parts.append(proc.stdout.strip())

    if os.path.isfile(CONSTITUTION):
        context_parts.append(
            "Constitution file: doubt_by_design2.md (hardened). Inject operating parameters from repo."
        )

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
