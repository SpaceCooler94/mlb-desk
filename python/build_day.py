#!/usr/bin/env python3
"""Rebuild feed/current.json for one MLB date.

Source rank 1: MLB Stats API schedule, probable pitchers, posted lineups,
season boards + starter game logs. Park factors are structural priors.

  python3 build_day.py
  python3 build_day.py --date 2026-09-23 --phase noon
  python3 build_day.py --phase grade --fresh
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

from desk_engine import (
    STATS,
    get_json,
    grade_props,
    looks_for,
    parse_lineups,
    project_hitter,
    seed_all,
    slot_of,
)
from props import SIGMA, p_over

ROOT = Path(__file__).resolve().parents[1]
FEED = ROOT / "feed" / "current.json"
LINES = ROOT / "feed" / "lines.json"
CT = ZoneInfo("America/Chicago")

ABBR = {"AZ": "ARI", "ARI": "ARI"}

PARK = {
    1: "Angel Stadium", 2: "Camden Yards", 3: "Fenway", 4: "Rate Field",
    5: "Progressive", 7: "Kauffman", 12: "Tropicana", 14: "Rogers Centre",
    15: "Chase", 17: "Wrigley", 19: "Coors", 22: "Dodger Stadium",
    31: "PNC Park", 32: "American Family", 2392: "Daikin", 2394: "Comerica",
    2395: "Oracle Park", 2529: "Sutter Health", 2602: "GABP", 2680: "Petco",
    2681: "Citizens Bank", 2889: "Busch", 3289: "Citi Field",
    3309: "Nationals Park", 3313: "Yankee Stadium", 4169: "loanDepot",
    4705: "Truist", 5325: "Globe Life", 680: "T-Mobile",
}
ROOF_CLOSED = {12, 14, 15, 32, 2392, 4169, 5325, 680}

_slot = slot_of


def today_ct(now: datetime | None = None) -> date:
    return (now or datetime.now(CT)).date()


def parse_date(raw: str | None, phase: str, now: datetime | None = None) -> date:
    now = now or datetime.now(CT)
    if raw:
        return date.fromisoformat(raw)
    if phase == "grade" and now.hour < 8:
        return now.date() - timedelta(days=1)
    return now.date()


def auto_phase(now: datetime | None = None) -> str:
    now = now or datetime.now(CT)
    if now.hour < 10:
        return "morning"
    if now.hour < 16:
        return "noon"
    if now.hour < 23:
        return "lock"
    return "grade"


def _abbr(team: dict) -> str:
    raw = (team.get("abbreviation") or team.get("teamCode") or "").upper()
    return ABBR.get(raw, raw)


def _when(iso: str, state: str) -> str:
    if not iso:
        return "TBD"
    dt = datetime.fromisoformat(iso.replace("Z", "+00:00")).astimezone(CT)
    days = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
    detail = (state or "").lower()
    if "final" in detail:
        return f"{days[dt.weekday()]} FINAL"
    if "delay" in detail:
        return f"{days[dt.weekday()]} DELAY"
    if "postpon" in detail:
        return f"{days[dt.weekday()]} PPD"
    hour = dt.strftime("%I:%M%p").lstrip("0").replace("PM", "p").replace("AM", "a")
    return f"{days[dt.weekday()]} {hour}"


def _park(venue: dict) -> str:
    vid = int(venue.get("id") or 0)
    return PARK.get(vid) or venue.get("name") or "—"


def _roof(venue: dict, weather: dict | None) -> str | None:
    vid = int(venue.get("id") or 0)
    if vid in ROOF_CLOSED:
        return "CLOSED"
    cond = str((weather or {}).get("condition") or "").lower()
    if "dome" in cond or "roof closed" in cond:
        return "CLOSED"
    return None


def fetch_schedule(day: date) -> dict:
    hydrate = "probablePitcher,venue,weather,team,linescore,lineups"
    return get_json(f"{STATS}/schedule?sportId=1&date={day.isoformat()}&hydrate={hydrate}")


def _lineup_side(players):
    from desk_engine import lineup_side
    return lineup_side(players)


def parse_games(board: dict) -> list[dict]:
    out = []
    for d in board.get("dates") or []:
        slate = d.get("date")
        for g in d.get("games") or []:
            aw, hm = g.get("teams", {}).get("away") or {}, g.get("teams", {}).get("home") or {}
            at, ht = aw.get("team") or {}, hm.get("team") or {}
            aab, hab = _abbr(at), _abbr(ht)
            state = (g.get("status") or {}).get("detailedState") or ""
            venue = g.get("venue") or {}
            weather = g.get("weather") or {}
            pk = g.get("gamePk")
            cards = parse_lineups(g)
            game = {
                "id": f"{slate}_{aab}_{hab}_{pk}",
                "gamePk": pk,
                "when": _when(g.get("gameDate") or "", state),
                "away": aab,
                "home": hab,
                "park": _park(venue),
                "venue": venue.get("name"),
                "venue_id": venue.get("id"),
                "away_sp": (aw.get("probablePitcher") or {}).get("fullName") or "TBD",
                "home_sp": (hm.get("probablePitcher") or {}).get("fullName") or "TBD",
                "away_sp_id": (aw.get("probablePitcher") or {}).get("id"),
                "home_sp_id": (hm.get("probablePitcher") or {}).get("id"),
                "state": state,
                "abstract": (g.get("status") or {}).get("abstractGameState") or "",
                "away_lineup": cards["away"],
                "home_lineup": cards["home"],
                "lineup_tag": cards["tag"],
            }
            roof = _roof(venue, weather)
            if roof:
                game["roof"] = roof
            if "delay" in state.lower():
                game["note"] = state
            if weather.get("condition"):
                game["weather"] = {
                    "condition": weather.get("condition"),
                    "temp": weather.get("temp"),
                    "wind": weather.get("wind"),
                }
            out.append(game)
    return out


def load_json(path: Path, default):
    if not path.exists():
        return default
    return json.loads(path.read_text())


def merge_props(old: list[dict], fresh: list[dict], keep_manual: bool) -> list[dict]:
    if not keep_manual:
        return fresh
    prev = {p["id"]: p for p in old if p.get("id")}
    out, seen = [], set()
    keep = (None, "", "SEED_PRIOR auto", "SEED_PRIOR season K/9 x IP x park")
    for p in fresh:
        if p["id"] in prev:
            oldp = prev[p["id"]]
            for k in ("line", "proj", "play", "units", "note", "sigma"):
                if oldp.get(k) not in keep:
                    p[k] = oldp[k]
            if oldp.get("line") is not None and oldp.get("proj") is not None:
                p["edge"] = round(float(p["proj"]) - float(p["line"]), 2 if p["market"] == "hr" else 1)
                po = p_over(float(p["proj"]), float(p["line"]), p["market"], float(p.get("sigma") or SIGMA.get(p["market"], 1)))
                p["p_over"] = None if po is None else round(po, 2)
            if oldp.get("actual") is not None:
                p["actual"] = oldp["actual"]
            if oldp.get("result"):
                p["result"] = oldp["result"]
        out.append(p)
        seen.add(p["id"])
    gids = {x["game_id"] for x in fresh}
    for p in old:
        if p.get("id") not in seen and p.get("game_id") in gids:
            out.append(p)
    return out


def status_for(phase: str, games: list[dict], props: list[dict]) -> str:
    if not games:
        return "SEED_PRIOR"
    named = sum(1 for g in games if g.get("away_sp") not in (None, "TBD") and g.get("home_sp") not in (None, "TBD"))
    finals = sum(1 for g in games if "FINAL" in str(g.get("when") or "") or g.get("abstract") == "Final")
    graded = sum(1 for p in props if p.get("actual") is not None)
    cards = sum(1 for g in games if g.get("lineup_tag") == "CONFIRMED")
    if phase == "grade" and finals == len(games) and graded:
        return "GRADED"
    if phase == "lock":
        return "LOCKED"
    if phase == "noon" and (named >= max(1, int(0.75 * len(games))) or cards):
        return "LIVE"
    if phase == "grade" and graded:
        return "LOCKED"
    return "SEED_PRIOR"


def strip_internal(games: list[dict]) -> list[dict]:
    drop = {"away_lineup", "home_lineup"}
    return [{k: v for k, v in g.items() if k not in drop} for g in games]


def build(day: date, phase: str, fresh: bool) -> dict:
    board = fetch_schedule(day)
    games = parse_games(board)
    if not games:
        raise SystemExit(f"empty slate {day.isoformat()}")
    season = day.year
    lines = load_json(LINES, {})
    new_props = seed_all(games, season, day.isoformat(), lines)
    old = load_json(FEED, {})
    same_day = old.get("date") == day.isoformat()
    if same_day and not fresh:
        props = merge_props(old.get("props") or [], new_props, keep_manual=True)
        old_looks = {g["id"]: g.get("looks") for g in old.get("games") or [] if g.get("looks")}
        for g in games:
            if g["id"] in old_looks and old_looks[g["id"]]:
                g["looks"] = old_looks[g["id"]]
    else:
        props = new_props
    if phase == "grade":
        props = grade_props(games, props)
    for g in games:
        if not g.get("looks"):
            g["looks"] = looks_for(g, props)
    st = status_for(phase, games, props)
    named = sum(1 for g in games if g.get("away_sp") != "TBD" and g.get("home_sp") != "TBD")
    cards = sum(1 for g in games if g.get("lineup_tag") == "CONFIRMED")
    disclaimer = (
        f"{day.isoformat()} slate from MLB Stats API. {named}/{len(games)} starters named. "
        f"{cards}/{len(games)} lineup cards posted. "
        f"Props are {st} — pitcher K/outs from K/9 x IP x park; "
        f"batter hits/TB/HR from slot PA x rates x opponent ERA x park. Not tickets."
    )
    return {
        "season": season,
        "date": day.isoformat(),
        "status": st,
        "card_type": "player_props",
        "layout": "xdesk-sheet",
        "generated_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "timezone": "America/Chicago",
        "disclaimer": disclaimer,
        "source": "mlb-desk",
        "feed_version": int(old.get("feed_version") or 2) + (0 if same_day else 1),
        "phase": phase,
        "games": strip_internal(games),
        "props": props,
    }


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--date", help="YYYY-MM-DD (CT slate date)")
    p.add_argument("--phase", default="auto", choices=["auto", "morning", "noon", "lock", "grade"])
    p.add_argument("--fresh", action="store_true")
    p.add_argument("--dry-run", action="store_true")
    args = p.parse_args()
    phase = auto_phase() if args.phase == "auto" else args.phase
    day = parse_date(args.date, phase)
    card = build(day, phase, args.fresh)
    ids = {g["id"] for g in card["games"]}
    missing = [x["id"] for x in card["props"] if x["game_id"] not in ids]
    if missing:
        print("props with unknown game_id", missing, file=sys.stderr)
        return 1
    print(f"date={card['date']} phase={phase} status={card['status']} games={len(card['games'])} props={len(card['props'])}")
    if args.dry_run:
        return 0
    FEED.parent.mkdir(parents=True, exist_ok=True)
    FEED.write_text(json.dumps(card, indent=2) + "\n")
    print(f"wrote {FEED}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
