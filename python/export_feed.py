#!/usr/bin/env python3
"""Validate feed/current.json against the sheet contract."""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FEED = ROOT / "feed" / "current.json"
ALLOWED_PLAY = {"OVER", "UNDER", "WATCH", "PASS"}
ALLOWED_MARKET = {"k", "outs", "hits", "tb", "hr", "hrr", "sb", "rbi", "runs"}
ALLOWED_STATUS = {"SEED_PRIOR", "LIVE", "LOCKED", "GRADED"}
REQUIRED_GAME = ("id", "away", "home", "when")
REQUIRED_PROP = ("id", "player", "team", "market", "play", "game_id")


def main() -> int:
    if not FEED.exists():
        print(f"missing {FEED}", file=sys.stderr)
        return 1
    card = json.loads(FEED.read_text())
    games = card.get("games") or []
    props = card.get("props") or []
    ids = {g.get("id") for g in games}
    bad = []
    if card.get("card_type") != "player_props":
        bad.append("card_type")
    if card.get("status") not in ALLOWED_STATUS:
        bad.append(f"status={card.get('status')}")
    for g in games:
        miss = [k for k in REQUIRED_GAME if not g.get(k)]
        if miss:
            bad.append(f"game {g.get('id')} missing {miss}")
    missing = [p.get("id") for p in props if p.get("game_id") not in ids]
    if missing:
        bad.append(f"props with unknown game_id: {missing}")
    for p in props:
        miss = [k for k in REQUIRED_PROP if not p.get(k)]
        if miss:
            bad.append(f"prop {p.get('id')} missing {miss}")
        if p.get("market") not in ALLOWED_MARKET:
            bad.append(f"prop {p.get('id')} market={p.get('market')}")
        if p.get("play") not in ALLOWED_PLAY:
            bad.append(f"prop {p.get('id')} play={p.get('play')}")
    print(
        f"date={card.get('date')} status={card.get('status')} "
        f"games={len(games)} props={len(props)}"
    )
    if bad:
        print("FAIL", *bad, sep="\n  ", file=sys.stderr)
        return 1
    print("ok")
    return 0


if __name__ == "__main__":
    sys.exit(main())
