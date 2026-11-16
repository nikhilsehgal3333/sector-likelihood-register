"""E2 (visibility): recorded non-fatal accidents follow the reporting system, fatal ones much less."""
from __future__ import annotations

from experiments.common import md_table
from register import eurostat
from register.stats import spearman

YEAR = "2022"


def spread(values: list[float]) -> float:
    return max(values) / min(values)


def run(refresh: bool = False) -> tuple[str, list[list]]:
    docs = {
        "nonfatal": eurostat.fetch("hsw_n2_01", "hsw_n2_01_total", refresh, nace_r2="TOTAL",
                                   unit="RT_INC", time=YEAR),
        "fatal": eurostat.fetch("hsw_n2_02", "hsw_n2_02_total", refresh, nace_r2="TOTAL",
                                unit="RT_INC", time=YEAR),
    }
    series: dict[str, dict[str, tuple[float, str]]] = {}
    for name, doc in docs.items():
        geo_at = doc["id"].index("geo")
        for key, cell in eurostat.cells(doc).items():
            series.setdefault(key[geo_at], {})[name] = cell
    names = eurostat.labels(docs["fatal"], "geo")

    rows = []
    for geo, cell in series.items():
        if len(geo) != 2 or "nonfatal" not in cell or "fatal" not in cell:
            continue  # keep countries only; drop EU aggregates and gaps
        (nonfatal, flag_n), (fatal, flag_f) = cell["nonfatal"], cell["fatal"]
        if fatal <= 0:
            continue
        rows.append([geo, names[geo], nonfatal, fatal, nonfatal / fatal, flag_n + flag_f])
    rows.sort(key=lambda r: r[4])

    ratios = [r[4] for r in rows]
    nonfatal = [r[2] for r in rows]
    fatal = [r[3] for r in rows]
    rho = spearman(nonfatal, fatal)
    shown = [[r[0], r[1], f"{r[2]:,.2f}", f"{r[3]:.2f}", f"{r[4]:,.0f}", r[5]] for r in rows]
    text = "\n\n".join([
        "## E2. Recorded cases follow the reporting system",
        "Data: non-fatal (`hsw_n2_01`) and fatal (`hsw_n2_02`) accidents at work per 100,000 "
        f"persons employed, all NACE activities, {YEAR}, {len(rows)} countries "
        f"({eurostat.meta(docs['nonfatal'])}). The flag column shows Eurostat status flags "
        "(b = break in series, e = estimated, p = provisional, u = low reliability).",
        md_table(["Code", "Country", "Non-fatal", "Fatal", "Non-fatal per fatal", "Flag"], shown),
        f"- Non-fatal per fatal accident runs from {min(ratios):,.0f} ({rows[0][1]}) to "
        f"{max(ratios):,.0f} ({rows[-1][1]}): a factor of {spread(ratios):,.0f}.",
        f"- The recorded non-fatal rate differs by a factor of {spread(nonfatal):,.0f} between "
        f"countries. The fatal rate differs by a factor of {spread(fatal):,.1f}.",
        "- Spearman correlation between the non-fatal and the fatal rate across countries: "
        f"{rho:+.2f}. If the recorded non-fatal accidents measured the same danger as the fatal "
        "accidents, this value would be clearly positive.",
        "- Eurostat reports under-reporting of non-fatal accidents in some Member States (ESAW "
        "metadata). The table agrees with that statement. It does not prove the cause.",
    ])
    table = [["geo", "country", "nonfatal_per_100k", "fatal_per_100k", "ratio", "flag"]] + \
            [[r[0], r[1], r[2], r[3], round(r[4], 1), r[5]] for r in rows]
    return text, table
