"""Stage A: read the standard BAFA questionnaire fields of an LkSG report with rules. No AI.

A report in the BAFA format answers fixed questions with fixed risk names. For each report this
module returns:
  - the risks that the company identified, per scope (own operations, direct or indirect suppliers);
  - the risks that the company prioritised, per scope, with the company's description and the
    countries that the company names.
Each item keeps the page number, so a reader can find it in the report.
"""
from __future__ import annotations

import bisect
import re
from dataclasses import dataclass, field

# Risk names of the BAFA questionnaire. Key = code used in this repository.
RISKS = {
    "child_labour": r"Verbot\s+von\s+Kinderarbeit",
    "forced_labour": r"Verbot\s+von\s+Zwangsarbeit",
    "health_safety": r"Missachtung\s+von\s+Arbeitsschutz",
    "freedom_of_association": r"Missachtung\s+der\s+Koalitionsfreiheit",
    "discrimination": r"Verbot\s+der\s+Ungleichbehandlung",
    "adequate_wage": r"Verbot\s+des\s+Vorenthaltens\s+eines\s+angemessenen\s+Lohns",
    "environmental_harm": r"Zerstörung\s+der\s+natürlichen\s+Lebensgrundlage",
    "land_rights": r"Widerrechtliche\s+Verletzung\s+von\s+Landrechten",
    "security_forces": r"Verbot\s+der\s+Beauftragung\s+oder\s+Nutzung\s+privater",
    "mercury": r"Verbotene\s+Herstellung,\s+Einsatz\s+und/oder\s+Entsorgung\s+von\s+Quecksilber",
    "persistent_pollutants": r"Verbotene\s+Produktion\s+und/oder\s+Verwendung\s+von\s+Stoffen",
    "hazardous_waste": r"Verbotene\s+Ein-/Ausfuhr\s+gefährlicher\s+Abfälle",
    "other": r"Sonstige\s+Verbote",
}
RISK_RE = re.compile("|".join(f"(?P<{code}>{pattern})" for code, pattern in RISKS.items()))

SCOPES = {"im eigenen Geschäftsbereich": "own", "bei unmittelbaren Zulieferern": "direct",
          "bei mittelbaren Zulieferern": "indirect"}
SCOPE = r"(im\s+eigenen\s+Geschäftsbereich|bei\s+unmittelbaren\s+Zulieferern|bei\s+mittelbaren\s+Zulieferern)"
IDENTIFIED = re.compile(r"Welche\s+Risiken\s+wurden\s+im\s+Rahmen\s+der\s+Risikoanalyse\(n\)\s+"
                        + SCOPE + r"\s+ermittelt\?")
PRIORITISED = re.compile(r"Welche\s+Risiken\s+wurden\s+(?:im\s+Berichtszeitraum|für\s+den\s+"
                         r"Berichtszeitraum|aufgrund\s+der\s+anlassbezogenen\s+Risikoanalyse)\s+"
                         + SCOPE + r"\s+priorisiert\?")
NEXT_QUESTION = re.compile(r"\n(?:Welche|Wurden|Wurde|Beschreiben\s+Sie|Inwiefern|Begründen\s+Sie)\s")
WHICH = re.compile(r"Um\s+welches\s+konkrete\s+Risiko\s+geht\s+es\?")
WHERE = re.compile(r"Wo\s+tritt\s+das\s+Risiko\s+auf\?")
NONE = re.compile(r"^\s*Keine\s*$", re.M)
NOISE = re.compile(r"^\s*(?:[•▪]|Seite\s+\d+|[A-E]\d?\.\s.*)\s*$")


@dataclass
class Prioritised:
    scope: str
    risk: str
    page: int
    description: str = ""
    countries: list[str] = field(default_factory=list)


@dataclass
class Report:
    identified: dict[str, dict[str, int]]  # scope -> risk -> page
    prioritised: list[Prioritised]
    answered: dict[str, set[str]]          # "identified" / "prioritised" -> scopes with a question
    none_stated: set[str]                  # scopes where the company answered "Keine" (prioritised)


class Text:
    """Report text without page headers, with a page number for each position."""

    def __init__(self, pages: list[str]):
        parts, starts, numbers = [], [], []
        position = 0
        for number, page in enumerate(pages, start=1):
            lines = [line.rstrip() for line in page.splitlines() if not NOISE.match(line)]
            chunk = "\n".join(lines) + "\n"
            parts.append(chunk)
            starts.append(position)
            numbers.append(number)
            position += len(chunk)
        self.text = "".join(parts)
        self._starts, self._numbers = starts, numbers

    def page(self, position: int) -> int:
        return self._numbers[bisect.bisect_right(self._starts, position) - 1]


def scope_of(match: re.Match) -> str:
    return SCOPES[re.sub(r"\s+", " ", match.group(1))]


def block_end(text: str, start: int) -> int:
    nxt = NEXT_QUESTION.search(text, start)
    return nxt.start() if nxt else len(text)


def clean(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


def parse(pages: list[str]) -> Report:
    doc = Text(pages)
    text = doc.text
    report = Report({}, [], {"identified": set(), "prioritised": set()}, set())

    for match in IDENTIFIED.finditer(text):
        scope = scope_of(match)
        report.answered["identified"].add(scope)
        block_start = match.end()
        for risk in RISK_RE.finditer(text, block_start, block_end(text, block_start)):
            report.identified.setdefault(scope, {}).setdefault(risk.lastgroup, doc.page(risk.start()))

    seen = set()
    for match in PRIORITISED.finditer(text):
        scope = scope_of(match)
        report.answered["prioritised"].add(scope)
        start, end = match.end(), block_end(text, match.end())
        block = text[start:end]
        if not RISK_RE.search(block):
            if NONE.search(block):
                report.none_stated.add(scope)
            continue
        details = list(WHICH.finditer(block))
        if not details:  # the company lists the risks without a description
            for risk in RISK_RE.finditer(block):
                if (scope, risk.lastgroup) not in seen:
                    seen.add((scope, risk.lastgroup))
                    report.prioritised.append(
                        Prioritised(scope, risk.lastgroup, doc.page(start + risk.start())))
            continue
        # Layout: risk name, "Um welches konkrete Risiko geht es?", description,
        # "Wo tritt das Risiko auf?", country lines, next risk name, and so on.
        headings = []
        floor = 0
        for detail in details:
            names = list(RISK_RE.finditer(block, floor, detail.start()))
            headings.append(names[-1] if names else None)
            floor = detail.end()
        for index, detail in enumerate(details):
            heading = headings[index]
            stop = len(block)
            if index + 1 < len(details):
                nxt = headings[index + 1]
                stop = nxt.start() if nxt else details[index + 1].start()
            where = WHERE.search(block, detail.end(), stop)
            if where and index + 1 < len(details):
                # a risk name inside the description must not end the country list early
                names = list(RISK_RE.finditer(block, where.end(), details[index + 1].start()))
                stop = names[-1].start() if names else details[index + 1].start()
            if heading is None or (scope, heading.lastgroup) in seen:
                continue
            seen.add((scope, heading.lastgroup))
            item = Prioritised(scope, heading.lastgroup, doc.page(start + heading.start()))
            item.description = clean(block[detail.end(): where.start() if where else stop])
            if where:
                item.countries = [clean(line) for line in block[where.end():stop].splitlines()
                                  if clean(line)]
            report.prioritised.append(item)
    return report
