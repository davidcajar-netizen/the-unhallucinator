#!/usr/bin/env python3
"""Scepticism Engine: Parallel Execution Host (L_2 = O_d_g).

Evaluates Θ = {L_1 ∧ ... ∧ L_8} concurrently via scripts/parallel_engine.py.
Does not call the LLM API.

Usage:
    python3 engine.py --gate "query"
    python3 engine.py --gate "query" --json
"""
from __future__ import annotations

import argparse
import json
import os
import sys

REPO_ROOT = os.path.dirname(os.path.abspath(__file__))
SCRIPTS_DIR = os.path.join(REPO_ROOT, "scripts")
sys.path.insert(0, SCRIPTS_DIR)

from gate_lib import audit_log, apply_parallel_eval_result, load_state, save_state, format_parallel_context  # noqa: E402
from parallel_engine import evaluate_parallel  # noqa: E402


def run_gate(query: str, json_output: bool = False) -> int:
    state = load_state()
    prior = evaluate_parallel(
        query,
        triangulation_sources=state.triangulation.sources,
        inference_seeds=state.inference_seeds,
        epistemic_reflect=state.epistemic_reflect,
    )
    state = apply_parallel_eval_result(state, query, prior)
    save_state(state)
    audit_log(
        "engine_gate",
        {
            "query": query,
            "L_p": sorted(prior.L_p),
            "D_m": prior.D_m,
            "C_i": prior.C_i,
            "E_i": prior.E_i,
        },
    )
    if json_output:
        out = state.to_dict()
        out["parallel_eval"] = prior.to_dict()
        print(json.dumps(out, indent=2))
    else:
        print(format_parallel_context(state, prior))
    return 0


def main() -> None:
    parser = argparse.ArgumentParser(description="Scepticism Engine Parallel Execution Host")
    parser.add_argument("--tasks", type=str, help="Legacy JSON task array (parallel shell batch).")
    parser.add_argument("--gate", type=str, help="Evaluate Θ in parallel for query.")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    if args.gate is not None:
        raise SystemExit(run_gate(args.gate, json_output=args.json))

    if args.tasks:
        from parallel_engine import _run_shell  # noqa: WPS433
        import concurrent.futures

        tasks = json.loads(args.tasks)
        if not isinstance(tasks, list):
            tasks = [tasks]
        results = []
        with concurrent.futures.ThreadPoolExecutor(max_workers=8) as pool:
            futs = {
                pool.submit(_run_shell, t.get("command", "")): t.get("task_id", "unknown")
                for t in tasks
                if t.get("command")
            }
            for fut in concurrent.futures.as_completed(futs):
                tid = futs[fut]
                raw = fut.result()
                results.append(
                    {
                        "task_id": tid,
                        "success": raw.get("success", False),
                        "stdout": raw.get("stdout", ""),
                        "stderr": raw.get("stderr", ""),
                    }
                )
        print(json.dumps({"results": results}, indent=2))
        return

    print(json.dumps({"status": "ready", "entry": "python3 engine.py --gate \"<query>\""}))


if __name__ == "__main__":
    main()
