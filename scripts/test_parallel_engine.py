#!/usr/bin/env python3
"""Tests for parallel_engine and gate formal evaluation."""
from __future__ import annotations

import os
import sys
import unittest

SCRIPTS = os.path.join(os.path.dirname(os.path.dirname(__file__)))
sys.path.insert(0, SCRIPTS)

from parallel_engine import evaluate_parallel  # noqa: E402
from gate_lib import GateState, apply_parallel_eval, reflect_on_response  # noqa: E402


class ParallelEngineTests(unittest.TestCase):
    def test_all_layers_run_concurrently(self):
        ev = evaluate_parallel("memory gate")
        self.assertEqual(ev.L_n, 1)
        self.assertIn("L_1", ev.witnesses)
        self.assertIn("L_8", ev.witnesses)
        self.assertTrue(ev.L_p)

    def test_L_p_is_set_not_empty_at_baseline(self):
        ev = evaluate_parallel("memory gate test")
        self.assertIsInstance(ev.L_p, set)
        self.assertGreater(len(ev.L_p), 0)

    def test_reflect_uses_lexicon_sets(self):
        state = GateState()
        state.parallel_gate_passed = True
        r = reflect_on_response("definitely certainly always", state)
        self.assertTrue(any("H_c" in m for m in r.collapse_markers))


if __name__ == "__main__":
    unittest.main()
