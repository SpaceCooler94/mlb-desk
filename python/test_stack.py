#!/usr/bin/env python3
"""Stack unit tests. Network-free. Works with or without the heavy libs."""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from unittest import mock

import stack


class TestStackMath(unittest.TestCase):
    def test_pct_detects_fraction_and_percent(self):
        self.assertEqual(stack._pct(0.225), 22.5)
        self.assertEqual(stack._pct(22.5), 22.5)
        self.assertIsNone(stack._pct(None))

    def test_norm_name(self):
        self.assertEqual(stack._norm_name("Aaron Judge"), "aaronjudge")
        self.assertEqual(stack._norm_name("Aaron Judge"), stack._norm_name("aaron  judge"))

    def test_adjust_hitter_barrel_lifts_hr(self):
        s = stack.Stack(
            2026,
            hitters={"aaronjudge": {"name": "Aaron Judge", "barrel": 22.0, "hardhit": 58.0, "ev": 96.0}},
            pitchers={},
            models={},
            cal={},
        )
        hi = s.adjust_hitter("Aaron Judge", "hr", 0.20, {"park": 1.16, "slot": 2})
        lo = s.adjust_hitter("Nobody", "hr", 0.20, {"park": 1.16, "slot": 2})
        self.assertGreater(hi.proj, lo.proj)
        self.assertIn("Barrel", hi.note)
        self.assertEqual(lo.engine, "rate")
        self.assertIn("savant", hi.engine)

    def test_adjust_pitcher_k_pct_lifts_k(self):
        s = stack.Stack(
            2026,
            hitters={},
            pitchers={"tarikskubal": {"name": "Tarik Skubal", "k_pct": 31.0, "csw": 32.0}},
            models={},
            cal={},
        )
        hi = s.adjust_pitcher("Tarik Skubal", "k", 6.0, {"park": 1.0})
        lo = s.adjust_pitcher("Nobody", "k", 6.0, {"park": 1.0})
        self.assertGreater(hi.proj, lo.proj)

    def test_calibrate_piecewise(self):
        s = stack.Stack(2026, {}, {}, {}, {"k": {"x": [0.2, 0.5, 0.8], "y": [0.25, 0.48, 0.7]}})
        self.assertEqual(s.calibrate("k", 0.5), 0.48)
        self.assertIsNone(s.calibrate("k", None))

    def test_boards_frame_without_pandas_is_none_or_frame(self):
        board = {1: {"avg": ".300", "homeRuns": 20}}
        frame = stack.boards_frame(board, "hitting")
        if stack.FLAGS["pandas"]:
            self.assertEqual(len(frame), 1)
            self.assertEqual(int(frame.iloc[0]["pid"]), 1)
        else:
            self.assertIsNone(frame)

    def test_history_roundtrip(self):
        rows = [{"date": "2026-09-22", "market": "k", "proj": 6.1, "actual": 7, "line": 5.5}]
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / "history.jsonl"
            with mock.patch.object(stack, "HISTORY", path):
                n = stack.append_history(rows)
                self.assertEqual(n, 1)
                loaded = stack.load_history()
                self.assertEqual(loaded[0]["actual"], 7)

    def test_train_thin_history_noop(self):
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / "history.jsonl"
            models = Path(td) / "models"
            models.mkdir()
            path.write_text("")
            with mock.patch.object(stack, "HISTORY", path), mock.patch.object(stack, "MODELS", models):
                report = stack.train_from_history(min_rows=40)
                self.assertEqual(report["n"], 0)

    def test_available_keys(self):
        flags = stack.available()
        for key in ("pandas", "numpy", "sklearn", "xgboost", "pybaseball"):
            self.assertIn(key, flags)
            self.assertIsInstance(flags[key], bool)


class TestIndexFrames(unittest.TestCase):
    def test_index_hitters_from_fake_frame(self):
        if not stack.FLAGS["pandas"]:
            self.skipTest("pandas not installed")
        pd = stack.MODS["pd"]
        df = pd.DataFrame([{"Name": "Aaron Judge", "Barrel%": 21.4, "HardHit%": 61.2, "EV": 96.1}])
        idx = stack._index_hitters(df)
        self.assertIn("aaronjudge", idx)
        self.assertAlmostEqual(idx["aaronjudge"]["barrel"], 21.4)


if __name__ == "__main__":
    unittest.main()
