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
GATE_CLI = os.path.join(REPO_ROOT, "scripts", "gate.py")


def read_input() -> dict[str, Any]:
    raw = sys.stdin.read()
    if not raw.strip():
        return {}
    return json.loads(raw)


def write_output(data: dict[str, Any]) -> None:
    sys.stdout.write(json.dumps(data))
    sys.stdout.flush()


def run_engine_gate(prompt: str) -> dict[str, Any]:
    """Execute engine.py --gate (L_2 parallel layer) before collapse."""
    query = prompt.strip()
    if not query:
        return {"ok": False, "error": "empty prompt"}
    proc = subprocess.run(
        ["python3", ENGINE_PATH, "--gate", query, "--json"],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        timeout=60,
        check=False,
    )
    if proc.returncode != 0 or not proc.stdout.strip():
        return {"ok": False, "error": proc.stderr.strip() or "engine.py --gate failed"}
    try:
        return {"ok": True, "state": json.loads(proc.stdout)}
    except json.JSONDecodeError:
        return {"ok": False, "error": "invalid engine gate json"}


def run_gate_parallel_eval(prompt: str) -> dict[str, Any]:
    """Alias — always routes through engine.py."""
    return run_engine_gate(prompt)


def run_gate_reflect(text: str) -> dict[str, Any]:
    proc = subprocess.run(
        ["python3", GATE_CLI, "reflect", "--json"],
        cwd=REPO_ROOT,
        input=text,
        capture_output=True,
        text=True,
        timeout=30,
        check=False,
    )
    if not proc.stdout.strip():
        return {"error": proc.stderr.strip()}
    try:
        return json.loads(proc.stdout)
    except json.JSONDecodeError:
        return {"error": "invalid reflect json"}


def run_gate_verify(text: str) -> dict[str, Any]:
    """Legacy alias — same as reflect."""
    return run_gate_reflect(text)
