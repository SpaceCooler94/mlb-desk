"""Research stack for MLB desk.

Intended jobs, not vanity imports:

- pandas / numpy  — season boards + game logs as frames; form windows
- pybaseball      — FanGraphs/Savant Barrel%, EV, HardHit%, K%, CSW%
- xgboost         — residual model on graded history (actual - rate proj)
- scikit-learn    — isotonic calibration of p_over; GBDT fallback

Every call degrades to the rate model when a library or scrape is missing.
"""

from __future__ import annotations

import json
import math
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
MODELS = ROOT / "models"
HISTORY = ROOT / "feed" / "history.jsonl"

LEAGUE_BARREL = 8.0
LEAGUE_HARDHIT = 38.5
LEAGUE_K_PCT = 22.5
LEAGUE_CSW = 28.0
LEAGUE_EV = 88.5


def _try_import():
    flags = {"pandas": False, "numpy": False, "sklearn": False, "xgboost": False, "pybaseball": False}
    mods = {}
    try:
        import pandas as pd
        flags["pandas"] = True
        mods["pd"] = pd
    except Exception:
        pd = None
    try:
        import numpy as np
        flags["numpy"] = True
        mods["np"] = np
    except Exception:
        np = None
    try:
        from sklearn.ensemble import GradientBoostingRegressor
        from sklearn.isotonic import IsotonicRegression
        flags["sklearn"] = True
        mods["IsotonicRegression"] = IsotonicRegression
        mods["GradientBoostingRegressor"] = GradientBoostingRegressor
    except Exception:
        pass
    try:
        import xgboost as xgb
        flags["xgboost"] = True
        mods["xgb"] = xgb
    except Exception:
        pass
    try:
        import pybaseball
        flags["pybaseball"] = True
        mods["pybaseball"] = pybaseball
    except Exception:
        pass
    return flags, mods


FLAGS, MODS = _try_import()


def available():
    return dict(FLAGS)


def _clip(x, lo, hi):
    return max(lo, min(hi, x))


def _pct(v):
    if v is None:
        return None
    try:
        x = float(v)
    except (TypeError, ValueError):
        return None
    if math.isnan(x):
        return None
    if x <= 1.0:
        x *= 100.0
    return x


def _norm_name(name):
    return "".join(ch.lower() for ch in name if ch.isalnum())


@dataclass
class Adjustment:
    proj: float
    note: str
    engine: str
    savant: dict


class Stack:
    def __init__(self, season, hitters, pitchers, models, cal):
        self.season = season
        self.hitters = hitters
        self.pitchers = pitchers
        self.models = models
        self.cal = cal

    @classmethod
    def load(cls, season, refresh=False):
        DATA.mkdir(parents=True, exist_ok=True)
        MODELS.mkdir(parents=True, exist_ok=True)
        hitters = _load_json(DATA / f"savant_hitters_{season}.json", {})
        pitchers = _load_json(DATA / f"savant_pitchers_{season}.json", {})
        if refresh or not hitters or not pitchers:
            pulled_h, pulled_p = pull_savant(season)
            if pulled_h:
                hitters = pulled_h
            if pulled_p:
                pitchers = pulled_p
        models = {}
        for market in ("k", "outs", "hits", "tb", "hr"):
            path = MODELS / f"{market}_xgb.json"
            if path.exists():
                models[market] = path
        cal = _load_json(MODELS / "calibrate.json", {})
        return cls(season, hitters, pitchers, models, cal)

    def hitter_row(self, name):
        return self.hitters.get(_norm_name(name)) or {}

    def pitcher_row(self, name):
        return self.pitchers.get(_norm_name(name)) or {}

    def adjust_pitcher(self, name, market, base, features):
        row = self.pitcher_row(name)
        proj = float(base)
        bits = []
        savant = {}
        if row:
            k_pct = _pct(row.get("k_pct"))
            csw = _pct(row.get("csw"))
            if market == "k" and k_pct is not None:
                proj *= _clip(1.0 + 0.45 * (k_pct - LEAGUE_K_PCT) / LEAGUE_K_PCT, 0.82, 1.22)
                savant["k_pct"] = round(k_pct, 1)
                bits.append(f"FG K% {k_pct:.1f}")
            if market == "k" and csw is not None:
                proj *= _clip(1.0 + 0.20 * (csw - LEAGUE_CSW) / LEAGUE_CSW, 0.90, 1.10)
                savant["csw"] = round(csw, 1)
        proj = self._residual(market, proj, features, row)
        engine = self._engine_tag(market, bool(row))
        note = ("Savant/FG. " + " · ".join(bits)) if bits else ""
        return Adjustment(round(proj, 2), note, engine, savant)

    def adjust_hitter(self, name, market, base, features):
        row = self.hitter_row(name)
        proj = float(base)
        bits = []
        savant = {}
        if row:
            barrel = _pct(row.get("barrel"))
            hard = _pct(row.get("hardhit"))
            ev = row.get("ev")
            try:
                ev = float(ev) if ev is not None else None
            except (TypeError, ValueError):
                ev = None
            if market == "hr" and barrel is not None:
                proj *= _clip(1.0 + 0.85 * (barrel - LEAGUE_BARREL) / LEAGUE_BARREL, 0.72, 1.40)
                savant["barrel"] = round(barrel, 1)
                bits.append(f"Barrel {barrel:.1f}%")
            if market in ("hits", "tb") and hard is not None:
                proj *= _clip(1.0 + 0.25 * (hard - LEAGUE_HARDHIT) / LEAGUE_HARDHIT, 0.88, 1.14)
                savant["hardhit"] = round(hard, 1)
            if market == "tb" and ev is not None:
                proj *= _clip(1.0 + 0.15 * (ev - LEAGUE_EV) / 6.0, 0.90, 1.12)
                savant["ev"] = round(ev, 1)
        proj = self._residual(market, proj, features, row)
        engine = self._engine_tag(market, bool(row))
        note = ("Savant/FG. " + " · ".join(bits)) if bits else ""
        return Adjustment(round(proj, 3 if market == "hr" else 2), note, engine, savant)

    def calibrate(self, market, p):
        if p is None:
            return None
        spec = self.cal.get(market) or {}
        xs = spec.get("x") or []
        ys = spec.get("y") or []
        if len(xs) < 3 or len(xs) != len(ys):
            return p
        return round(_piecewise(xs, ys, p), 2)

    def _residual(self, market, proj, features, row):
        vec = _feature_vec(market, proj, features, row)
        path = self.models.get(market)
        if path and FLAGS["xgboost"]:
            try:
                xgb = MODS["xgb"]
                booster = xgb.Booster()
                booster.load_model(str(path))
                import numpy as np
                d = xgb.DMatrix(np.array([vec], dtype=float))
                resid = float(booster.predict(d)[0])
                cap = 0.20 if market == "hr" else 1.6
                return proj + _clip(resid, -cap, cap)
            except Exception as exc:
                print(f"xgb miss {market}: {exc}", file=sys.stderr)
        if path is None and FLAGS["sklearn"] and (MODELS / f"{market}_gbrt.joblib").exists():
            try:
                import joblib
                model = joblib.load(MODELS / f"{market}_gbrt.joblib")
                resid = float(model.predict([vec])[0])
                cap = 0.20 if market == "hr" else 1.6
                return proj + _clip(resid, -cap, cap)
            except Exception as exc:
                print(f"gbrt miss {market}: {exc}", file=sys.stderr)
        return proj

    def _engine_tag(self, market, savant):
        parts = ["rate"]
        if savant:
            parts.append("savant")
        if market in self.models:
            parts.append("xgb")
        elif (MODELS / f"{market}_gbrt.joblib").exists():
            parts.append("gbrt")
        if market in self.cal:
            parts.append("cal")
        return "+".join(parts)


def _feature_vec(market, proj, features, row):
    barrel = _pct(row.get("barrel")) or 0.0
    hard = _pct(row.get("hardhit")) or 0.0
    k_pct = _pct(row.get("k_pct")) or 0.0
    csw = _pct(row.get("csw")) or 0.0
    return [
        float(proj),
        float(features.get("park") or 1.0),
        float(features.get("slot") or 5) / 9.0,
        float(features.get("form_n") or 0) / 5.0,
        1.0 if features.get("thin") else 0.0,
        float(features.get("opp_era") or 4.15) / 4.15,
        barrel / 10.0,
        hard / 40.0,
        k_pct / 25.0,
        csw / 30.0,
    ]


def _piecewise(xs, ys, p):
    if p <= xs[0]:
        return ys[0]
    if p >= xs[-1]:
        return ys[-1]
    for i in range(1, len(xs)):
        if p <= xs[i]:
            t = (p - xs[i - 1]) / (xs[i] - xs[i - 1] or 1e-9)
            return ys[i - 1] + t * (ys[i] - ys[i - 1])
    return p


def _load_json(path, default):
    if not path.exists():
        return default
    try:
        return json.loads(path.read_text())
    except Exception:
        return default


def pull_savant(season):
    if not FLAGS["pybaseball"] or not FLAGS["pandas"]:
        return {}, {}
    pb = MODS["pybaseball"]
    hitters, pitchers = {}, {}
    try:
        bat = pb.batting_stats(season, qual=20)
        hitters = _index_hitters(bat)
        (DATA / f"savant_hitters_{season}.json").write_text(json.dumps(hitters, indent=2) + "\n")
        print(f"savant hitters {len(hitters)}", file=sys.stderr)
    except Exception as exc:
        print(f"pybaseball batting_stats miss: {exc}", file=sys.stderr)
    try:
        pit = pb.pitching_stats(season, qual=10)
        pitchers = _index_pitchers(pit)
        (DATA / f"savant_pitchers_{season}.json").write_text(json.dumps(pitchers, indent=2) + "\n")
        print(f"savant pitchers {len(pitchers)}", file=sys.stderr)
    except Exception as exc:
        print(f"pybaseball pitching_stats miss: {exc}", file=sys.stderr)
    return hitters, pitchers


def _col(df, *names):
    cols = {str(c).lower(): c for c in df.columns}
    for n in names:
        if n.lower() in cols:
            return cols[n.lower()]
    return None


def _index_hitters(df):
    name_c = _col(df, "Name")
    if name_c is None:
        return {}
    barrel_c = _col(df, "Barrel%")
    hard_c = _col(df, "HardHit%")
    ev_c = _col(df, "EV")
    out = {}
    for _, r in df.iterrows():
        name = str(r[name_c])
        out[_norm_name(name)] = {"name": name, "barrel": _cell(r, barrel_c), "hardhit": _cell(r, hard_c), "ev": _cell(r, ev_c)}
    return out


def _index_pitchers(df):
    name_c = _col(df, "Name")
    if name_c is None:
        return {}
    k_c = _col(df, "K%", "K %")
    csw_c = _col(df, "CSW%")
    ev_c = _col(df, "EV")
    out = {}
    for _, r in df.iterrows():
        name = str(r[name_c])
        out[_norm_name(name)] = {"name": name, "k_pct": _cell(r, k_c), "csw": _cell(r, csw_c), "ev": _cell(r, ev_c)}
    return out


def _cell(row, col):
    if col is None:
        return None
    v = row[col]
    try:
        if v is None or (isinstance(v, float) and math.isnan(v)):
            return None
        return float(v)
    except (TypeError, ValueError):
        return None


def boards_frame(board, group):
    if not FLAGS["pandas"]:
        return None
    pd = MODS["pd"]
    rows = []
    for pid, stat in (board or {}).items():
        row = {"pid": int(pid), "group": group}
        row.update(stat)
        rows.append(row)
    return pd.DataFrame(rows)


def append_history(rows):
    if not rows:
        return 0
    HISTORY.parent.mkdir(parents=True, exist_ok=True)
    with HISTORY.open("a") as fh:
        for row in rows:
            fh.write(json.dumps(row, separators=(",", ":")) + "\n")
    return len(rows)


def load_history():
    if not HISTORY.exists():
        return []
    out = []
    for line in HISTORY.read_text().splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            out.append(json.loads(line))
        except json.JSONDecodeError:
            continue
    return out


def train_from_history(min_rows=40):
    rows = load_history()
    report = {"n": len(rows), "markets": {}}
    if not rows or not FLAGS["numpy"]:
        return report
    np = MODS["np"]
    by = {}
    for r in rows:
        if r.get("actual") is None or r.get("proj") is None or not r.get("market"):
            continue
        by.setdefault(r["market"], []).append(r)
    MODELS.mkdir(parents=True, exist_ok=True)
    cal = _load_json(MODELS / "calibrate.json", {})
    for market, items in by.items():
        report["markets"][market] = {"n": len(items), "model": None}
        if len(items) < min_rows:
            continue
        X, y, p_hat, y_bin = [], [], [], []
        for r in items:
            feat = r.get("features") or {}
            sav = r.get("savant") or {}
            row = {"barrel": sav.get("barrel"), "hardhit": sav.get("hardhit"), "k_pct": sav.get("k_pct"), "csw": sav.get("csw")}
            X.append(_feature_vec(market, float(r["proj"]), feat, row))
            y.append(float(r["actual"]) - float(r["proj"]))
            if r.get("p_over") is not None and r.get("line") is not None:
                p_hat.append(float(r["p_over"]))
                y_bin.append(1.0 if float(r["actual"]) > float(r["line"]) else 0.0)
        Xn = np.array(X, dtype=float)
        yn = np.array(y, dtype=float)
        if FLAGS["xgboost"]:
            xgb = MODS["xgb"]
            dtrain = xgb.DMatrix(Xn, label=yn)
            params = {"max_depth": 3, "eta": 0.08, "objective": "reg:squarederror", "subsample": 0.8, "min_child_weight": 4}
            booster = xgb.train(params, dtrain, num_boost_round=80)
            dest = MODELS / f"{market}_xgb.json"
            booster.save_model(str(dest))
            report["markets"][market]["model"] = str(dest)
        elif FLAGS["sklearn"]:
            import joblib
            model = MODS["GradientBoostingRegressor"](max_depth=2, n_estimators=60, learning_rate=0.08)
            model.fit(Xn, yn)
            dest = MODELS / f"{market}_gbrt.joblib"
            joblib.dump(model, dest)
            report["markets"][market]["model"] = str(dest)
        if FLAGS["sklearn"] and len(p_hat) >= min_rows:
            iso = MODS["IsotonicRegression"](out_of_bounds="clip")
            iso.fit(p_hat, y_bin)
            grid = [i / 20 for i in range(1, 20)]
            cal[market] = {"x": grid, "y": [round(float(v), 4) for v in iso.predict(grid)], "n": len(p_hat)}
            report["markets"][market]["cal_n"] = len(p_hat)
    if cal:
        (MODELS / "calibrate.json").write_text(json.dumps(cal, indent=2) + "\n")
        (MODELS / "trained_at.json").write_text(json.dumps({"at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"), "report": report}, indent=2) + "\n")
    return report
