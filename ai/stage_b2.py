"""Stage B, second design of the free-text task: two calls for each text.

The first design (stage_b.py, task "free") asked for the supplier group and the NACE division in
one call. The word-for-word test showed that the model then often wrote a code in place of words
from the text. This design separates the two steps:
  1. extract: name the industry, supplier group, product group, raw material or activity in the
     words of the text, say if the description is concrete, and give a quotation;
  2. code: only if step 1 gave words that are in the text, select a NACE division for them.

This design was made after the results of the first design were known, on the same texts. Thus
its results are not an independent test.

    py ai/stage_b2.py <folder with the PDF files>
"""
from __future__ import annotations

import csv
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from ai import llm  # noqa: E402
from ai.stage_b import RISK_NAMES, ROOT, SCOPE_TEXT, Cache, nace_divisions, squeeze  # noqa: E402

EXTRACT_SYSTEM = {
    "de": ("Du liest die Beschreibung eines Risikos aus einem Bericht nach dem deutschen "
           "Lieferkettensorgfaltspflichtengesetz. Aufgabe:\n"
           "1. group: Nennt der Text eine bestimmte Branche, Zulieferergruppe, Warengruppe, einen "
           "Rohstoff oder eine Tätigkeit, bei der das Risiko auftritt? Wenn ja, kopiere genau "
           "diese Wörter aus dem Text. Schreibe keinen Code und keine eigenen Wörter. Wenn der "
           "Text keine nennt, gib einen leeren Text an. Allgemeine Wörter wie 'Zulieferer' oder "
           "'Lieferanten' zählen nicht.\n"
           "2. concrete: true, wenn der Text ein bestimmtes Risiko beschreibt (was, wo oder bei "
           "wem). false, wenn der Text nur allgemein über das Vorgehen spricht.\n"
           "3. quote: Kopiere einen Satz oder Satzteil exakt aus dem Text, der deine Antwort "
           "belegt."),
    "en": ("You read the description of one risk from a report under the German Supply Chain "
           "Due Diligence Act. The description is in German. Task:\n"
           "1. group: Does the text name a specific industry, supplier group, product group, raw "
           "material or activity where the risk occurs? If yes, copy exactly these words from "
           "the text. Do not write a code and do not use your own words. If the text names none, "
           "give an empty text. General words such as 'Zulieferer' or 'Lieferanten' do not "
           "count.\n"
           "2. concrete: true if the text describes a specific risk (what, where or with whom). "
           "false if the text speaks only in general terms about the procedure.\n"
           "3. quote: Copy one sentence or part of a sentence exactly from the text that supports "
           "your answer."),
}
CODE_SYSTEM = ("You get a German phrase that names an industry, supplier group, product group, "
               "raw material or activity, and the text it comes from. Select the NACE division "
               "that fits the phrase best. Select NONE if no division fits.")


def main() -> None:
    folder = Path(sys.argv[1])
    cache = Cache(folder / "llm_cache.jsonl")
    model = llm.model_name()
    divisions = nace_divisions()
    extract_schema = {"type": "object", "additionalProperties": False,
                      "required": ["group", "concrete", "quote"],
                      "properties": {"group": {"type": "string"}, "concrete": {"type": "boolean"},
                                     "quote": {"type": "string"}}}
    code_schema = {"type": "object", "additionalProperties": False, "required": ["nace"],
                   "properties": {"nace": {"type": "string",
                                           "enum": ["NONE"] + sorted(divisions)}}}
    nace_list = "\n".join(f"{code} {label}" for code, label in sorted(divisions.items()))
    passages = [json.loads(line) for line in
                (folder / "passages.jsonl").read_text(encoding="utf-8").splitlines()]
    rows = [["report", "company", "company_nace", "scope", "risk", "page", "prompt", "group",
             "group_in_text", "nace", "concrete", "quote", "quote_in_text"]]
    stats = {lang: {"n": 0, "quote_ok": 0, "group_given": 0, "group_ok": 0, "concrete": 0}
             for lang in EXTRACT_SYSTEM}
    agree = {"n": 0, "group_given": 0, "same_group": 0, "nace": 0, "concrete": 0, "all": 0}
    for number, passage in enumerate(passages, start=1):
        text = passage["text"]
        answers = {}
        for lang, system in EXTRACT_SYSTEM.items():
            user = (f"Risk: {RISK_NAMES[passage['risk']]}\nScope: {SCOPE_TEXT[passage['scope']]}"
                    f"\n\nText:\n{text}")
            answer = dict(cache.call(model, system, user, extract_schema, 300))
            group = answer["group"].strip()
            quote_ok = bool(answer["quote"].strip()) and squeeze(answer["quote"]) in squeeze(text)
            group_ok = bool(group) and squeeze(group) in squeeze(text)
            answer["nace"] = ""
            if group_ok:  # only words that are in the text go to the coding step
                user = f"NACE divisions:\n{nace_list}\n\nPhrase: {group}\n\nText:\n{text}"
                answer["nace"] = cache.call(model, CODE_SYSTEM, user, code_schema, 30)["nace"]
            answer["group_ok"] = group_ok
            answers[lang] = answer
            s = stats[lang]
            s["n"] += 1
            s["quote_ok"] += quote_ok
            s["group_given"] += bool(group)
            s["group_ok"] += group_ok
            s["concrete"] += answer["concrete"]
            rows.append([passage["report"], passage["company"], passage["nace"], passage["scope"],
                         passage["risk"], passage["page"], lang, group,
                         "yes" if group_ok else "no", answer["nace"], answer["concrete"],
                         answer["quote"][:300], "yes" if quote_ok else "no"])
        a, b = answers["de"], answers["en"]
        same = [a["group_ok"] == b["group_ok"], a["nace"] == b["nace"],
                a["concrete"] == b["concrete"]]
        agree["n"] += 1
        agree["group_given"] += same[0]
        agree["same_group"] += squeeze(a["group"]) == squeeze(b["group"])
        agree["nace"] += same[1]
        agree["concrete"] += same[2]
        agree["all"] += all(same)
        print(f"{number}/{len(passages)} {passage['report']} {passage['risk']}: "
              f"de={a['group'][:30]!r}/{a['nace']} en={b['group'][:30]!r}/{b['nace']}", flush=True)
    with open(ROOT / "results" / "ai_free_text_v2.csv", "w", newline="", encoding="utf-8") as h:
        csv.writer(h).writerows(rows)
    summary = {"model": model, "passages": len(passages), "per_prompt": stats,
               "agreement_between_prompts": agree}
    (ROOT / "results" / "ai_free_text_v2.json").write_text(json.dumps(summary, indent=1),
                                                           encoding="utf-8")
    print(summary)


if __name__ == "__main__":
    main()
