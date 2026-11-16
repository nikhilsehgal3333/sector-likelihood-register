"""E7 (result): a register for one right. Each NACE division gets a point, a range and a grade.

Right: occupational health and safety. Event: fatal accident at work. Unit: one worker for one
year. Period: 2020-2024, pooled. Area: EU-27. Scale: the fixed logarithmic scale of this study.
"""
from __future__ import annotations

import math

from experiments.common import DIVISION, exposure, fatal_counts, md_table
from experiments.e5_sparse import shrink
from register.scales import log_point

GEO = "EU27_2020"
YEARS = [2020, 2021, 2022, 2023, 2024]
Z = 1.96
EXAMPLES = ("H49", "H52", "H53", "C22", "C29", "M70", "B07", "F43", "C15")


def poisson_interval(cases: float) -> tuple[float, float]:
    """95% interval for a Poisson count (Byar's approximation)."""
    if cases == 0:
        return 0.0, -math.log(0.025)
    low = cases * (1 - 1 / (9 * cases) - Z / (3 * math.sqrt(cases))) ** 3
    up = cases + 1
    high = up * (1 - 1 / (9 * up) + Z / (3 * math.sqrt(up))) ** 3
    return max(low, 0.0), high


def grade(cases: float) -> str:
    """Confidence grade from the number of cases. The limits are a proposal of this study."""
    if cases >= 100:
        return "high"
    return "medium" if cases >= 20 else "low"


def run(refresh: bool = False) -> tuple[str, list[list]]:
    data, labels, _geos, source = fatal_counts(refresh)
    cases, expo = {}, {}
    for (geo, nace), series in data.items():
        if geo == GEO and DIVISION.match(nace):
            e = exposure(series, YEARS)
            if e:
                cases[nace] = sum(series[y][0] for y in YEARS)
                expo[nace] = e
    shrunk, _a = shrink(cases, expo)

    rows = {}
    for code in sorted(cases):
        rate = cases[code] / expo[code]
        low, high = (v / expo[code] for v in poisson_interval(cases[code]))
        rows[code] = [code, labels[code], int(cases[code]), round(rate, 2), round(low, 2),
                      round(high, 2), log_point(rate / 1e5), log_point(low / 1e5),
                      log_point(high / 1e5), grade(cases[code]), round(shrunk[code], 2),
                      log_point(shrunk[code] / 1e5)]
    n = len(rows)
    grades = {g: sum(1 for r in rows.values() if r[9] == g) for g in ("high", "medium", "low")}
    one_point = sum(1 for r in rows.values() if r[7] == r[8])
    wide = sum(1 for r in rows.values() if r[8] - r[7] >= 2)
    shown = [[f"{r[0]} {r[1]}", r[2], f"{r[3]:.2f} ({r[4]:.2f} to {r[5]:.2f})", r[6],
              f"{r[7]} to {r[8]}" if r[7] != r[8] else str(r[6]), r[9]]
             for r in (rows[c] for c in EXAMPLES if c in rows)]
    text = "\n\n".join([
        "## E7. A register for one right: health and safety",
        f"Event: fatal accident at work. Unit: one worker for one year. Period: {YEARS[0]}-"
        f"{YEARS[-1]}, pooled. Area: EU-27. Data: `hsw_n2_02` ({source}). The range is the 95% "
        "interval of the count of cases. The grade comes from the number of cases: high from "
        "100, medium from 20, low below 20. The full table for all divisions is in "
        "`results/e7_register.csv`.",
        md_table(["Division", "Cases", "Rate per 100,000 (range)", "Point", "Point range",
                  "Confidence"], shown),
        f"- {n} divisions: {grades['high']} with high, {grades['medium']} with medium and "
        f"{grades['low']} with low confidence.",
        f"- For {one_point} of {n} divisions the range stays in one point. For {wide} divisions "
        "the range covers three or more points.",
        "- Limit: this register is for one right, for fatal events, for work in the EU. It shows "
        "the format of a register entry. It is not a register for global supply chains.",
    ])
    table = [["nace", "label", "cases_2020_2024", "rate_per_100k", "rate_low", "rate_high",
              "point", "point_low", "point_high", "confidence", "shrunk_rate_per_100k",
              "shrunk_point"]] + list(rows.values())
    return text, table
