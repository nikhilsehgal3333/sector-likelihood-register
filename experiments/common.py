"""Shared loading code for the experiments."""
from __future__ import annotations

import re

from register import eurostat

DIVISION = re.compile(r"^[A-U]\d\d$")


def fatal_by_division(refresh: bool = False):
    """EU-27 fatal accidents at work per 100,000 persons employed, by NACE division and year.

    Returns (rates[code][year], flags[code][year], labels[code], source note).
    """
    doc = eurostat.fetch("hsw_n2_02", "hsw_n2_02_eu27", refresh, geo="EU27_2020", unit="RT_INC")
    rates: dict[str, dict[int, float]] = {}
    flags: dict[str, dict[int, str]] = {}
    for (_freq, _unit, nace, _geo, year), (value, flag) in eurostat.cells(doc).items():
        if DIVISION.match(nace) or nace == "TOTAL":
            rates.setdefault(nace, {})[int(year)] = value
            flags.setdefault(nace, {})[int(year)] = flag
    return rates, flags, eurostat.labels(doc, "nace_r2"), eurostat.meta(doc)


def window_mean(rates: dict[str, dict[int, float]], years: list[int]) -> dict[str, float]:
    """Mean rate per division over `years`. Divisions with a missing year are left out."""
    out = {}
    for code, series in rates.items():
        if code != "TOTAL" and all(year in series for year in years):
            out[code] = sum(series[year] for year in years) / len(years)
    return out


def md_table(header: list[str], rows: list[list]) -> str:
    lines = ["| " + " | ".join(header) + " |", "|" + "---|" * len(header)]
    lines += ["| " + " | ".join(str(cell) for cell in row) + " |" for row in rows]
    return "\n".join(lines)
