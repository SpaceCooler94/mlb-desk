"""Seed MLB prop math. Volume x opponent x park. Not a live book."""

from math import erf, floor, sqrt

SIGMA = {
    "k": 1.8,
    "outs": 3.5,
    "hits": 0.7,
    "tb": 1.1,
    "hrr": 1.2,
    "rbi": 0.9,
    "runs": 0.7,
}


def p_over(proj, line, market, sigma=None):
    s = sigma or SIGMA.get(market, 1.0)
    if s <= 0:
        return None
    z = (proj - line) / s
    return 0.5 * (1 + erf(z / sqrt(2)))


def play(proj, line, market, juice=-110):
    edge = proj - line
    s = SIGMA.get(market, 1.0)
    if market == "hr":
        return "WATCH" if proj >= 0.18 else "PASS"
    if abs(edge) < 0.45 * s:
        return "PASS"
    if juice <= -130 and abs(edge) < 0.7 * s:
        return "PASS"
    return "WATCH"


def half_line(x: float) -> float:
    """Nearest n.5. Ties (exactly n.0) go down to (n-0.5)."""
    lo = float(floor(x - 0.5)) + 0.5
    hi = lo + 1.0
    return lo if abs(x - lo) <= abs(x - hi) else hi
