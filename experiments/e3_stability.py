"""E3 (validation, part): does a score built on past years still rank the later years?"""
from __future__ import annotations

from experiments.common import fatal_by_division, md_table, window_mean
from register.scales import decile_points, log_point
from register.stats import spearman

TEST = [2023, 2024]
BASES = {"2020-2022 mean": [2020, 2021, 2022], "2022 alone": [2022]}


def run(refresh: bool = False) -> tuple[str, list[list]]:
    rates, _flags, _labels, source = fatal_by_division(refresh)
    test = window_mean(rates, TEST)
    rows = []
    table = [["base", "nace", "base_rate", "test_rate", "base_log", "test_log",
              "base_decile", "test_decile"]]
    n = 0
    for name, years in BASES.items():
        base = window_mean(rates, years)
        codes = sorted(set(base) & set(test))
        n = len(codes)
        b = {c: base[c] / 100_000 for c in codes}
        t = {c: test[c] / 100_000 for c in codes}
        db, dt = decile_points(b), decile_points(t)
        log_moves = sum(1 for c in codes if log_point(b[c]) != log_point(t[c]))
        dec_moves = sum(1 for c in codes if db[c] != dt[c])
        dec_big = sum(1 for c in codes if abs(db[c] - dt[c]) >= 2)
        rho = spearman([b[c] for c in codes], [t[c] for c in codes])
        rows.append([name, f"{rho:.3f}", f"{log_moves} of {n} ({100 * log_moves / n:.0f}%)",
                     f"{dec_moves} of {n} ({100 * dec_moves / n:.0f}%)", dec_big])
        for c in codes:
            table.append([name, c, round(base[c], 2), round(test[c], 2), log_point(b[c]),
                          log_point(t[c]), db[c], dt[c]])
    counts: dict[int, int] = {}
    for value in test.values():
        point = log_point(value / 100_000)
        counts[point] = counts.get(point, 0) + 1
    used = ", ".join(f"{counts[p]} divisions at point {p}" for p in sorted(counts))
    text = "\n\n".join([
        "## E3. Stability over time (test-retest)",
        f"Data: the same EU-27 fatal accident rates ({source}). A score is built on a base window "
        f"and compared with the {TEST[0]}-{TEST[1]} mean, {n} divisions.",
        md_table(["Base window", f"Spearman with {TEST[0]}-{TEST[1]}", "Log-scale point changes",
                  "Decile changes", "Decile changes of 2 or more"], rows),
        f"- Points in the test window: {used}.",
        "- Limit: this is stability for one right inside the EU. It is not a test of validity. "
        "Fatal accidents are rare, so they use only the lowest points of the scale.",
    ])
    return text, table
