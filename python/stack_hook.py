"""Post-process rate props with the research stack. Soft-fail."""

from __future__ import annotations

import sys

from props import SIGMA, p_over, play


def apply_stack(props, season, refresh=False):
    try:
        from stack import Stack
    except Exception as exc:
        print(f"stack import miss: {exc}", file=sys.stderr)
        return props
    try:
        st = Stack.load(season, refresh=refresh)
    except Exception as exc:
        print(f"stack load miss: {exc}", file=sys.stderr)
        return props
    for p in props:
        market = p.get("market")
        try:
            base = float(p.get("proj") or 0)
        except (TypeError, ValueError):
            continue
        slot = 5
        pos = str(p.get("pos") or "")
        if pos[:1].isdigit():
            slot = int(pos[0])
        feats = p.get("features") or {"park": 1.0, "slot": slot, "form_n": 0, "thin": False, "opp_era": 4.15}
        name = p.get("player") or ""
        try:
            if market == "k":
                adj = st.adjust_pitcher(name, market, base, feats)
            elif market in ("hits", "tb", "hr"):
                adj = st.adjust_hitter(name, market, base, feats)
            else:
                p.setdefault("engine", "rate")
                continue
        except Exception as exc:
            print(f"stack adj miss {name} {market}: {exc}", file=sys.stderr)
            p.setdefault("engine", "rate")
            continue
        p["proj"] = adj.proj if market == "hr" else round(float(adj.proj), 1)
        p["engine"] = adj.engine
        p["savant"] = adj.savant
        p["features"] = feats
        if adj.note and adj.note not in str(p.get("note") or ""):
            p["note"] = f"{adj.note} {p.get('note') or ''}".strip()
        line = p.get("line")
        if line is not None:
            po = p_over(float(p["proj"]), float(line), market, float(p.get("sigma") or SIGMA.get(market, 1)))
            po = st.calibrate(market, po)
            p["p_over"] = None if po is None else round(po, 2)
            p["edge"] = round(float(p["proj"]) - float(line), 2 if market == "hr" else 1)
            p["play"] = play(float(p["proj"]), float(line), market)
    return props


def record_history(day_iso, props):
    rows = []
    for p in props:
        if p.get("actual") is None:
            continue
        rows.append({
            "date": day_iso,
            "player": p.get("player"),
            "market": p.get("market"),
            "line": p.get("line"),
            "proj": p.get("proj"),
            "p_over": p.get("p_over"),
            "actual": p.get("actual"),
            "features": p.get("features") or {},
            "savant": p.get("savant") or {},
        })
    if not rows:
        return 0
    try:
        from stack import append_history, load_history, train_from_history
        n = append_history(rows)
        if len(load_history()) >= 40:
            train_from_history(min_rows=40)
        return n
    except Exception as exc:
        print(f"history miss: {exc}", file=sys.stderr)
        return 0


def stack_flags():
    try:
        from stack import available
        return available()
    except Exception:
        return {}
