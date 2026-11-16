"""E6 (integration): can a country factor times a sector factor reproduce country-sector rates?

Model: expected cases = person-years x country factor x sector factor (Poisson, main effects only).
The fit uses iterative proportional fitting, which gives the maximum-likelihood estimate.
"""
from __future__ import annotations

import math
import re

from experiments.common import exposure, fatal_counts, md_table
from register.scales import log_point

YEARS = [2020, 2021, 2022, 2023, 2024]
SECTION = re.compile(r"^[A-S]$")
MIN_EXPECTED = 20.0


def deviance(obs: dict, fit: dict) -> float:
    total = 0.0
    for key, y in obs.items():
        mu = fit[key]
        total += 2 * ((y * math.log(y / mu) if y > 0 else 0.0) - (y - mu))
    return total


def margin_fit(obs: dict, expo: dict, index: int) -> dict:
    tot_y: dict = {}
    tot_e: dict = {}
    for key in obs:
        tot_y[key[index]] = tot_y.get(key[index], 0.0) + obs[key]
        tot_e[key[index]] = tot_e.get(key[index], 0.0) + expo[key]
    return {key: expo[key] * tot_y[key[index]] / tot_e[key[index]] for key in obs}


def run(refresh: bool = False) -> tuple[str, list[list]]:
    data, labels, geos, source = fatal_counts(refresh)
    obs, expo = {}, {}
    dropped = 0
    for (geo, nace), series in data.items():
        if len(geo) != 2 or not SECTION.match(nace):
            continue
        e = exposure(series, YEARS)
        if e is None:
            dropped += 1
            continue
        obs[(geo, nace)] = sum(series[y][0] for y in YEARS)
        expo[(geo, nace)] = e
    countries = sorted({g for g, _ in obs})
    sectors = sorted({s for _, s in obs})
    overall = sum(obs.values()) / sum(expo.values())

    a = {g: 1.0 for g in countries}
    b = {s: overall for s in sectors}
    for _ in range(500):
        for g in countries:
            keys = [k for k in obs if k[0] == g]
            a[g] = sum(obs[k] for k in keys) / sum(expo[k] * b[k[1]] for k in keys)
        for s in sectors:
            keys = [k for k in obs if k[1] == s]
            b[s] = sum(obs[k] for k in keys) / sum(expo[k] * a[k[0]] for k in keys)
    both = {k: expo[k] * a[k[0]] * b[k[1]] for k in obs}

    d_null = deviance(obs, {k: expo[k] * overall for k in obs})
    d_country = deviance(obs, margin_fit(obs, expo, 0))
    d_sector = deviance(obs, margin_fit(obs, expo, 1))
    d_both = deviance(obs, both)
    df = len(obs) - len(countries) - len(sectors) + 1

    big = [k for k in obs if both[k] >= MIN_EXPECTED]
    ratio = {k: obs[k] / both[k] for k in big}
    off = [k for k in big
           if log_point(obs[k] / expo[k] / 1e5) != log_point(both[k] / expo[k] / 1e5)]
    within = sum(1 for k in big if 0.67 <= ratio[k] <= 1.5)
    extremes = sorted(big, key=lambda k: abs(math.log(ratio[k])) if ratio[k] > 0 else 99,
                      reverse=True)[:8]

    def share(d: float) -> str:
        return f"{100 * (1 - d / d_null):.0f}%"

    fit_rows = [["Sector only", f"{d_sector:,.0f}", share(d_sector)],
                ["Country only", f"{d_country:,.0f}", share(d_country)],
                ["Country factor x sector factor", f"{d_both:,.0f}", share(d_both)]]
    ext_rows = [[geos[g], f"{s} {labels[s]}", f"{obs[(g, s)]:.0f}", f"{both[(g, s)]:.1f}",
                 f"{ratio[(g, s)]:.2f}"] for g, s in extremes]
    text = "\n\n".join([
        "## E6. Does country factor times sector factor work?",
        f"Data: fatal accidents at work {YEARS[0]}-{YEARS[-1]} by country and NACE section "
        f"(`hsw_n2_02`; {source}): {len(obs)} country-sector cells, {len(countries)} countries, "
        f"{len(sectors)} sections, {sum(obs.values()):,.0f} fatal accidents. {dropped} cells "
        "without any recorded accident since 2020 have no derivable person-years and are left out.",
        md_table(["Model", "Deviance", "Share of the null deviance explained"], fit_rows),
        f"- Null deviance (one rate for all cells): {d_null:,.0f}. Residual deviance of the factor "
        f"model: {d_both:,.0f} on {df} degrees of freedom, a ratio of {d_both / df:.1f}. A ratio "
        "of 1 means that only chance is left. A larger ratio means that real country-sector "
        "differences remain.",
        f"- In the {len(big)} cells with at least {MIN_EXPECTED:.0f} expected accidents, "
        f"{within} ({100 * within / len(big):.0f}%) have an observed count between 0.67 and 1.5 "
        f"times the model value. {len(off)} ({100 * len(off) / len(big):.0f}%) get a different "
        "log-scale point from the model than from their own rate.",
        "Largest differences (cells with at least 20 expected accidents):",
        md_table(["Country", "Section", "Observed", "Model", "Observed / model"], ext_rows),
        "- Limit: the recording systems of the countries are different. A part of each difference "
        "can come from these systems and not from the real risk.",
    ])
    table = [["geo", "section", "observed", "person_years_100k", "model", "ratio"]] + \
            [[g, s, obs[(g, s)], round(expo[(g, s)], 3), round(both[(g, s)], 2),
              round(obs[(g, s)] / both[(g, s)], 3)] for g, s in sorted(obs)]
    return text, table
