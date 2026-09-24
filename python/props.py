"""Seed MLB prop math. Volume x opponent x park. Not a live book."""

from math import erf, floor, sqrt

SIGMA = {
    "k": 1.8,
    "outs": 3.5,
    "hits": 0.75,
    "tb": 1.15,
    "hr": 0.35,
    "hrr": 1.2,
    "rbi": 0.95,
    "runs": 0.75,
    "sb": 0.4,
}

# Expected plate appearances by batting-order slot (league average start).
PA_BY_SLOT = {
    1: 4.60,
    2: 4.48,
    3: 4.36,
    4: 4.24,
    5: 4.12,
    6: 4.00,
    7: 3.88,
    8: 3.76,
    9: 3.64,
}

LEAGUE = {
    "avg": 0.245,
    "slg": 0.400,
    "hr_pa": 0.031,
    "k9": 8.5,
    "ip_gs": 5.3,
    "era": 4.15,
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
        if proj >= 0.28:
            return "WATCH"
        return "PASS"
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
