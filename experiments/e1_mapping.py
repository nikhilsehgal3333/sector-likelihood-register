"""E1 (construct): the same rates give different 1-10 points under different mappings."""
from __future__ import annotations

from experiments.common import fatal_by_division, md_table, window_mean
from register.scales import company_probability, decile_points, linear_point, log_point

FOCUS = ["H49", "C22", "M70"]
YEAR = 2024


def run(refresh: bool = False) -> tuple[str, list[list]]:
    rates, flags, labels, source = fatal_by_division(refresh)
    per_100k = window_mean(rates, [YEAR])
    shares = {code: value / 100_000 for code, value in per_100k.items()}
    deciles = decile_points(shares)

    rows = []
    for code in sorted(shares):
        share = shares[code]
        rows.append([code, labels[code], f"{per_100k[code]:.2f}", flags[code][YEAR],
                     log_point(share), deciles[code], linear_point(share)])

    focus_rows = []
    for code in FOCUS:
        share = shares[code]
        one_in = f"1 in {round(1 / share):,}" if share > 0 else "0"
        sizes = " / ".join(f"{100 * company_probability(share, n):.2f}%" for n in (50, 250, 5000))
        focus_rows.append([f"{code} {labels[code]}", f"{per_100k[code]:.2f}", one_in, sizes,
                           log_point(share), deciles[code], linear_point(share)])

    used = sorted({log_point(s) for s in shares.values()})
    zero = sorted(code for code, s in shares.items() if s == 0)
    linear_one = sum(1 for r in rows if r[6] == 1)
    text = "\n\n".join([
        "## E1. One set of rates, three mappings, three different scores",
        f"Data: fatal accidents at work per 100,000 persons employed, EU-27, {YEAR}, "
        f"{len(shares)} NACE divisions (`hsw_n2_02`; {source}).",
        md_table(["Sector", "Rate per 100,000", "Per worker per year",
                  "Company with 50 / 250 / 5,000 workers: P(at least 1 per year)",
                  "Fixed log scale", "Decile", "Linear 10% steps (250 workers)"], focus_rows),
        "- The three mappings keep the same order of the sectors, but the points differ: "
        f"{'/'.join(str(r[4]) for r in focus_rows)} (log), "
        f"{'/'.join(str(r[5]) for r in focus_rows)} (decile), "
        f"{'/'.join(str(r[6]) for r in focus_rows)} (linear).",
        f"- Across all {len(shares)} divisions the fixed log scale uses the points {used}. "
        f"The linear scale gives point 1 to {linear_one} divisions.",
        f"- Divisions with a rate of 0 in {YEAR}: {', '.join(zero) if zero else 'none'}. "
        "A rate of 0 in one year is not a probability of 0.",
    ])
    table = [["nace", "label", "rate_per_100k", "flag", "log_point", "decile", "linear_point"]] + rows
    return text, table
