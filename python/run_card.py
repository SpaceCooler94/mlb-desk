#!/usr/bin/env python3
"""Same CLI as build_day.py, with the research stack applied on the way out."""

from __future__ import annotations

import argparse
import json
import sys

import build_day as b
from stack_hook import apply_stack, record_history, stack_flags


def wrap(day, phase, fresh):
    card = b.build(day, phase, fresh)
    card["props"] = apply_stack(card["props"], card["season"], refresh=(phase == "morning"))
    if phase == "grade":
        record_history(card["date"], card["props"])
    card["stack"] = stack_flags()
    engines = sorted({p.get("engine") or "rate" for p in card["props"]})
    extra = f" Engines this card: {', '.join(engines)}."
    if extra.strip() not in (card.get("disclaimer") or ""):
        card["disclaimer"] = (card.get("disclaimer") or "").rstrip(".") + "." + extra
    return card


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--date", help="YYYY-MM-DD (CT slate date)")
    p.add_argument("--phase", default="auto", choices=["auto", "morning", "noon", "lock", "grade"])
    p.add_argument("--fresh", action="store_true")
    p.add_argument("--dry-run", action="store_true")
    args = p.parse_args()
    phase = b.auto_phase() if args.phase == "auto" else args.phase
    day = b.parse_date(args.date, phase)
    card = wrap(day, phase, args.fresh)
    ids = {g["id"] for g in card["games"]}
    missing = [x["id"] for x in card["props"] if x["game_id"] not in ids]
    if missing:
        print("props with unknown game_id", missing, file=sys.stderr)
        return 1
    print(
        f"date={card['date']} phase={phase} status={card['status']} "
        f"games={len(card['games'])} props={len(card['props'])} stack={card.get('stack')}"
    )
    if args.dry_run:
        return 0
    b.FEED.parent.mkdir(parents=True, exist_ok=True)
    b.FEED.write_text(json.dumps(card, indent=2) + "\n")
    print(f"wrote {b.FEED}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
