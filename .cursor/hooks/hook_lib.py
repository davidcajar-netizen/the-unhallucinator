#!/usr/bin/env python3
"""Shared stdin/stdout helpers for Cursor hooks."""
from __future__ import annotations

import json
import os
import subprocess
import sys
from typing import Any

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
ENGINE_PATH = os.path.join(REPO_ROOT, "engine.py")
STATE_PATH = os.path.join(REPO_ROOT, ".cursor", "gate-state.json")


def read_input() -> dict[str, Any]:
    raw = sys.stdin.read()
    if not raw.strip():
        return {}
    return json.loads(raw)


def write_output(data: dict[str, Any]) -> None:
    sys.stdout.write(json.dumps(data))
    sys.stdout.flush()


def load_last_response() -> str:
    if not os.path.isfile(STATE_PATH):
        return ""
    with open(STATE_PATH, "r", encoding="utf-8") as fh:
        data = json.load(fh)
    return str(data.get("last_response", ""))


def run_engine_observe(
    prompt: str,
    last_response: str = "",
    shell_command: str = "",
    shell_only: bool = False,
) -> dict[str, Any]:
    payload = {
        "prompt": prompt,
        "last_response": last_response,
        "shell_command": shell_command,
        "shell_only": shell_only,
        "json": True,
    }
    proc = subprocess.run(
        ["python3", ENGINE_PATH],
        cwd=REPO_ROOT,
        input=json.dumps(payload),
        capture_output=True,
        text=True,
        timeout=90,
        check=False,
    )
    if proc.returncode != 0 or not proc.stdout.strip():
        return {"ok": False, "error": proc.stderr.strip() or "engine observe failed"}
    try:
        return {"ok": True, "state": json.loads(proc.stdout)}
    except json.JSONDecodeError:
        return {"ok": False, "error": "invalid engine json"}
