"""Stage B: use a local open-weight language model where rules cannot read the report.

Two tasks:
  known   The model reads the raw pages with the list of identified risks. Stage A already read
          these lists with rules, so the correct answer is known. This measures the error rate of
          the model on an easy task.
  free    The model reads the free-text description of each prioritised risk. It names the
          supplier group, product or activity that the company connects to the risk, gives a NACE
          division for it, and gives a quotation. A program then tests if the quotation is in the
          report word for word. The task runs with two prompts (German and English instructions)
          to measure how much the prompt changes the answer.

    py ai/stage_b.py known <folder with the PDF files>
    py ai/stage_b.py free  <folder with the PDF files>

Each call is stored in <folder>/llm_cache.jsonl, so a second run does not call the model again.
"""
from __future__ import annotations

import csv
import hashlib
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from ai import bafa, llm  # noqa: E402

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
SCOPE_TEXT = {"own": "im eigenen Geschäftsbereich", "direct": "bei unmittelbaren Zulieferern",
              "indirect": "bei mittelbaren Zulieferern"}
RISK_NAMES = {
    "child_labour": "Verbot von Kinderarbeit",
    "forced_labour": "Verbot von Zwangsarbeit und aller Formen der Sklaverei",
    "health_safety": "Missachtung von Arbeitsschutz und arbeitsbedingten Gesundheitsgefahren",
    "freedom_of_association": "Missachtung der Koalitionsfreiheit",
    "discrimination": "Verbot der Ungleichbehandlung in Beschäftigung",
    "adequate_wage": "Verbot des Vorenthaltens eines angemessenen Lohns",
    "environmental_harm": "Zerstörung der natürlichen Lebensgrundlage durch Umweltverunreinigungen",
    "land_rights": "Widerrechtliche Verletzung von Landrechten",
    "security_forces": "Verbot der Beauftragung oder Nutzung privater/öffentlicher Sicherheitskräfte",
    "mercury": "Verbotene Herstellung, Einsatz und/oder Entsorgung von Quecksilber",
    "persistent_pollutants": "Verbotene Produktion und/oder Verwendung von Stoffen (POP)",
    "hazardous_waste": "Verbotene Ein-/Ausfuhr gefährlicher Abfälle",
    "other": "Sonstige Verbote",
}


class Cache:
    def __init__(self, path: Path):
        self.path = path
        self.items = {}
        if path.exists():
            for line in path.read_text(encoding="utf-8").splitlines():
                entry = json.loads(line)
                self.items[entry["key"]] = entry["answer"]

    def call(self, model: str, system: str, user: str, schema: dict, max_tokens: int) -> dict:
        key = hashlib.sha256(json.dumps([model, system, user, schema]).encode("utf-8")).hexdigest()
        if key not in self.items:
            self.items[key] = llm.chat(system, user, schema, max_tokens)
            with open(self.path, "a", encoding="utf-8") as handle:
                handle.write(json.dumps({"key": key, "answer": self.items[key]},
                                        ensure_ascii=False) + "\n")
        return self.items[key]


def squeeze(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip().lower()


def nace_divisions() -> dict[str, str]:
    doc = json.loads((ROOT / "data" / "raw" / "hsw_n2_02_eu27.json").read_text(encoding="utf-8"))
    labels = doc["dimension"]["nace_r2"]["category"]["label"]
    return {code: label for code, label in labels.items() if re.match(r"^[A-U]\d\d$", code)}


# ---------------------------------------------------------------- task "known"

KNOWN_SYSTEM = (
    "Du liest Seiten aus einem Bericht nach dem deutschen Lieferkettensorgfaltspflichtengesetz. "
    "Der Bericht enthält die Frage \"Welche Risiken wurden im Rahmen der Risikoanalyse(n) ... "
    "ermittelt?\" und darunter eine Liste von Risiken. Gib für den genannten Bereich an, welche "
    "Risiken in dieser Liste stehen. Nenne nur Risiken, die unter genau dieser Frage stehen."
)


def task_known(folder: Path, cache: Cache, model: str) -> None:
    schema = {"type": "object", "additionalProperties": False, "required": ["risks"],
              "properties": {"risks": {"type": "array",
                                       "items": {"type": "string", "enum": list(RISK_NAMES)}}}}
    names = "\n".join(f"- {code}: {name}" for code, name in RISK_NAMES.items())
    rows = [["report", "scope", "rules", "model", "missed_by_model", "added_by_model"]]
    tp = fp = fn = 0
    exact = total = 0
    for entry in csv.DictReader(open(HERE / "corpus.csv", encoding="utf-8")):
        path = folder / f"{entry['id']}.pages.json"
        if not path.exists():
            continue
        pages = json.loads(path.read_text(encoding="utf-8"))
        report = bafa.parse(pages)
        doc = bafa.Text(pages)
        for match in bafa.IDENTIFIED.finditer(doc.text):
            scope = bafa.scope_of(match)
            truth = set(report.identified.get(scope, {}))
            first = doc.page(match.start())
            last = doc.page(bafa.block_end(doc.text, match.end()))
            raw = "\n".join(pages[first - 1:last])
            user = (f"Mögliche Risiken (Code: Name):\n{names}\n\nBereich: {SCOPE_TEXT[scope]}\n\n"
                    f"Seiten des Berichts:\n{raw}")
            answer = set(cache.call(model, KNOWN_SYSTEM, user, schema, 300)["risks"])
            tp += len(truth & answer)
            fp += len(answer - truth)
            fn += len(truth - answer)
            total += 1
            exact += truth == answer
            rows.append([entry["id"], scope, len(truth), len(answer),
                         " ".join(sorted(truth - answer)), " ".join(sorted(answer - truth))])
            print(entry["id"], scope, "ok" if truth == answer else "DIFFERENT", flush=True)
    with open(ROOT / "results" / "ai_known_answer.csv", "w", newline="", encoding="utf-8") as h:
        csv.writer(h).writerows(rows)
    summary = {"model": model, "lists": total, "lists_identical": exact, "risks_by_rules": tp + fn,
               "model_correct": tp, "model_missed": fn, "model_added": fp,
               "precision": round(tp / (tp + fp), 3) if tp + fp else None,
               "recall": round(tp / (tp + fn), 3) if tp + fn else None}
    (ROOT / "results" / "ai_known_answer.json").write_text(json.dumps(summary, indent=1),
                                                           encoding="utf-8")
    print(summary)


# ----------------------------------------------------------------- task "free"

FREE_SYSTEM = {
    "de": ("Du liest die Beschreibung eines Risikos aus einem Bericht nach dem deutschen "
           "Lieferkettensorgfaltspflichtengesetz. Aufgabe:\n"
           "1. group: Nenne die Zulieferergruppe, Branche, Warengruppe, den Rohstoff oder die "
           "Tätigkeit, mit der das Unternehmen das Risiko verbindet. Kopiere die Wörter exakt aus "
           "dem Text. Wenn der Text keine nennt, gib einen leeren Text an.\n"
           "2. nace: Wähle die NACE-Abteilung, die zu group passt. Wenn group leer ist oder keine "
           "Abteilung passt, wähle NONE.\n"
           "3. concrete: true, wenn der Text ein bestimmtes Risiko beschreibt (was, wo oder bei "
           "wem). false, wenn der Text nur allgemein über das Vorgehen spricht.\n"
           "4. quote: Kopiere einen Satz oder Satzteil exakt aus dem Text, der deine Antwort "
           "belegt."),
    "en": ("You read the description of one risk from a report under the German Supply Chain "
           "Due Diligence Act. The description is in German. Task:\n"
           "1. group: Name the supplier group, industry, product group, raw material or activity "
           "that the company connects to the risk. Copy the words exactly from the text. If the "
           "text names none, give an empty text.\n"
           "2. nace: Select the NACE division that fits group. If group is empty or no division "
           "fits, select NONE.\n"
           "3. concrete: true if the text describes a specific risk (what, where or with whom). "
           "false if the text speaks only in general terms about the procedure.\n"
           "4. quote: Copy one sentence or part of a sentence exactly from the text that supports "
           "your answer."),
}


def task_free(folder: Path, cache: Cache, model: str) -> None:
    divisions = nace_divisions()
    schema = {"type": "object", "additionalProperties": False,
              "required": ["group", "nace", "concrete", "quote"],
              "properties": {"group": {"type": "string"},
                             "nace": {"type": "string", "enum": ["NONE"] + sorted(divisions)},
                             "concrete": {"type": "boolean"},
                             "quote": {"type": "string"}}}
    nace_list = "\n".join(f"{code} {label}" for code, label in sorted(divisions.items()))
    passages = [json.loads(line) for line in
                (folder / "passages.jsonl").read_text(encoding="utf-8").splitlines()]
    rows = [["report", "company", "company_nace", "scope", "risk", "page", "prompt", "group",
             "group_in_text", "nace", "concrete", "quote", "quote_in_text"]]
    stats = {lang: {"n": 0, "quote_ok": 0, "group_given": 0, "group_ok": 0, "concrete": 0}
             for lang in FREE_SYSTEM}
    agree = {"n": 0, "group_given": 0, "nace": 0, "concrete": 0, "all": 0}
    for number, passage in enumerate(passages, start=1):
        text = passage["text"]
        answers = {}
        for lang, system in FREE_SYSTEM.items():
            user = (f"NACE divisions:\n{nace_list}\n\nRisk: {RISK_NAMES[passage['risk']]}\n"
                    f"Scope: {SCOPE_TEXT[passage['scope']]}\n\nText:\n{text}")
            answer = cache.call(model, system, user, schema, 400)
            answers[lang] = answer
            quote_ok = bool(answer["quote"].strip()) and squeeze(answer["quote"]) in squeeze(text)
            group_ok = bool(answer["group"].strip()) and squeeze(answer["group"]) in squeeze(text)
            s = stats[lang]
            s["n"] += 1
            s["quote_ok"] += quote_ok
            s["group_given"] += bool(answer["group"].strip())
            s["group_ok"] += group_ok
            s["concrete"] += answer["concrete"]
            rows.append([passage["report"], passage["company"], passage["nace"], passage["scope"],
                         passage["risk"], passage["page"], lang, answer["group"],
                         "yes" if group_ok else "no", answer["nace"], answer["concrete"],
                         answer["quote"][:300], "yes" if quote_ok else "no"])
        a, b = answers["de"], answers["en"]
        same = [bool(a["group"].strip()) == bool(b["group"].strip()), a["nace"] == b["nace"],
                a["concrete"] == b["concrete"]]
        agree["n"] += 1
        agree["group_given"] += same[0]
        agree["nace"] += same[1]
        agree["concrete"] += same[2]
        agree["all"] += all(same)
        print(f"{number}/{len(passages)} {passage['report']} {passage['risk']}: "
              f"de={a['nace']} en={b['nace']}", flush=True)
    with open(ROOT / "results" / "ai_free_text.csv", "w", newline="", encoding="utf-8") as h:
        csv.writer(h).writerows(rows)
    summary = {"model": model, "passages": len(passages), "per_prompt": stats,
               "agreement_between_prompts": agree}
    (ROOT / "results" / "ai_free_text.json").write_text(json.dumps(summary, indent=1),
                                                        encoding="utf-8")
    print(summary)


def main() -> None:
    task, folder = sys.argv[1], Path(sys.argv[2])
    cache = Cache(folder / "llm_cache.jsonl")
    model = llm.model_name()
    (task_known if task == "known" else task_free)(folder, cache, model)


if __name__ == "__main__":
    main()
