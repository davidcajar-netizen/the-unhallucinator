#!/usr/bin/env python3
"""CLI for Scepticism Engine gate enforcement.

  parallel-eval   Run parallel pre-collapse evaluation (memory + probes)
  verify          Score text against gate state
  state           Show or reset gate state
  audit           Tail recent audit log entries
"""
from __future__ import annotations

import argparse
import json
import os
import sys

from gate_lib import (
    DEFAULT_AUDIT_PATH,
    DEFAULT_STATE_PATH,
    apply_parallel_eval,
    audit_log,
    build_gate_context,
    load_state,
    save_state,
    verify_response,
)


def cmd_parallel_eval(args: argparse.Namespace) -> int:
    state = load_state(args.state_path)
    state = apply_parallel_eval(state, args.query or "")
    save_state(state, args.state_path)
    audit_log(
        "parallel_eval",
        {
            "query": state.last_memory.query,
            "parallel_gate_passed": state.parallel_gate_passed,
            "memory_exit_code": state.last_memory.exit_code,
            "effective_certainty": state.last_memory.max_epistemic,
        },
        args.audit_path,
    )
    if args.json:
        print(json.dumps(state.to_dict(), indent=2))
    else:
        print(build_gate_context(state))
    return 0


def cmd_verify(args: argparse.Namespace) -> int:
    state = load_state(args.state_path)
    text = args.text or ""
    if args.text_file:
        with open(args.text_file, "r", encoding="utf-8") as fh:
            text = fh.read()
    if not text and not sys.stdin.isatty():
        text = sys.stdin.read()

    result = verify_response(text, state)
    state.last_verification = result.to_dict()
    save_state(state, args.state_path)
    audit_log("verify", result.to_dict(), args.audit_path)

    if args.json:
        print(json.dumps(result.to_dict(), indent=2))
    else:
        status = "PASS" if result.passed else "FAIL"
        print(f"[gate] verification {status} (C_i={result.certainty_score:.2f})")
        for v in result.violations:
            print(f"  VIOLATION: {v}")
        for w in result.warnings:
            print(f"  warning: {w}")

    return 0 if result.passed else 1


def cmd_state(args: argparse.Namespace) -> int:
    if args.reset:
        from gate_lib import GateState

        save_state(GateState(), args.state_path)
        if args.json:
            print(json.dumps({"reset": True}))
        else:
            print("[gate] state reset")
        return 0

    state = load_state(args.state_path)
    if args.json:
        print(json.dumps(state.to_dict(), indent=2))
    else:
        print(build_gate_context(state))
    return 0


def cmd_context(args: argparse.Namespace) -> int:
    state = load_state(args.state_path)
    print(build_gate_context(state))
    return 0


def cmd_audit(args: argparse.Namespace) -> int:
    path = args.audit_path
    if not os.path.isfile(path):
        print("[gate] no audit log yet")
        return 0
    with open(path, "r", encoding="utf-8") as fh:
        lines = fh.readlines()
    for line in lines[-args.limit:]:
        print(line.rstrip())
    return 0


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--state-path", default=DEFAULT_STATE_PATH)
    p.add_argument("--audit-path", default=DEFAULT_AUDIT_PATH)
    sub = p.add_subparsers(dest="command", required=True)

    pe = sub.add_parser("parallel-eval", help="run parallel pre-collapse gate")
    pe.add_argument("query", nargs="?", default="", help="query text or prompt excerpt")
    pe.add_argument("--json", action="store_true")
    pe.set_defaults(func=cmd_parallel_eval)

    vf = sub.add_parser("verify", help="verify response text against gate state")
    vf.add_argument("text", nargs="?", default="")
    vf.add_argument("--text-file", help="read text from file")
    vf.add_argument("--json", action="store_true")
    vf.set_defaults(func=cmd_verify)

    st = sub.add_parser("state", help="show or reset gate state")
    st.add_argument("--json", action="store_true")
    st.add_argument("--reset", action="store_true")
    st.set_defaults(func=cmd_state)

    cx = sub.add_parser("context", help="print gate context block for injection")
    cx.set_defaults(func=cmd_context)

    au = sub.add_parser("audit", help="show recent audit log lines")
    au.add_argument("--limit", type=int, default=20)
    au.set_defaults(func=cmd_audit)

    return p


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
