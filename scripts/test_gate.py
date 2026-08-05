#!/usr/bin/env python3
"""Tests for Scepticism Engine gate layer."""
from __future__ import annotations

import json
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
    save_state,
    verify_response,
)


class GateLibTests(unittest.TestCase):
    def test_extract_query_strips_gate_pass(self):
        q = extract_query("GATE_PASS tell me about memory gates")
        self.assertNotIn("GATE_PASS", q)
        self.assertIn("memory", q.lower())

    def test_verify_fails_high_confidence_at_baseline(self):
        state = GateState()
        state.parallel_gate_passed = True
        text = "This is definitely true and certainly always correct."
        result = verify_response(text, state)
        self.assertFalse(result.passed)
        self.assertTrue(result.violations)

    def test_verify_passes_hedged_uncertainty(self):
        state = GateState()
        state.parallel_gate_passed = True
        text = "I cannot verify from direct observation; training prior may be wrong at C_i=0.5."
        result = verify_response(text, state)
        self.assertTrue(result.passed)

    def test_state_roundtrip(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "state.json")
            state = GateState()
            state.last_memory.query = "test query"
            save_state(state, path)
            loaded = load_state(path)
            self.assertEqual(loaded.last_memory.query, "test query")

    def test_parallel_eval_sets_L_n(self):
        state = apply_parallel_eval(GateState(), "memory gate test")
        self.assertEqual(state.L_n, 1)
        self.assertTrue(state.parallel_gate_passed)


if __name__ == "__main__":
    unittest.main()
