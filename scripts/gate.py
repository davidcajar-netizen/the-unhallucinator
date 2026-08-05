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
    REPO_ROOT,
    DEFAULT_AUDIT_PATH,
    DEFAULT_STATE_PATH,
    apply_reflection,
    audit_log,
    build_gate_context,
    load_state,
    reflect_on_response,
    save_state,
    verify_response,
)


def cmd_parallel_eval(args: argparse.Namespace) -> int:
    """Delegate to engine.py --gate (canonical parallel entry)."""
    import subprocess

    query = args.query or ""
    cmd = ["python3", os.path.join(REPO_ROOT, "engine.py"), "--gate", query]
    if args.json:
        cmd.append("--json")
    proc = subprocess.run(cmd, cwd=REPO_ROOT, check=False)
    if proc.returncode != 0:
        return proc.returncode
    audit_log(
        "parallel_eval_via_engine",
        {"query": query},
        args.audit_path,
    )
    return 0


def cmd_reflect(args: argparse.Namespace) -> int:
    state = load_state(args.state_path)
    text = args.text or ""
    if args.text_file:
        with open(args.text_file, "r", encoding="utf-8") as fh:
            text = fh.read()
    if not text and not sys.stdin.isatty():
        text = sys.stdin.read()

    reflection = reflect_on_response(text, state)
    state = apply_reflection(state, reflection)
    save_state(state, args.state_path)
    audit_log("reflect", reflection.to_dict(), args.audit_path)

    if args.json:
        print(json.dumps(reflection.to_dict(), indent=2))
    else:
        print(f"[gate] epistemic reflect C_i={reflection.certainty_score:.2f}")
        for note in reflection.epistemic_notes:
            print(f"  note: {note}")
        for seed in reflection.inference_seeds:
            print(f"  infer: {seed}")
        for marker in reflection.collapse_markers:
            print(f"  collapse: {marker}")
    return 0


def cmd_verify(args: argparse.Namespace) -> int:
    """Audit alias for reflect — no fail exit code."""
    state = load_state(args.state_path)
    text = args.text or ""
    if args.text_file:
        with open(args.text_file, "r", encoding="utf-8") as fh:
            text = fh.read()
    if not text and not sys.stdin.isatty():
        text = sys.stdin.read()

    result = verify_response(text, state)
    reflection = reflect_on_response(text, state)
    state = apply_reflection(state, reflection)
    save_state(state, args.state_path)
    audit_log("verify_alias", reflection.to_dict(), args.audit_path)

    if args.json:
        out = reflection.to_dict()
        out["legacy_verify"] = result.to_dict()
        print(json.dumps(out, indent=2))
    else:
        cmd_reflect(args)
    return 0


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

    vf = sub.add_parser("verify", help="audit alias for reflect (no fail/stop semantics)")
    vf.add_argument("text", nargs="?", default="")
    vf.add_argument("--text-file", help="read text from file")
    vf.add_argument("--json", action="store_true")
    vf.set_defaults(func=cmd_verify)

    rf = sub.add_parser("reflect", help="epistemic reflection after collapse — feeds next inference")
    rf.add_argument("text", nargs="?", default="")
    rf.add_argument("--text-file", help="read text from file")
    rf.add_argument("--json", action="store_true")
    rf.set_defaults(func=cmd_reflect)

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
