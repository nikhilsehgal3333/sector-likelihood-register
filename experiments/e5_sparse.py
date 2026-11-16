"""E5 (data gaps): how to score divisions with few or no recorded cases.

Method: gamma-Poisson shrinkage (empirical Bayes). The rate of a division is pulled toward the rate
of its NACE section. The pull is strong when the division has little exposure and weak when it has
much. The strength is estimated from the data (method of moments).
"""
from __future__ import annotations

from experiments.common import DIVISION, exposure, fatal_counts, md_table
from register.scales import log_point
from register.stats import spearman

GEO = "EU27_2020"
TEST = [2023, 2024]
BASES = {"2022 alone": [2022], "2020-2022": [2020, 2021, 2022]}
INF = float("inf")


def shrink(cases: dict[str, float], expo: dict[str, float]) -> tuple[dict[str, float], float]:
    """Return (shrunk rate per division, estimated prior strength a)."""
    sec_cases: dict[str, float] = {}
    sec_expo: dict[str, float] = {}
    for code in cases:
        sec_cases[code[0]] = sec_cases.get(code[0], 0.0) + cases[code]
        sec_expo[code[0]] = sec_expo.get(code[0], 0.0) + expo[code]
    prior = {code: sec_cases[code[0]] / sec_expo[code[0]] for code in cases}
    expected = {code: prior[code] * expo[code] for code in cases}
    usable = [code for code in cases if expected[code] > 0]
    weight = sum(expected[c] for c in usable)
    excess = sum(expected[c] * ((cases[c] / expected[c] - 1) ** 2 - 1 / expected[c])
                 for c in usable) / weight
    a = 1 / excess if excess > 0 else INF
    out = {}
    for code in cases:
        if expected[code] <= 0 or a == INF:
            out[code] = prior[code]
        else:
            out[code] = prior[code] * (cases[code] + a) / (expected[code] + a)
    return out, a


def mean_error(est: dict[str, float], truth: dict[str, float], subset: list[str]) -> float:
    return sum(abs(est[c] - truth[c]) for c in subset) / len(subset)


def wrong_points(est: dict[str, float], truth: dict[str, float], subset: list[str]) -> int:
    return sum(1 for c in subset if log_point(est[c] / 1e5) != log_point(truth[c] / 1e5))


def run(refresh: bool = False) -> tuple[str, list[list]]:
    data, labels, _geos, source = fatal_counts(refresh)
    series = {nace: s for (geo, nace), s in data.items() if geo == GEO and DIVISION.match(nace)}

    test_cases, test_rate = {}, {}
    for code, s in series.items():
        e = exposure(s, TEST)
        if e:
            test_cases[code] = sum(s[y][0] for y in TEST)
            test_rate[code] = test_cases[code] / e

    rows = []
    table = [["base", "nace", "label", "base_cases", "raw_per_100k", "shrunk_per_100k",
              "test_per_100k", "raw_point", "shrunk_point", "test_point"]]
    notes = []
    for name, years in BASES.items():
        cases, expo = {}, {}
        for code, s in series.items():
            e = exposure(s, years)
            if e and code in test_rate:
                cases[code] = sum(s[y][0] for y in years)
                expo[code] = e
        raw = {c: cases[c] / expo[c] for c in cases}
        shrunk, a = shrink(cases, expo)
        codes = sorted(cases)
        few = [c for c in codes if cases[c] < 5 * len(years)]
        zero = [c for c in codes if cases[c] == 0]
        zero_later = [c for c in zero if test_cases[c] > 0]
        truth = [test_rate[c] for c in codes]
        rows.append([
            name, len(codes), len(few), f"{len(zero)} ({len(zero_later)})",
            f"{spearman([raw[c] for c in codes], truth):.3f} / "
            f"{spearman([shrunk[c] for c in codes], truth):.3f}",
            f"{mean_error(raw, test_rate, codes):.2f} / {mean_error(shrunk, test_rate, codes):.2f}",
            f"{mean_error(raw, test_rate, few):.2f} / {mean_error(shrunk, test_rate, few):.2f}"
            if few else "n/a",
            f"{wrong_points(raw, test_rate, codes)} / {wrong_points(shrunk, test_rate, codes)}",
        ])
        notes.append(f"- {name}: estimated prior strength a = {a:.1f}. A division with fewer "
                     "expected cases than a takes more than half of its score from its section.")
        for c in codes:
            table.append([name, c, labels[c], cases[c], round(raw[c], 2), round(shrunk[c], 2),
                          round(test_rate[c], 2), log_point(raw[c] / 1e5),
                          log_point(shrunk[c] / 1e5), log_point(test_rate[c] / 1e5)])

    text = "\n\n".join([
        "## E5. Divisions with few or no recorded cases",
        "Data: number and rate of fatal accidents at work, EU-27, NACE divisions (`hsw_n2_02`; "
        f"{source}). Person-years are derived as number / rate. Each estimate is built on a base "
        f"window and compared with the observed {TEST[0]}-{TEST[1]} rate. Raw is the recorded "
        "rate of the division. Shrunk pulls that rate toward the rate of its NACE section.",
        md_table(["Base window", "Divisions", "Fewer than 5 cases per year",
                  "Zero cases (of these, cases later)", "Spearman with later rate: raw / shrunk",
                  "Mean absolute error per 100,000: raw / shrunk",
                  "Same error, divisions with fewer than 5 cases per year",
                  "Wrong log-scale point: raw / shrunk"], rows),
        "\n".join(notes),
        "- Limit: the section rate is a good substitute only if the divisions of one section are "
        "similar. A division that is alone in its section keeps its raw rate.",
    ])
    return text, table
