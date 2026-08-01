#!/usr/bin/env python3
"""Scepticism Engine: Parallel Execution Host

This script acts as the parallel execution layer for the Scepticism Engine agent.
It does NOT call the LLM API. It stays open and listens for tasks from the agent,
executing independent tool calls concurrently in background threads to bypass
the sequential agent loop bottleneck.

Usage:
    python engine.py
"""
from __future__ import annotations
import os
import sys
import json
import shlex
import subprocess
import argparse
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Optional

# Maximum concurrent background tasks
MAX_WORKERS = 4

class ParallelExecutionHost:
    def __init__(self):
        self.active = True
        self.executor = ThreadPoolExecutor(max_workers=MAX_WORKERS)

    def _execute_single_task(self, task_id: str, command: str) -> dict:
        """Executes a single shell command in a background thread."""
        try:
            # Using subprocess to run the command (e.g., python memory.py retrieve "...")
            # Timeout set to 30s to prevent infinite hangs
            result = subprocess.run(
                command, 
                shell=True, 
                capture_output=True, 
                text=True, 
                timeout=30
            )
            return {
                "task_id": task_id,
                "command": command,
                "success": result.returncode == 0,
                "stdout": result.stdout.strip(),
                "stderr": result.stderr.strip()
            }
        except subprocess.TimeoutExpired:
            return {
                "task_id": task_id,
                "command": command,
                "success": False,
                "stdout": "",
                "stderr": "Task timed out after 30 seconds."
            }
        except Exception as e:
            return {
                "task_id": task_id,
                "command": command,
                "success": False,
                "stdout": "",
                "stderr": str(e)
            }

    def execute_parallel(self, tasks: list[dict]) -> str:
        """Receives a list of tasks, executes them in parallel, and returns JSON."""
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
            except Exception as e:
                results.append({
                    "task_id": futures[future],
                    "success": False,
                    "stdout": "",
                    "stderr": f"Thread execution failed: {e}"
                })

        # Output as JSON so the agent can parse it cleanly
        return json.dumps({"results": results}, indent=2)

    def run_cli(self, command: str):
        """Runs a single parallel batch from CLI arguments."""
        # Example: python engine.py --tasks '[{"task_id": "1", "command": "python memory.py retrieve query"}]'
        try:
            tasks = json.loads(command)
            if not isinstance(tasks, list):
                tasks = [tasks]
            output = self.execute_parallel(tasks)
            print(output)
        except json.JSONDecodeError:
            print(json.dumps({"error": "Invalid JSON provided for tasks."}))
        finally:
            self.shutdown()

    def shutdown(self):
        """Cleanly shuts down the thread pool."""
        self.executor.shutdown(wait=False)
        self.active = False

def main():
    parser = argparse.ArgumentParser(description="Scepticism Engine Parallel Execution Host")
    parser.add_argument(
        "--tasks", 
        type=str, 
        help='JSON array of tasks to run concurrently. Example: \'[{"task_id": "1", "command": "echo hello"}]\''
    )
    args = parser.parse_args()

    host = ParallelExecutionHost()

    if args.tasks:
        host.run_cli(args.tasks)
    else:
        # If no arguments provided, just confirm the host is ready.
        print(json.dumps({"status": "Parallel Execution Host ready. Waiting for tasks."}))

if __name__ == "__main__":
    main()
