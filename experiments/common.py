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


def fatal_counts(refresh: bool = False):
    """Fatal accidents since 2020 for every country and NACE code: number and rate.

    Returns (data[(geo, nace)][year] = (number, rate per 100,000), nace labels, geo labels, note).
    A cell is kept only if both the number and the rate are present.
    """
    doc = eurostat.fetch("hsw_n2_02", "hsw_n2_02_since2020", refresh, sinceTimePeriod="2020")
    number: dict = {}
    rate: dict = {}
    for (_freq, unit, nace, geo, year), (value, _flag) in eurostat.cells(doc).items():
        (number if unit == "NR" else rate).setdefault((geo, nace), {})[int(year)] = value
    data = {}
    for key, series in number.items():
        both = {y: (series[y], rate[key][y]) for y in series if y in rate.get(key, {})}
        if both:
            data[key] = both
    return data, eurostat.labels(doc, "nace_r2"), eurostat.labels(doc, "geo"), eurostat.meta(doc)


def exposure(series: dict[int, tuple[float, float]], years: list[int]) -> float | None:
    """Person-years of work in `years`, in units of 100,000, derived as number / rate.

    A year with no accident has no derivable exposure. Such a year gets the mean exposure of the
    other years since 2020. Returns None if no year since 2020 has a derivable exposure.
    """
    known = [n / r for n, r in series.values() if n > 0 and r > 0]
    if not known:
        return None
    fallback = sum(known) / len(known)
    total = 0.0
    for year in years:
        if year not in series:
            return None
        n, r = series[year]
        total += n / r if n > 0 and r > 0 else fallback
    return total


def md_table(header: list[str], rows: list[list]) -> str:
    lines = ["| " + " | ".join(header) + " |", "|" + "---|" * len(header)]
    lines += ["| " + " | ".join(str(cell) for cell in row) + " |" for row in rows]
    return "\n".join(lines)
