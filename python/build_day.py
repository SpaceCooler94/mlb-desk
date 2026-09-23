#!/usr/bin/env python3
"""Rebuild feed/current.json for one MLB date.

Source: MLB Stats API schedule + probable pitchers + season pitching splits.
Lines come from feed/lines.json when present; otherwise a seed x.5 on the model.

  python3 build_day.py
  python3 build_day.py --date 2026-09-23 --phase noon
  python3 build_day.py --phase grade --fresh
"""

from __future__ import annotations

import argparse
import json
import sys
import urllib.request
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

from props import SIGMA, half_line, p_over, play

ROOT = Path(__file__).resolve().parents[1]
FEED = ROOT / "feed" / "current.json"
LINES = ROOT / "feed" / "lines.json"
PRIORS = ROOT / "feed" / "priors.json"
STATS = "https://statsapi.mlb.com/api/v1"
UA = "mlb-desk/1.0 (+https://github.com/SpaceCooler94/mlb-desk)"
CT = ZoneInfo("America/Chicago")

ABBR = {"AZ": "ARI", "ARI": "ARI"}

PARK = {
    1: "Angel Stadium",
    2: "Camden Yards",
    3: "Fenway",
    4: "Rate Field",
    5: "Progressive",
    7: "Kauffman",
    12: "Tropicana",
    14: "Rogers Centre",
    15: "Chase",
    17: "Wrigley",
    19: "Coors",
    22: "Dodger Stadium",
    31: "PNC Park",
    32: "American Family",
    2392: "Daikin",
    2394: "Comerica",
    2395: "Oracle Park",
    2529: "Sutter Health",
    2602: "GABP",
    2680: "Petco",
    2681: "Citizens Bank",
    2889: "Busch",
    3289: "Citi Field",
    3309: "Nationals Park",
    3313: "Yankee Stadium",
    4169: "loanDepot",
    4705: "Truist",
    5325: "Globe Life",
    680: "T-Mobile",
}

ROOF_CLOSED = {12, 14, 15, 32, 2392, 4169, 5325, 680}

PARK_K = {
    19: 0.86,
    2602: 1.06,
    2680: 1.05,
    3313: 1.04,
    2681: 1.04,
    2: 1.03,
    2395: 1.04,
    12: 1.03,
    15: 1.02,
    5325: 1.02,
    7: 0.96,
    17: 0.97,
}

LEAGUE_K9 = 8.5
LEAGUE_IP = 5.3


def _get(url: str) -> dict:
    req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept": "application/json"})
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.loads(resp.read().decode("utf-8"))


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
    hydrate = "probablePitcher,venue,weather,team,linescore"
    return _get(f"{STATS}/schedule?sportId=1&date={day.isoformat()}&hydrate={hydrate}")


def parse_games(board: dict) -> list[dict]:
    out = []
    for d in board.get("dates") or []:
        slate = d.get("date")
        for g in d.get("games") or []:
            aw, hm = g.get("teams", {}).get("away") or {}, g.get("teams", {}).get("home") or {}
            at, ht = aw.get("team") or {}, hm.get("team") or {}
            aab, hab = _abbr(at), _abbr(ht)
            asp = (aw.get("probablePitcher") or {}).get("fullName")
            hsp = (hm.get("probablePitcher") or {}).get("fullName")
            state = (g.get("status") or {}).get("detailedState") or ""
            abstract = (g.get("status") or {}).get("abstractGameState") or ""
            venue = g.get("venue") or {}
            weather = g.get("weather") or {}
            pk = g.get("gamePk")
            game = {
                "id": f"{slate}_{aab}_{hab}_{pk}",
                "gamePk": pk,
                "when": _when(g.get("gameDate") or "", state),
                "away": aab,
                "home": hab,
                "park": _park(venue),
                "venue": venue.get("name"),
                "away_sp": asp or "TBD",
                "home_sp": hsp or "TBD",
                "away_sp_id": (aw.get("probablePitcher") or {}).get("id"),
                "home_sp_id": (hm.get("probablePitcher") or {}).get("id"),
                "state": state,
                "abstract": abstract,
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


def _ip_to_float(raw) -> float:
    if raw is None or raw == "":
        return 0.0
    s = str(raw)
    if "." in s:
        whole, frac = s.split(".", 1)
        return int(whole or 0) + int(frac or 0) / 3.0
    return float(s)


def pitcher_season(pid: int, season: int) -> dict:
    if not pid:
        return {}
    try:
        data = _get(f"{STATS}/people/{pid}/stats?stats=season&group=pitching&season={season}")
    except Exception:
        return {}
    splits = ((data.get("stats") or [{}])[0].get("splits") or [])
    if not splits:
        return {}
    return splits[0].get("stat") or {}


def project_start(stat: dict, venue_id: int | None) -> tuple[float, float]:
    k9 = float(stat.get("strikeoutsPer9Inn") or LEAGUE_K9)
    gs = float(stat.get("gamesStarted") or 0)
    ip = _ip_to_float(stat.get("inningsPitched"))
    ip_gs = ip / gs if gs >= 3 else LEAGUE_IP
    ip_gs = max(4.0, min(6.4, ip_gs))
    park = PARK_K.get(int(venue_id or 0), 1.0)
    proj_k = round(k9 / 9.0 * ip_gs * park, 1)
    proj_outs = round(ip_gs * 3.0, 1)
    return proj_k, proj_outs


def load_json(path: Path, default):
    if not path.exists():
        return default
    return json.loads(path.read_text())


def line_for(lines: dict, day: str, player: str, market: str, proj: float) -> float:
    row = ((lines.get(day) or {}).get(player) or {})
    if market in row and row[market] is not None:
        return float(row[market])
    return half_line(proj)


def seed_props(games: list[dict], season: int, day: str, lines: dict, venue_ids: dict) -> list[dict]:
    props = []
    cache: dict[int, dict] = {}
    for g in games:
        vid = venue_ids.get(g["id"])
        for side, opp, name, pid in (
            ("away", g["home"], g.get("away_sp"), g.get("away_sp_id")),
            ("home", g["away"], g.get("home_sp"), g.get("home_sp_id")),
        ):
            if not name or name == "TBD":
                continue
            if pid and pid not in cache:
                cache[int(pid)] = pitcher_season(int(pid), season)
            stat = cache.get(int(pid) if pid else 0) or {}
            proj_k, proj_outs = project_start(stat, vid)
            gs = float(stat.get("gamesStarted") or 0)
            thin = gs < 3
            for market, label, proj, sigma_key in (
                ("k", "Strikeouts", proj_k, "k"),
                ("outs", "Outs", proj_outs, "outs"),
            ):
                line = line_for(lines, day, name, market, proj)
                sigma = SIGMA[sigma_key]
                note = "SEED_PRIOR auto"
                if thin:
                    note = "Thin sample. Confirm start."
                if "DELAY" in str(g.get("when") or ""):
                    note = "Delay. Only if he starts."
                if vid in PARK_K and PARK_K[vid] <= 0.9 and market == "k":
                    note = "Park kills Ks."
                po = p_over(proj, line, market, sigma)
                props.append(
                    {
                        "id": f"{day}_{g[side]}_{market}_{_slug(name)}".lower(),
                        "game_id": g["id"],
                        "when": g["when"],
                        "player": name,
                        "team": g[side],
                        "opp": opp,
                        "pos": "SP",
                        "market": market,
                        "market_label": label,
                        "line": line,
                        "proj": proj,
                        "sigma": sigma,
                        "p_over": None if po is None else round(po, 2),
                        "edge": round(proj - line, 1),
                        "play": play(proj, line, market),
                        "units": 0,
                        "note": note,
                    }
                )
    return props


def _slug(name: str) -> str:
    return "".join(ch.lower() if ch.isalnum() else "" for ch in name.split()[-1])


def looks_for(game: dict, props: list[dict]) -> list[dict]:
    rows = [p for p in props if p["game_id"] == game["id"] and p["market"] == "k"]
    rows.sort(key=lambda p: abs(float(p.get("edge") or 0)), reverse=True)
    out = []
    for p in rows[:2]:
        out.append(
            {
                "side": "home" if p["team"] == game["home"] else "away",
                "player": p["player"],
                "pos": "SP",
                "note": f"K {p['line']} \u00b7 {p['play']}",
                "score": int(round(float(p.get("p_over") or 0.5) * 100)),
            }
        )
    return out


def merge_props(old: list[dict], fresh: list[dict], keep_manual: bool) -> list[dict]:
    if not keep_manual:
        return fresh
    prev = {p["id"]: p for p in old if p.get("id")}
    out = []
    seen = set()
    for p in fresh:
        if p["id"] in prev:
            oldp = prev[p["id"]]
            for k in ("line", "proj", "play", "units", "note", "sigma"):
                if oldp.get(k) not in (None, "", "SEED_PRIOR auto"):
                    p[k] = oldp[k]
            if oldp.get("line") is not None and oldp.get("proj") is not None:
                p["edge"] = round(float(p["proj"]) - float(p["line"]), 1)
                po = p_over(
                    float(p["proj"]),
                    float(p["line"]),
                    p["market"],
                    float(p.get("sigma") or SIGMA.get(p["market"], 1)),
                )
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


def fetch_box(game_pk: int) -> dict:
    return _get(f"{STATS}/game/{game_pk}/boxscore")


def _find_pitcher(box: dict, name: str) -> dict | None:
    want = name.lower()
    last = name.split()[-1].lower()
    for side in ("away", "home"):
        players = (box.get("teams") or {}).get(side, {}).get("players") or {}
        for row in players.values():
            person = row.get("person") or {}
            full = (person.get("fullName") or "").lower()
            if full == want or full.endswith(last):
                pitching = (row.get("stats") or {}).get("pitching") or {}
                if pitching:
                    return pitching
    return None


def grade_props(games: list[dict], props: list[dict]) -> list[dict]:
    boxes: dict[int, dict] = {}
    for g in games:
        pk = g.get("gamePk")
        if not pk:
            continue
        if "FINAL" not in str(g.get("when") or "") and (g.get("abstract") or "") != "Final":
            continue
        try:
            boxes[int(pk)] = fetch_box(int(pk))
        except Exception as exc:
            print(f"box miss {pk}: {exc}", file=sys.stderr)
    by_game = {g["id"]: g for g in games}
    for p in props:
        g = by_game.get(p.get("game_id") or "")
        if not g:
            continue
        box = boxes.get(int(g["gamePk"])) if g.get("gamePk") else None
        if not box:
            continue
        row = _find_pitcher(box, p["player"])
        if not row:
            continue
        if p["market"] == "k":
            actual = row.get("strikeOuts")
        elif p["market"] == "outs":
            actual = row.get("outs")
        else:
            continue
        if actual is None:
            continue
        p["actual"] = actual
        line = float(p.get("line") or 0)
        if actual > line:
            p["result"] = "OVER"
        elif actual < line:
            p["result"] = "UNDER"
        else:
            p["result"] = "PUSH"
    return props


def status_for(phase: str, games: list[dict], props: list[dict]) -> str:
    if not games:
        return "SEED_PRIOR"
    named = sum(
        1
        for g in games
        if g.get("away_sp") not in (None, "TBD") and g.get("home_sp") not in (None, "TBD")
    )
    finals = sum(1 for g in games if "FINAL" in str(g.get("when") or "") or g.get("abstract") == "Final")
    graded = sum(1 for p in props if p.get("actual") is not None)
    if phase == "grade" and finals == len(games) and graded:
        return "GRADED"
    if phase == "lock":
        return "LOCKED"
    if phase == "noon" and named >= max(1, int(0.75 * len(games))):
        return "LIVE"
    if phase == "grade" and graded:
        return "LOCKED"
    return "SEED_PRIOR"


def venue_ids_from_board(board: dict, games: list[dict]) -> dict:
    pks = {}
    for d in board.get("dates") or []:
        slate = d.get("date")
        for g in d.get("games") or []:
            aw = ((g.get("teams") or {}).get("away") or {}).get("team") or {}
            hm = ((g.get("teams") or {}).get("home") or {}).get("team") or {}
            gid = f"{slate}_{_abbr(aw)}_{_abbr(hm)}_{g.get('gamePk')}"
            pks[gid] = (g.get("venue") or {}).get("id")
    return pks


def build(day: date, phase: str, fresh: bool) -> dict:
    board = fetch_schedule(day)
    games = parse_games(board)
    if not games:
        raise SystemExit(f"empty slate {day.isoformat()}")
    season = day.year
    lines = load_json(LINES, {})
    vids = venue_ids_from_board(board, games)
    new_props = seed_props(games, season, day.isoformat(), lines, vids)
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
    disclaimer = (
        f"{day.isoformat()} slate from MLB Stats API. {named}/{len(games)} starters named. "
        f"Props are {st} — seed K/outs from season K/9 \u00d7 expected IP \u00d7 park. Not tickets."
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
        "games": games,
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
    text = json.dumps(card, indent=2) + "\n"
    print(
        f"date={card['date']} phase={phase} status={card['status']} "
        f"games={len(card['games'])} props={len(card['props'])}"
    )
    if args.dry_run:
        return 0
    FEED.parent.mkdir(parents=True, exist_ok=True)
    FEED.write_text(text)
    print(f"wrote {FEED}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
