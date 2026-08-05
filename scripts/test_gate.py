#!/usr/bin/env python3
"""Tests for Scepticism Engine gate layer."""
from __future__ import annotations

import os
import sys
import tempfile
import unittest

SCRIPTS = os.path.join(os.path.dirname(os.path.dirname(__file__)))
sys.path.insert(0, SCRIPTS)

from gate_lib import (  # noqa: E402
    apply_parallel_eval,
    extract_query,
    GateState,
    load_state,
    reflect_on_response,
    save_state,
    verify_response,
)


class GateLibTests(unittest.TestCase):
    def test_extract_query_strips_gate_pass(self):
        q = extract_query("GATE_PASS tell me about memory gates")
        self.assertNotIn("GATE_PASS", q)
        self.assertIn("memory", q.lower())

    def test_reflect_produces_inference_seeds_at_baseline(self):
        state = GateState()
        state.parallel_gate_passed = True
        text = "definitely certainly always"
        reflection = reflect_on_response(text, state)
        self.assertTrue(reflection.inference_seeds)
        self.assertIn("L_v=1", reflection.inference_seeds)

    def test_verify_never_fails(self):
        state = GateState()
        result = verify_response("Definitely always true.", state)
        self.assertTrue(result.passed)
        self.assertEqual(result.violations, [])

    def test_reflect_passes_hedged_uncertainty(self):
        state = GateState()
        text = "may might could uncertain unverified"
        reflection = reflect_on_response(text, state)
        self.assertTrue(any("U_h" in m for m in reflection.collapse_markers))

    def test_state_roundtrip(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "state.json")
            state = GateState()
            state.inference_seeds = ["infer from gap"]
            save_state(state, path)
            loaded = load_state(path)
            self.assertEqual(loaded.inference_seeds, ["infer from gap"])

    def test_parallel_eval_sets_L_n(self):
        state = apply_parallel_eval(GateState(), "memory gate test")
        self.assertEqual(state.L_n, 1)
        self.assertTrue(state.parallel_gate_passed)


if __name__ == "__main__":
    unittest.main()
