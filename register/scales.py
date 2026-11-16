"""Three ways to turn an annual rate into a point from 1 to 10.

The rate is the share of workers with the event in one year (for example 7.5 per 100,000 = 0.000075).
Only `log_point` gives a point with a fixed meaning. The other two are here for comparison.
"""
from __future__ import annotations

import math

# Lower limit of each point, as an annual share. Each point is about 3 times the point below.
# This table is a proposal of this study. It is not a standard.
LOG_ANCHORS = {
    10: 1 / 10,
    9: 1 / 30,
    8: 1 / 100,
    7: 1 / 300,
    6: 1 / 1_000,
    5: 1 / 3_000,
    4: 1 / 10_000,
    3: 1 / 30_000,
    2: 1 / 100_000,
}


def log_point(share: float, shift: float = 1.0) -> int:
    """Fixed logarithmic scale. `shift` multiplies every limit (sensitivity test only)."""
    for point in range(10, 1, -1):
        if share >= LOG_ANCHORS[point] * shift:
            return point
    return 1


def decile_points(shares: dict[str, float]) -> dict[str, int]:
    """Relative scale: point = 1 + floor(10 x rank / n), ranks ascending from 0."""
    order = sorted(shares, key=lambda code: (shares[code], code))
    n = len(order)
    return {code: 1 + (10 * rank) // n for rank, code in enumerate(order)}


def company_probability(share: float, workers: int) -> float:
    """P(at least one event in a company in one year), Poisson approximation."""
    return 1.0 - math.exp(-share * workers)


def linear_point(share: float, workers: int = 250) -> int:
    """Linear scale: 10% steps of the company probability for a company of `workers`."""
    return max(1, min(10, math.ceil(10 * company_probability(share, workers))))
