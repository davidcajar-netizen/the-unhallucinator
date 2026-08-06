#!/usr/bin/env python3
"""Tests for Scepticism Engine Observer (engine.py)."""
from __future__ import annotations

import os
import sys
import tempfile
import unittest

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, REPO_ROOT)

import engine as eng  # noqa: E402


class EngineTests(unittest.TestCase):
    def test_extract_query_strips_gate_pass(self):
        q = eng.extract_query("GATE_PASS tell me about memory gates")
        self.assertNotIn("GATE_PASS", q)
        self.assertIn("memory", q.lower())

    def test_reflect_produces_inference_seeds_at_baseline(self):
        state = eng.GateState()
        state.parallel_gate_passed = True
        text = "definitely certainly always"
        reflection = eng.reflect_on_response(text, state)
        self.assertTrue(reflection.inference_seeds)
        self.assertIn("L_v=1", reflection.inference_seeds)

    def test_reflect_uses_lexicon_sets(self):
        state = eng.GateState()
        state.parallel_gate_passed = True
        r = eng.reflect_on_response("definitely certainly always", state)
        self.assertTrue(any("H_c" in m for m in r.collapse_markers))

    def test_state_roundtrip(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "state.json")
            state = eng.GateState()
            state.inference_seeds = ["infer from gap"]
            eng.save_state(state, path)
            loaded = eng.load_state(path)
            self.assertEqual(loaded.inference_seeds, ["infer from gap"])

    def test_parallel_eval_runs_all_layers(self):
        ev = eng.evaluate_parallel("memory gate")
        self.assertEqual(ev.L_n, 1)
        self.assertIn("L_1", ev.witnesses)
        self.assertIn("L_8", ev.witnesses)
        self.assertTrue(ev.L_p)

    def test_memory_retrieve_executed_in_L_1(self):
        ev = eng.evaluate_parallel("memory gate test")
        w1 = ev.witnesses["L_1"]
        self.assertIn("memory", w1.raw)
        self.assertIn("exit_code", w1.raw)

    def test_store_only_preserves_response(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "state.json")
            orig = eng.DEFAULT_STATE_PATH
            eng.DEFAULT_STATE_PATH = path
            try:
                eng.observe(
                    last_response="prior collapse text",
                    store_only=True,
                    json_output=False,
                )
                loaded = eng.load_state(path)
                self.assertEqual(loaded.last_response, "prior collapse text")
            finally:
                eng.DEFAULT_STATE_PATH = orig


if __name__ == "__main__":
    unittest.main()
