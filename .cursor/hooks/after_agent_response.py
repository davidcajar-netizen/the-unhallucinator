#!/usr/bin/env python3
"""afterAgentResponse: verify assistant text; audit failures for stop hook."""
from __future__ import annotations

import json
import os
import sys

from hook_lib import read_input, run_gate_verify

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
PENDING_PATH = os.path.join(REPO_ROOT, ".cursor", "gate-pending-followup.json")


def main() -> None:
    payload = read_input()
    text = payload.get("text") or ""
    result = run_gate_verify(text)

    if not result.get("passed", True):
        pending = {
            "violations": result.get("violations", []),
            "warnings": result.get("warnings", []),
            "certainty_score": result.get("certainty_score", 0.5),
        }
        os.makedirs(os.path.dirname(PENDING_PATH), exist_ok=True)
        with open(PENDING_PATH, "w", encoding="utf-8") as fh:
            json.dump(pending, fh, indent=2)
    else:
        if os.path.isfile(PENDING_PATH):
            os.remove(PENDING_PATH)

    # afterAgentResponse has no output fields — audit only
    sys.stdout.write("{}")
    sys.stdout.flush()


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        sys.stderr.write(f"after_agent_response hook error: {exc}\n")
        sys.stdout.write("{}")
        sys.stdout.flush()
