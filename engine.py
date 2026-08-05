#!/usr/bin/env python3
"""Scepticism Engine: Parallel Execution Host

L_2 parallel layer — execute this before token collapse. Runs independent
probes concurrently (memory, state), then updates gate state.

Usage:
    python3 engine.py --gate "your query"
    python3 engine.py --gate "your query" --json
    python3 engine.py --tasks '[{"task_id": "1", "command": "..."}]'
"""
from __future__ import annotations

import argparse
import json
import os
import shlex
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed

REPO_ROOT = os.path.dirname(os.path.abspath(__file__))
SCRIPTS_DIR = os.path.join(REPO_ROOT, "scripts")
sys.path.insert(0, SCRIPTS_DIR)

MAX_WORKERS = 4


def build_gate_tasks(query: str) -> list[dict]:
    q = shlex.quote(query)
    return [
        {
            "task_id": "memory",
            "command": f"python3 scripts/memory.py retrieve {q} --json --limit 5",
        },
        {
            "task_id": "memory_list",
            "command": "python3 scripts/memory.py list",
        },
        {
            "task_id": "gate_state",
            "command": "python3 scripts/gate.py state --json",
        },
    ]


class ParallelExecutionHost:
    def __init__(self) -> None:
        self.executor = ThreadPoolExecutor(max_workers=MAX_WORKERS)

    def _execute_single_task(self, task_id: str, command: str) -> dict:
        try:
            result = subprocess.run(
                command,
                shell=True,
                capture_output=True,
                text=True,
                timeout=30,
                cwd=REPO_ROOT,
            )
            return {
                "task_id": task_id,
                "command": command,
                "success": result.returncode == 0,
                "exit_code": result.returncode,
                "stdout": result.stdout.strip(),
                "stderr": result.stderr.strip(),
            }
        except subprocess.TimeoutExpired:
            return {
                "task_id": task_id,
                "command": command,
                "success": False,
                "exit_code": -1,
                "stdout": "",
                "stderr": "Task timed out after 30 seconds.",
            }
        except Exception as exc:
            return {
                "task_id": task_id,
                "command": command,
                "success": False,
                "exit_code": -1,
                "stdout": "",
                "stderr": str(exc),
            }

    def execute_parallel(self, tasks: list[dict]) -> dict:
        futures = {}
        results = []

        for task in tasks:
            task_id = task.get("task_id", "unknown")
            command = task.get("command", "")
            if command:
                futures[self.executor.submit(self._execute_single_task, task_id, command)] = task_id

        for future in as_completed(futures):
            try:
                results.append(future.result())
            except Exception as exc:
                results.append(
                    {
                        "task_id": futures[future],
                        "success": False,
                        "exit_code": -1,
                        "stdout": "",
                        "stderr": f"Thread execution failed: {exc}",
                    }
                )

        return {"results": results}

    def shutdown(self) -> None:
        self.executor.shutdown(wait=False)


def run_gate(query: str, json_output: bool = False) -> int:
    """Primary entry: parallel L_n layer + gate state update."""
    from gate_lib import (  # noqa: WPS433
        apply_parallel_from_envelope,
        audit_log,
        build_gate_context,
        load_state,
        save_state,
    )

    host = ParallelExecutionHost()
    envelope = host.execute_parallel(build_gate_tasks(query))
    host.shutdown()

    state = load_state()
    state = apply_parallel_from_envelope(state, query, envelope)
    save_state(state)
    audit_log(
        "engine_gate",
        {
            "query": query,
            "parallel_gate_passed": state.parallel_gate_passed,
            "memory_exit_code": state.last_memory.exit_code,
            "task_count": len(envelope.get("results", [])),
        },
    )

    if json_output:
        print(json.dumps(state.to_dict(), indent=2))
    else:
        print(build_gate_context(state))
    return 0


def main() -> None:
    parser = argparse.ArgumentParser(description="Scepticism Engine Parallel Execution Host")
    parser.add_argument(
        "--tasks",
        type=str,
        help="JSON array of tasks to run concurrently.",
    )
    parser.add_argument(
        "--gate",
        type=str,
        help="Run parallel pre-collapse layer for a query (primary entry point).",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="With --gate: output gate state as JSON.",
    )
    args = parser.parse_args()

    if args.gate is not None:
        raise SystemExit(run_gate(args.gate, json_output=args.json))

    if args.tasks:
        host = ParallelExecutionHost()
        try:
            tasks = json.loads(args.tasks)
            if not isinstance(tasks, list):
                tasks = [tasks]
            print(json.dumps(host.execute_parallel(tasks), indent=2))
        except json.JSONDecodeError:
            print(json.dumps({"error": "Invalid JSON provided for tasks."}))
        finally:
            host.shutdown()
        return

    print(json.dumps({"status": "Parallel Execution Host ready. Run: python3 engine.py --gate \"<query>\""}))


if __name__ == "__main__":
    main()
