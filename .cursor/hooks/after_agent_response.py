#!/usr/bin/env python3
"""afterAgentResponse: epistemic reflection after collapse — feeds next inference."""
from __future__ import annotations

import json
import os
import sys

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.insert(0, os.path.join(REPO_ROOT, "scripts"))

from gate_lib import (  # noqa: E402
    DEFAULT_AUDIT_PATH,
    DEFAULT_STATE_PATH,
    apply_reflection,
    audit_log,
    load_state,
    reflect_on_response,
    save_state,
)


def main() -> None:
    payload = json.loads(sys.stdin.read() or "{}")
    text = payload.get("text") or ""

    state = load_state(DEFAULT_STATE_PATH)
    reflection = reflect_on_response(text, state)
    state = apply_reflection(state, reflection)
    save_state(state)

    audit_log(
        "epistemic_reflect",
        reflection.to_dict(),
        DEFAULT_AUDIT_PATH,
    )

    # No followup, no stop — reflection is input to the next parallel pass
    sys.stdout.write("{}")
    sys.stdout.flush()


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        sys.stderr.write(f"after_agent_response hook error: {exc}\n")
        sys.stdout.write("{}")
        sys.stdout.flush()
