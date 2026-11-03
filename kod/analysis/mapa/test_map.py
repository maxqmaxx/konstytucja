"""Consistency of the world map with the CCP prevalence tables."""

import csv
import json
from pathlib import Path
import unittest

from bs4 import BeautifulSoup

HERE = Path(__file__).resolve().parent
FEATURES = HERE.parent / "features"


class MapTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.soup = BeautifulSoup((HERE / "index.html").read_text(), "lxml")
        cls.data = json.loads(cls.soup.select_one("#map-data").string)
        cls.prev = {r["topic"]: r for r in csv.DictReader(open(FEATURES / "prevalence.csv", encoding="utf-8"))}

    def test_every_sample_country_is_drawn(self):
        drawn = {n["data-code"] for n in self.soup.select("#map [data-code]") if n["data-code"]}
        self.assertEqual(set(self.data["countries"]) - drawn, set())
        self.assertEqual(len(self.data["countries"]), self.data["sample"])

    def test_counts_match_prevalence_table(self):
        for index, (key, label, en, count, eu) in enumerate(self.data["topics"]):
            have = sum(str(index) in c["topics"] for c in self.data["countries"].values())
            self.assertEqual(have, int(self.prev[key]["count"]), key)
            self.assertEqual(eu, int(self.prev[key]["count_eu27"]), key)
            self.assertTrue(label and label != en or key in {"radio"}, key)

    def test_poland(self):
        pl = self.data["countries"]["PL"]
        idx = {t[0]: i for i, t in enumerate(self.data["topics"])}
        self.assertNotIn(str(idx["unamend"]), pl["topics"])
        self.assertEqual(pl["topics"][str(idx["hosterml"])][0], "art. 127")
        self.assertTrue(pl["eu"])

    def test_nav_links(self):
        hrefs = [a["href"] for a in self.soup.select(".site-nav a")]
        self.assertEqual(hrefs, ["../ATLAS.html", "index.html", "../rp/index.html", "../problemy/index.html", "../tematy/index.html", "../panstwa/index.html", "../ATLAS.html", "../polska/index.html", "../wizualizacje/index.html"])


if __name__ == "__main__":
    unittest.main()
