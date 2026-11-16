"""E4 (robustness): how far does a division's point move when defensible choices change?"""
from __future__ import annotations

from experiments.common import fatal_by_division, md_table, window_mean
from register.scales import log_point

WINDOWS = {"1 year (2024)": [2024], "3 years (2022-2024)": [2022, 2023, 2024],
           "5 years (2020-2024)": [2020, 2021, 2022, 2023, 2024]}
SHIFTS = {"limits x 0.5": 0.5, "limits as proposed": 1.0, "limits x 2": 2.0}
EXAMPLES = ("H49", "C22", "M70", "B07", "A03")


def point_range(points: list[int]) -> int:
    return max(points) - min(points)


def run(refresh: bool = False) -> tuple[str, list[list]]:
    rates, _flags, labels, source = fatal_by_division(refresh)
    means = {name: window_mean(rates, years) for name, years in WINDOWS.items()}
    codes = sorted(set.intersection(*(set(m) for m in means.values())))
    n = len(codes)

    by_window = {c: [log_point(means[w][c] / 100_000) for w in WINDOWS] for c in codes}
    by_all = {c: [log_point(means[w][c] / 100_000, s) for w in WINDOWS for s in SHIFTS.values()]
              for c in codes}
    win_moves = sum(1 for c in codes if point_range(by_window[c]) > 0)
    dist: dict[int, int] = {}
    for c in codes:
        dist[point_range(by_all[c])] = dist.get(point_range(by_all[c]), 0) + 1

    rows = [[k, f"{v} of {n}"] for k, v in sorted(dist.items())]
    examples = [[f"{c} {labels[c]}"] + by_window[c] for c in EXAMPLES if c in by_window]
    text = "\n\n".join([
        "## E4. Sensitivity to the choices of the analyst",
        f"Data: the same EU-27 fatal accident rates ({source}), {n} divisions. Two choices are "
        f"varied: the time window ({', '.join(WINDOWS)}) and the position of the scale limits "
        f"({', '.join(SHIFTS)}). This gives {len(WINDOWS) * len(SHIFTS)} combinations.",
        f"- Window only: {win_moves} of {n} divisions change their point when the window changes.",
        md_table(["Sector"] + list(WINDOWS), examples),
        "Point range of each division across all combinations:",
        md_table(["Largest minus smallest point", "Divisions"], rows),
    ])
    table = [["nace", "label"] + [f"{w} | {s}" for w in WINDOWS for s in SHIFTS]] + \
            [[c, labels[c]] + by_all[c] for c in codes]
    return text, table
