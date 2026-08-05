#!/usr/bin/env python3
"""preToolUse: deny Task tool explore/debug when parallel gate not passed."""
from __future__ import annotations

import json
import os
import sys

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
STATE_PATH = os.path.join(REPO_ROOT, ".cursor", "gate-state.json")

BLOCKED_SUBAGENTS = frozenset({"explore", "computerUse", "debug", "videoReview"})


def gate_passed() -> bool:
    if not os.path.isfile(STATE_PATH):
        return False
    with open(STATE_PATH, "r", encoding="utf-8") as fh:
        data = json.load(fh)
    if data.get("T_g_bypass_unlocked"):
        return True
    return bool(data.get("parallel_gate_passed"))


def main() -> None:
    payload = json.loads(sys.stdin.read() or "{}")
    tool_name = (payload.get("tool_name") or "").lower()
    tool_input = payload.get("tool_input") or {}

    out = {"permission": "allow"}

    if tool_name == "task":
        subagent = (tool_input.get("subagent_type") or tool_input.get("type") or "").strip()
        if subagent in BLOCKED_SUBAGENTS and not gate_passed():
            out = {
                "permission": "deny",
                "agent_message": (
                    f"Task subagent '{subagent}' blocked by Scepticism Engine gate. "
                    "Run parallel-eval first: python3 scripts/gate.py parallel-eval \"<query>\" "
                    "or use custom subagent sceptic-inherit after gate passes."
                ),
            }

    sys.stdout.write(json.dumps(out))
    sys.stdout.flush()


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        sys.stderr.write(f"pre_tool_use hook error: {exc}\n")
        sys.stdout.write(json.dumps({"permission": "allow"}))
        sys.stdout.flush()
