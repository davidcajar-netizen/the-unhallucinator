#!/usr/bin/env python3
"""beforeSubmitPrompt: Body parallel witness — never blocks Brain."""
from __future__ import annotations

import sys

from hook_lib import load_last_response, read_input, run_engine_observe, write_output


def main() -> None:
    payload = read_input()
    prompt = payload.get("prompt") or ""

    try:
        last_response = str(payload.get("last_response") or load_last_response())
        run_engine_observe(prompt, last_response=last_response)
    except Exception as exc:
        sys.stderr.write(f"engine observe (non-blocking): {exc}\n")

    write_output({"continue": True})


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        sys.stderr.write(f"before_submit_prompt hook error: {exc}\n")
        write_output({"continue": True})
