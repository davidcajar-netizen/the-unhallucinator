#!/usr/bin/env python3
"""subagentStart: block Fast explore/debug subagents until parallel gate passes."""
from __future__ import annotations

import json
import os
import sys

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
STATE_PATH = os.path.join(REPO_ROOT, ".cursor", "gate-state.json")

# Built-in subagents that often bypass parent model / run Composer Fast
GATED_TYPES = frozenset({"explore", "computerUse", "debug", "videoReview"})


def read_input() -> dict:
    raw = sys.stdin.read()
    return json.loads(raw) if raw.strip() else {}


def load_parallel_passed() -> bool:
    if not os.path.isfile(STATE_PATH):
        return False
    with open(STATE_PATH, "r", encoding="utf-8") as fh:
        data = json.load(fh)
    if data.get("T_g_bypass_unlocked"):
        return True
    return bool(data.get("parallel_gate_passed"))


def main() -> None:
    payload = read_input()
    subagent_type = payload.get("subagent_type") or ""
    subagent_model = (payload.get("subagent_model") or "").lower()

    out: dict = {"permission": "allow"}

    if "fast" in subagent_model and "composer" in subagent_model:
        out = {
            "permission": "deny",
            "user_message": (
                "Subagent blocked: Composer 2.5 Fast denied by gate policy. "
                "Use composer-2.5[fast=false] or sceptic-inherit subagent."
            ),
        }
    elif subagent_type in GATED_TYPES and not load_parallel_passed():
        out = {
            "permission": "deny",
            "user_message": (
                f"Subagent '{subagent_type}' blocked until parallel gate runs. "
                "Submit a prompt (hooks run parallel-eval) or run: "
                "python3 scripts/gate.py parallel-eval \"<query>\""
            ),
        }

    sys.stdout.write(json.dumps(out))
    sys.stdout.flush()


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        sys.stderr.write(f"subagent_start hook error: {exc}\n")
        sys.stdout.write(json.dumps({"permission": "allow"}))
        sys.stdout.flush()
