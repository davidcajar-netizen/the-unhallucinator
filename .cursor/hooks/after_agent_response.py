#!/usr/bin/env python3
"""afterAgentResponse: capture collapse text for next parallel Observer pass."""
from __future__ import annotations

import json
import subprocess
import sys

from hook_lib import REPO_ROOT, ENGINE_PATH


def main() -> None:
    payload = json.loads(sys.stdin.read() or "{}")
    text = payload.get("text") or ""
    if not text.strip():
        sys.stdout.write("{}")
        sys.stdout.flush()
        return

    subprocess.run(
        ["python3", ENGINE_PATH],
        cwd=REPO_ROOT,
        input=json.dumps({"last_response": text, "store_only": True, "json": True}),
        capture_output=True,
        text=True,
        timeout=15,
        check=False,
    )
    sys.stdout.write("{}")
    sys.stdout.flush()


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        sys.stderr.write(f"after_agent_response hook error: {exc}\n")
        sys.stdout.write("{}")
        sys.stdout.flush()
