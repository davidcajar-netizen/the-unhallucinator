#!/usr/bin/env python3
"""beforeSubmitPrompt: single parallel Observer pass via engine.py."""
from __future__ import annotations

import sys

from hook_lib import load_last_response, read_input, run_engine_observe, write_output

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
                        "Prompt blocked: attempted gate bypass without GATE_BYPASS_AUDITED token."
                    ),
                }
            )
            return

    last_response = str(payload.get("last_response") or load_last_response())
    run_engine_observe(prompt, last_response=last_response)
    write_output({"continue": True})


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        sys.stderr.write(f"before_submit_prompt hook error: {exc}\n")
        write_output({"continue": True})
