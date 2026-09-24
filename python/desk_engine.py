"""Lineups, season boards, and prop seeding. Rank-1 MLB Stats API only."""

from __future__ import annotations

import json
import sys
import time
import urllib.error
import urllib.request

from props import LEAGUE, PA_BY_SLOT, SIGMA, half_line, p_over, play

STATS = "https://statsapi.mlb.com/api/v1"
UA = "mlb-desk/1.1 (+https://github.com/SpaceCooler94/mlb-desk)"

PARK_HIT = {
    19: 1.18, 3: 1.06, 3313: 1.04, 2602: 1.04, 4: 1.03, 2681: 1.03,
    2680: 0.90, 2395: 0.92, 31: 0.94, 22: 0.95, 680: 0.96,
}
PARK_HR = {
    19: 1.22, 3313: 1.16, 2602: 1.18, 2: 1.12, 2681: 1.10, 4: 1.08, 3: 1.04,
    2680: 0.82, 2395: 0.78, 31: 0.86, 22: 0.90, 680: 0.92, 7: 0.88,
}
PARK_K = {
    19: 0.86, 2602: 1.06, 2680: 1.05, 3313: 1.04, 2681: 1.04, 2: 1.03,
    2395: 1.04, 12: 1.03, 15: 1.02, 5325: 1.02, 7: 0.96, 17: 0.97,
}


def get_json(url: str, retries: int = 3) -> dict:
    req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept": "application/json"})
    last = None
    for i in range(retries):
        try:
            with urllib.request.urlopen(req, timeout=30) as resp:
                return json.loads(resp.read().decode("utf-8"))
        except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as exc:
            last = exc
            time.sleep(0.4 * (i + 1))
    raise RuntimeError(f"GET fail {url}: {last}")


def slot_of(raw):
    if raw is None or raw == "":
        return None
    try:
        n = int(raw)
    except (TypeError, ValueError):
        return None
    if n >= 100:
        n = n // 100
    return n if 1 <= n <= 9 else None


def lineup_side(players):
    rows = []
    for i, p in enumerate(players or [], start=1):
        person = p.get("person") or p
        slot = slot_of(p.get("battingOrder") or p.get("order") or person.get("battingOrder"))
        if slot is None:
            slot = i if i <= 9 else None
        pos = ((p.get("position") or {}).get("abbreviation") or (p.get("primaryPosition") or {}).get("abbreviation") or p.get("pos"))
        name = person.get("fullName") or p.get("fullName")
        pid = person.get("id") or p.get("id")
        if not name or not pid or not slot:
            continue
        rows.append({"id": int(pid), "name": name, "slot": slot, "pos": pos or "DH"})
    rows.sort(key=lambda r: r["slot"])
    return rows


def parse_lineups(game):
    lu = game.get("lineups") or {}
    home = lineup_side(lu.get("homePlayers") or lu.get("home") or [])
    away = lineup_side(lu.get("awayPlayers") or lu.get("away") or [])
    tag = "CONFIRMED" if home and away else "PROBABLE" if home or away else "UNKNOWN"
    return {"home": home, "away": away, "tag": tag}


def ip_to_float(raw):
    if raw is None or raw == "":
        return 0.0
    s = str(raw)
    if "." in s:
        whole, frac = s.split(".", 1)
        return int(whole or 0) + int(frac or 0) / 3.0
    return float(s)


def num(stat, *keys, default=0.0):
    for k in keys:
        v = stat.get(k)
        if v not in (None, "", "-"):
            try:
                return float(v)
            except (TypeError, ValueError):
                continue
    return default


def person_stats(pid, season, group, stat_type):
    if not pid:
        return {}
    url = f"{STATS}/people/{pid}/stats?stats={stat_type}&group={group}&season={season}"
    try:
        data = get_json(url)
    except Exception:
        return {}
    splits = ((data.get("stats") or [{}])[0].get("splits") or [])
    if not splits:
        return {}
    if stat_type == "gameLog":
        return {"logs": [s.get("stat") or {} for s in splits[:15]]}
    return splits[0].get("stat") or {}


def load_season_board(season, group):
    url = f"{STATS}/stats?stats=season&group={group}&season={season}&sportId=1&playerPool=all&limit=800"
    try:
        data = get_json(url)
    except Exception as exc:
        print(f"season board miss {group}: {exc}", file=sys.stderr)
        return {}
    out = {}
    for s in ((data.get("stats") or [{}])[0].get("splits") or []):
        pid = ((s.get("player") or {}).get("id"))
        if pid:
            out[int(pid)] = s.get("stat") or {}
    return out


def blend_rate(season_val, recent_val, n, floor_n=3):
    if recent_val is None or n < floor_n:
        return season_val
    w = min(0.45, 0.12 * n)
    return (1 - w) * season_val + w * recent_val


def pitcher_profile(pid, season, cache, board=None):
    if not pid:
        return {}
    if pid in cache:
        return cache[pid]
    season_s = (board or {}).get(int(pid)) or person_stats(pid, season, "pitching", "season")
    logs = person_stats(pid, season, "pitching", "gameLog").get("logs") or []
    starts = [x for x in logs if num(x, "gamesStarted", "gamesPitched") >= 1][:5]
    k9 = num(season_s, "strikeoutsPer9Inn", default=LEAGUE["k9"])
    gs = num(season_s, "gamesStarted")
    ip = ip_to_float(season_s.get("inningsPitched"))
    ip_gs = ip / gs if gs >= 3 else LEAGUE["ip_gs"]
    if starts:
        rec_ip = sum(ip_to_float(s.get("inningsPitched")) for s in starts)
        rec_k = sum(num(s, "strikeOuts") for s in starts)
        rec_k9 = (rec_k / rec_ip * 9.0) if rec_ip >= 8 else None
        rec_ip_gs = rec_ip / len(starts)
        k9 = blend_rate(k9, rec_k9, len(starts))
        ip_gs = blend_rate(ip_gs, rec_ip_gs, len(starts))
    prof = {"k9": k9, "ip_gs": max(4.0, min(6.4, ip_gs)), "gs": gs, "era": num(season_s, "era", default=LEAGUE["era"]), "thin": gs < 3, "form_n": len(starts)}
    cache[pid] = prof
    return prof


def hitter_profile(pid, season, cache, board=None):
    if not pid:
        return {}
    if pid in cache:
        return cache[pid]
    season_s = (board or {}).get(int(pid)) or person_stats(pid, season, "hitting", "season")
    pa = num(season_s, "plateAppearances")
    hr = num(season_s, "homeRuns")
    avg = num(season_s, "avg", default=LEAGUE["avg"])
    slg = num(season_s, "slg", default=LEAGUE["slg"])
    hr_pa = (hr / pa) if pa >= 40 else LEAGUE["hr_pa"]
    prof = {"avg": max(0.160, min(0.380, avg)), "slg": max(0.250, min(0.720, slg)), "hr_pa": max(0.005, min(0.090, hr_pa)), "pa": pa, "thin": pa < 80, "form_n": 0}
    cache[pid] = prof
    return prof


def project_start(prof, venue_id):
    k9 = float(prof.get("k9") or LEAGUE["k9"])
    ip_gs = float(prof.get("ip_gs") or LEAGUE["ip_gs"])
    park = PARK_K.get(int(venue_id or 0), 1.0)
    return round(k9 / 9.0 * ip_gs * park, 1), round(ip_gs * 3.0, 1)


def project_hitter(prof, slot, venue_id, opp_era):
    pa = PA_BY_SLOT.get(int(slot or 5), 4.1)
    env = 1.0 + 0.12 * ((opp_era - LEAGUE["era"]) / LEAGUE["era"])
    hit_pk = PARK_HIT.get(int(venue_id or 0), 1.0)
    hr_pk = PARK_HR.get(int(venue_id or 0), 1.0)
    return {
        "hits": round(pa * prof["avg"] * env * hit_pk, 2),
        "tb": round(pa * prof["slg"] * env * ((hit_pk + hr_pk) / 2.0), 2),
        "hr": round(pa * prof["hr_pa"] * env * hr_pk, 3),
        "pa": round(pa, 2),
    }


def slug(name):
    return "".join(ch.lower() if ch.isalnum() else "" for ch in name.split()[-1])


def line_for(lines, day, player, market, proj):
    row = ((lines.get(day) or {}).get(player) or {})
    if market in row and row[market] is not None:
        return float(row[market])
    if market == "hr":
        return 0.5
    return half_line(proj)


def make_prop(day, game, player, team, opp, pos, market, label, proj, line, note, sigma):
    po = p_over(proj, line, market, sigma)
    return {
        "id": f"{day}_{team}_{market}_{slug(player)}".lower(),
        "game_id": game["id"],
        "when": game["when"],
        "player": player,
        "team": team,
        "opp": opp,
        "pos": pos,
        "market": market,
        "market_label": label,
        "line": line,
        "proj": proj if market == "hr" else round(float(proj), 1),
        "sigma": sigma,
        "p_over": None if po is None else round(po, 2),
        "edge": round(float(proj) - float(line), 2 if market == "hr" else 1),
        "play": play(proj, line, market),
        "units": 0,
        "note": note,
    }


def seed_all(games, season, day, lines):
    p_board = load_season_board(season, "pitching")
    h_board = load_season_board(season, "hitting")
    p_cache, h_cache, props = {}, {}, []
    for g in games:
        vid = g.get("venue_id")
        for side, opp, name, pid in (("away", g["home"], g.get("away_sp"), g.get("away_sp_id")), ("home", g["away"], g.get("home_sp"), g.get("home_sp_id"))):
            if not name or name == "TBD":
                continue
            prof = pitcher_profile(int(pid) if pid else 0, season, p_cache, p_board)
            proj_k, proj_outs = project_start(prof, vid)
            note = "SEED_PRIOR season K/9 x IP x park"
            if prof.get("form_n"):
                note = f"Season + last {prof['form_n']} GS."
            if prof.get("thin"):
                note = "Thin sample. Confirm start."
            if "DELAY" in str(g.get("when") or ""):
                note = "Delay. Only if he starts."
            if vid in PARK_K and PARK_K[vid] <= 0.9:
                note = "Park kills Ks. " + note
            for market, label, proj in (("k", "Strikeouts", proj_k), ("outs", "Outs", proj_outs)):
                props.append(make_prop(day, g, name, g[side], opp, "SP", market, label, proj, line_for(lines, day, name, market, proj), note, SIGMA[market]))
        for side, opp_side, opp_sp_id in (("away", "home", g.get("home_sp_id")), ("home", "away", g.get("away_sp_id"))):
            card = g.get(f"{side}_lineup") or []
            if not card:
                continue
            opp_era = float(pitcher_profile(int(opp_sp_id) if opp_sp_id else 0, season, p_cache, p_board).get("era") or LEAGUE["era"])
            tag = g.get("lineup_tag") or "UNKNOWN"
            for batter in card:
                if not batter.get("slot") or batter["slot"] > 6:
                    continue
                prof = hitter_profile(int(batter["id"]), season, h_cache, h_board)
                proj = project_hitter(prof, batter["slot"], vid, opp_era)
                note = f"{tag} lineup slot {batter['slot']}. Season rates x park x SP ERA."
                if prof.get("thin"):
                    note = "Thin PA. " + note
                if vid in PARK_HR and PARK_HR[vid] >= 1.15:
                    note = "HR park. " + note
                name = batter["name"]
                pos = f"{batter['slot']} {batter.get('pos') or ''}".strip()
                for market, label, raw in (("hits", "Hits", proj["hits"]), ("tb", "Total bases", proj["tb"]), ("hr", "Home run", proj["hr"])):
                    props.append(make_prop(day, g, name, g[side], g[opp_side], pos, market, label, raw, line_for(lines, day, name, market, raw), note, SIGMA[market]))
    return props


def looks_for(game, props):
    rows = [p for p in props if p["game_id"] == game["id"] and p["market"] in ("k", "hits", "hr", "tb")]
    rows.sort(key=lambda p: abs(float(p.get("edge") or 0)), reverse=True)
    out, seen = [], set()
    for p in rows:
        key = (p["player"], p["market"])
        if key in seen:
            continue
        seen.add(key)
        out.append({"side": "home" if p["team"] == game["home"] else "away", "player": p["player"], "pos": p.get("pos") or "", "note": f"{p['market_label']} {p['line']} · {p['play']}", "score": int(round(float(p.get("p_over") or 0.5) * 100))})
        if len(out) >= 8:
            break
    return out


def find_player_stats(box, name, group):
    want = name.lower()
    last = name.split()[-1].lower()
    for side in ("away", "home"):
        players = (box.get("teams") or {}).get(side, {}).get("players") or {}
        for row in players.values():
            full = ((row.get("person") or {}).get("fullName") or "").lower()
            if full == want or full.endswith(last):
                stats = (row.get("stats") or {}).get(group) or {}
                if stats:
                    return stats
    return None


FIELD = {
    "k": ("pitching", "strikeOuts"),
    "outs": ("pitching", "outs"),
    "hits": ("batting", "hits"),
    "tb": ("batting", "totalBases"),
    "hr": ("batting", "homeRuns"),
    "rbi": ("batting", "rbi"),
    "runs": ("batting", "runs"),
    "sb": ("batting", "stolenBases"),
}


def grade_props(games, props):
    boxes = {}
    for g in games:
        pk = g.get("gamePk")
        if not pk:
            continue
        if "FINAL" not in str(g.get("when") or "") and (g.get("abstract") or "") != "Final":
            continue
        try:
            boxes[int(pk)] = get_json(f"{STATS}/game/{pk}/boxscore")
        except Exception as exc:
            print(f"box miss {pk}: {exc}", file=sys.stderr)
    by_game = {g["id"]: g for g in games}
    for p in props:
        g = by_game.get(p.get("game_id") or "")
        if not g or not g.get("gamePk") or p["market"] not in FIELD:
            continue
        box = boxes.get(int(g["gamePk"]))
        if not box:
            continue
        group, key = FIELD[p["market"]]
        row = find_player_stats(box, p["player"], group)
        if not row or row.get(key) is None:
            continue
        actual = row.get(key)
        p["actual"] = actual
        line = float(p.get("line") or 0)
        p["result"] = "OVER" if actual > line else "UNDER" if actual < line else "PUSH"
    return props
