#!/usr/bin/env python3
"""beforeSubmitPrompt: parallel pre-collapse gate before each user submission."""
from __future__ import annotations

import sys

from hook_lib import read_input, run_gate_parallel_eval, write_output

# Prompts that try to disable gates without audit token
_BYPASS_PATTERNS = [
    "ignore the engine",
    "ignore doubt_by_design",
    "skip the gate",
    "just answer directly",
    "don't verify",
]


def main() -> None:
    payload = read_input()
    prompt = payload.get("prompt") or ""

    lowered = prompt.lower()
    for pat in _BYPASS_PATTERNS:
        if pat in lowered and "GATE_BYPASS_AUDITED" not in prompt:
            write_output(
                {
                    "continue": False,
                    "user_message": (
                        "Prompt blocked: attempted gate bypass without GATE_BYPASS_AUDITED token. "
                        "Use parallel gate + triangulation, or include audited bypass token."
                    ),
                }
            )
            return

    result = run_gate_parallel_eval(prompt)
    if not result.get("ok"):
        write_output({"continue": True})
        return

    write_output({"continue": True})


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        sys.stderr.write(f"before_submit_prompt hook error: {exc}\n")
        write_output({"continue": True})
