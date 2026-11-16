import unittest

from ai.bafa import parse

# A synthetic report in the layout of the BAFA questionnaire. It is not text of a real company.
PAGES = [
    "Seite 1\nB. Risikoanalyse und Präventionsmaßnahmen\n"
    "Welche Risiken wurden im Rahmen der Risikoanalyse(n) im eigenen Geschäftsbereich\nermittelt?\n"
    "•\nVerbot von Kinderarbeit\nMissachtung von Arbeitsschutz und arbeitsbedingten Gesundheitsgefahren\n"
    "Welche Risiken wurden im Rahmen der Risikoanalyse(n) bei unmittelbaren Zulieferern ermittelt?\n"
    "Keine\n"
    "Wurden die im Berichtszeitraum ermittelten Risiken gewichtet?\nJa\n",
    "Seite 2\nB2. Präventionsmaßnahmen im eigenen Geschäftsbereich\n"
    "Welche Risiken wurden im Berichtszeitraum im eigenen Geschäftsbereich priorisiert?\n"
    "Missachtung von Arbeitsschutz und arbeitsbedingten Gesundheitsgefahren\nSonstige Verbote\n"
    "Missachtung von Arbeitsschutz und arbeitsbedingten Gesundheitsgefahren\n"
    "Um welches konkrete Risiko geht es?\n"
    "Unfälle im Lager. Das Thema \"Verbot von Kinderarbeit\" ist nicht betroffen.\n"
    "Wo tritt das Risiko auf?\nDeutschland\nPolen\n",
    "Seite 3\nSonstige Verbote\nUm welches konkrete Risiko geht es?\nArbeitszeit.\n"
    "Wo tritt das Risiko auf?\nSpanien\n"
    "Welche Präventionsmaßnahmen wurden umgesetzt?\nSchulungen\n"
    "Welche Risiken wurden für den Berichtszeitraum bei unmittelbaren Zulieferern priorisiert?\n"
    "Keine\nWelche Präventionsmaßnahmen wurden umgesetzt?\n",
]


class Bafa(unittest.TestCase):
    def setUp(self):
        self.report = parse(PAGES)

    def test_identified(self):
        self.assertEqual(set(self.report.identified["own"]), {"child_labour", "health_safety"})
        self.assertNotIn("direct", self.report.identified)
        self.assertEqual(self.report.answered["identified"], {"own", "direct"})

    def test_prioritised(self):
        items = {(p.scope, p.risk): p for p in self.report.prioritised}
        self.assertEqual(set(items), {("own", "health_safety"), ("own", "other")})
        safety = items[("own", "health_safety")]
        self.assertEqual(safety.countries, ["Deutschland", "Polen"])
        self.assertTrue(safety.description.startswith("Unfälle im Lager."))
        self.assertEqual(safety.page, 2)
        self.assertEqual(items[("own", "other")].countries, ["Spanien"])
        self.assertEqual(items[("own", "other")].page, 3)

    def test_none_stated(self):
        self.assertEqual(self.report.none_stated, {"direct"})


if __name__ == "__main__":
    unittest.main()
