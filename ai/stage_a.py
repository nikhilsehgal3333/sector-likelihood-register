"""Run stage A (rules) on all reports. Write the evidence table and the passages for stage B.

    py ai/stage_a.py <folder with the PDF files>

Writes results/ai_stage_a.csv (in the repository) and passages.jsonl (in the PDF folder, because
it holds longer text of the companies).
"""
from __future__ import annotations

import csv
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from ai.bafa import parse  # noqa: E402

HERE = Path(__file__).resolve().parent
OUT = HERE.parent / "results"


def main() -> None:
    folder = Path(sys.argv[1])
    corpus = list(csv.DictReader(open(HERE / "corpus.csv", encoding="utf-8")))
    rows = [["report", "company", "nace", "scope", "status", "risk", "page", "countries",
             "has_description"]]
    passages = []
    summary = []
    for entry in corpus:
        path = folder / f"{entry['id']}.pages.json"
        if not path.exists():
            continue
        report = parse(json.loads(path.read_text(encoding="utf-8")))
        if not report.answered["identified"]:
            summary.append(f"{entry['id']}: not in the standard BAFA layout, skipped")
            continue
        for scope, risks in report.identified.items():
            for risk, page in risks.items():
                rows.append([entry["id"], entry["company"], entry["nace"], scope, "identified",
                             risk, page, "", ""])
        for item in report.prioritised:
            rows.append([entry["id"], entry["company"], entry["nace"], item.scope, "prioritised",
                         item.risk, item.page, "; ".join(item.countries),
                         "yes" if item.description else "no"])
            if item.description:
                passages.append({"report": entry["id"], "company": entry["company"],
                                 "nace": entry["nace"], "scope": item.scope, "risk": item.risk,
                                 "page": item.page, "text": item.description})
        for scope in sorted(report.none_stated):
            rows.append([entry["id"], entry["company"], entry["nace"], scope, "prioritised",
                         "none_stated", "", "", ""])
        ident = {s: len(r) for s, r in report.identified.items()}
        summary.append(f"{entry['id']}: identified {ident}; prioritised "
                       f"{[(p.scope, p.risk, len(p.countries)) for p in report.prioritised]}; "
                       f"none stated {sorted(report.none_stated)}")
    OUT.mkdir(exist_ok=True)
    with open(OUT / "ai_stage_a.csv", "w", newline="", encoding="utf-8") as handle:
        csv.writer(handle).writerows(rows)
    with open(folder / "passages.jsonl", "w", encoding="utf-8") as handle:
        for passage in passages:
            handle.write(json.dumps(passage, ensure_ascii=False) + "\n")
    print("\n".join(summary))
    print(f"{len(rows) - 1} evidence rows, {len(passages)} passages with a description")


if __name__ == "__main__":
    main()
