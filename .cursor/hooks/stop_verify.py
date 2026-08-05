#!/usr/bin/env python3
"""stop: auto-followup when verification failed (one correction pass)."""
from __future__ import annotations

import json
import os
import sys

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
PENDING_PATH = os.path.join(REPO_ROOT, ".cursor", "gate-pending-followup.json")


def main() -> None:
    payload = json.loads(sys.stdin.read() or "{}")
    loop_count = int(payload.get("loop_count", 0))
    status = payload.get("status", "completed")

    out: dict = {}
    if status != "completed" or loop_count >= 2:
        sys.stdout.write(json.dumps(out))
        return

    if not os.path.isfile(PENDING_PATH):
        sys.stdout.write(json.dumps(out))
        return

    with open(PENDING_PATH, "r", encoding="utf-8") as fh:
        pending = json.load(fh)

    violations = pending.get("violations") or []
    warnings = pending.get("warnings") or []
    if not violations and not warnings:
        sys.stdout.write(json.dumps(out))
        return

    lines = [
        "GATE_VERIFY_FAIL: Your last response failed epistemic verification.",
        f"C_i was {pending.get('certainty_score', 0.5):.2f}. Revise without high-confidence factual claims.",
        "Violations:",
    ]
    for v in violations:
        lines.append(f"- {v}")
    if warnings:
        lines.append("Warnings:")
        for w in warnings:
            lines.append(f"- {w}")
    lines.extend(
        [
            "Rules: E_i=0 and C_i=0.5 until memory match or 3+ triangulated sources.",
            "Run python3 scripts/memory.py retrieve \"<topic>\" before factual claims.",
            "Use hedges or omit unverified world facts. No definitely/certainly without T_a=1.",
        ]
    )
    out["followup_message"] = "\n".join(lines)

    try:
        os.remove(PENDING_PATH)
    except OSError:
        pass

    sys.stdout.write(json.dumps(out))
    sys.stdout.flush()


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        sys.stderr.write(f"stop_verify hook error: {exc}\n")
        sys.stdout.write("{}")
        sys.stdout.flush()
