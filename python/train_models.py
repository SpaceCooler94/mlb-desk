#!/usr/bin/env python3
"""Fit residual + calibration models from feed/history.jsonl.

  python3 train_models.py
  python3 train_models.py --min-rows 40

Daily card does not train. Grade phase appends history; run this after
you have a few weeks of boxes, or wire it as a weekly workflow later.
"""

from __future__ import annotations

import argparse
import json
import sys

from stack import available, load_history, train_from_history


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--min-rows", type=int, default=40)
    args = p.parse_args()
    print("stack", json.dumps(available()))
    print("history", len(load_history()))
    report = train_from_history(min_rows=args.min_rows)
    print(json.dumps(report, indent=2))
    if report["n"] < args.min_rows:
        print("thin history — rate model stays in charge", file=sys.stderr)
        return 0
    return 0


if __name__ == "__main__":
    sys.exit(main())
