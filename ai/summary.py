"""Write results/AI_RESULTS.md from the stage A table and, if they exist, the stage B results."""
from __future__ import annotations

import csv
import json
from collections import Counter, defaultdict
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "results"


def table(header: list[str], rows: list[list]) -> str:
    lines = ["| " + " | ".join(header) + " |", "|" + "---|" * len(header)]
    lines += ["| " + " | ".join(str(c) for c in row) + " |" for row in rows]
    return "\n".join(lines)


def stage_a() -> str:
    rows = list(csv.DictReader(open(OUT / "ai_stage_a.csv", encoding="utf-8")))
    reports = sorted({r["report"] for r in rows})
    per_report = defaultdict(lambda: Counter())
    nace = {}
    for r in rows:
        nace[r["report"]] = r["nace"]
        if r["risk"] != "none_stated":
            per_report[r["report"]][r["status"]] += 1
    report_rows = [[rep, nace[rep], per_report[rep]["identified"], per_report[rep]["prioritised"]]
                   for rep in sorted(reports, key=lambda x: (nace[x], x))]
    identified = [per_report[rep]["identified"] for rep in reports]
    prioritised = [r for r in rows if r["status"] == "prioritised" and r["risk"] != "none_stated"]
    with_country = sum(1 for r in prioritised if r["countries"])
    with_text = sum(1 for r in prioritised if r["has_description"] == "yes")
    by_risk = Counter(r["risk"] for r in prioritised)
    companies = defaultdict(set)
    for r in prioritised:
        companies[r["risk"]].add(r["report"])
    risk_rows = [[risk, n, len(companies[risk])] for risk, n in by_risk.most_common()]
    return "\n\n".join([
        "## A. Rules only: the standard fields of the BAFA questionnaire",
        f"{len(reports)} reports in the standard layout. The parser found {len(rows)} entries. "
        "Each entry has the report, the scope (own operations, direct suppliers, indirect "
        "suppliers), the risk, and the page number. No language model is used in this stage.",
        table(["Report", "NACE division of the company", "Risk entries identified",
               "Risk entries prioritised"], report_rows),
        f"- The number of identified risk entries per company runs from {min(identified)} to "
        f"{max(identified)}. Two companies in one sector can report very different numbers. A "
        "count of entries measures how a company reports. It does not measure how often a "
        "violation occurs.",
        f"- {len(prioritised)} prioritised risk entries. {with_country} name one or more "
        f"countries. {with_text} have a description in the words of the company.",
        table(["Prioritised risk", "Entries", "Companies"], risk_rows),
    ])


def copied(empty: list[dict]) -> int:
    """Number of empty lists where the model returned the risk set of another scope."""
    by_scope = defaultdict(set)
    for r in csv.DictReader(open(OUT / "ai_stage_a.csv", encoding="utf-8")):
        if r["status"] == "identified":
            by_scope[(r["report"], r["scope"])].add(r["risk"])
    count = 0
    for r in empty:
        added = set(r["added_by_model"].split())
        count += any(added == risks for (report, scope), risks in by_scope.items()
                     if report == r["report"] and scope != r["scope"])
    return count


def stage_b() -> str:
    parts = ["## B. Local language model"]
    known = OUT / "ai_known_answer.json"
    free = OUT / "ai_free_text.json"
    if not known.exists() and not free.exists():
        return "\n\n".join(parts + ["Not run yet. See the README for the commands."])
    if known.exists():
        k = json.loads(known.read_text(encoding="utf-8"))
        parts.append(
            f"Model: `{k['model']}`, temperature 0.\n\n"
            "**Known-answer test.** The model read the raw pages with the lists of identified "
            f"risks. The rules of stage A give the correct answer. {k['lists']} lists with "
            f"{k['risks_by_rules']} risk entries: the model found {k['model_correct']}, missed "
            f"{k['model_missed']} and added {k['model_added']} that are not in the list "
            f"(precision {k['precision']}, recall {k['recall']}). {k['lists_identical']} of "
            f"{k['lists']} lists are identical to the rules.")
        diff = [r for r in csv.DictReader(open(OUT / "ai_known_answer.csv", encoding="utf-8"))
                if r["missed_by_model"] or r["added_by_model"]]
        empty = [r for r in diff if r["rules"] == "0"]
        parts.append(
            f"- The author compared the {len(diff)} lists that differ with the report text. The "
            "rules were correct in each of them."
            f"\n- In {len(empty)} of these {len(diff)} lists the company answered \"Keine\" "
            f"(none). {sum(len(r['added_by_model'].split()) for r in empty)} of the "
            f"{k['model_added']} added entries come from these lists. In {copied(empty)} of the "
            f"{len(empty)} lists the model gave exactly the risks that the company lists for a "
            "different scope."
            "\n- Reading: where the layout is fixed, rules are more reliable than this model. The "
            "typical error of the model is not an invented risk. It is a real risk in the wrong "
            "place.")
    labels = {"ai_free_text.json": "First design: one call gives the group, the NACE division "
                                   "and the quotation",
              "ai_free_text_v2.json": "Second design: one call extracts, a second call selects "
                                      "the NACE division only for a group that is in the text"}
    shown = False
    for name, label in labels.items():
        if not (OUT / name).exists():
            continue
        f = json.loads((OUT / name).read_text(encoding="utf-8"))
        if not shown:
            parts.append(
                f"**Free text.** {f['passages']} descriptions of prioritised risks. The model "
                "names the industry, supplier group, product group, raw material or activity "
                "that the company connects to the risk, selects a NACE division and gives a "
                "quotation. A program tests if the quotation and the group are in the "
                "description word for word. Each design runs with German and with English "
                "instructions.")
            shown = True
        rows = []
        for lang, s in f["per_prompt"].items():
            rows.append([lang, s["n"], f"{s['quote_ok']} ({100 * s['quote_ok'] / s['n']:.0f}%)",
                         s["group_given"], s["group_ok"], s["concrete"]])
        a = f["agreement_between_prompts"]
        parts.append(f"*{label}.*")
        parts.append(table(["Instructions", "Descriptions", "Quotation found word for word",
                            "Group named", "Group found word for word", "Rated concrete"], rows))
        parts.append(
            f"- Agreement between the two instructions on {a['n']} descriptions: group given or "
            f"not {a['group_given']}, NACE division {a['nace']}, concrete or not {a['concrete']}, "
            f"all three {a['all']}.")
    if shown:
        parts.append("- The second design was made after the results of the first design were "
                     "known, on the same texts. Its results are not an independent test.")
        parts.append("- A quotation that is in the text shows that the model did not invent the "
                     "evidence. It does not show that the group or the NACE division is correct. "
                     "That needs a check by a person. This check is not done yet.")
    return "\n\n".join(parts)


def main() -> None:
    text = "\n\n".join([
        f"# Results of the text pipeline\n\nGenerated by `ai/summary.py` on "
        f"{date.today().isoformat()}. Source: public reports under the German Supply Chain Due "
        "Diligence Act (LkSG) for 2023, listed in `ai/corpus.csv`.",
        stage_a(), stage_b()])
    (OUT / "AI_RESULTS.md").write_text(text + "\n", encoding="utf-8")
    print(text)


if __name__ == "__main__":
    main()
