"""Konstytucja RP on the world background and topic variant pages."""

import csv
from pathlib import Path
import re
import unittest
from urllib.parse import unquote, urlparse

from bs4 import BeautifulSoup

HERE = Path(__file__).resolve().parent
TOPICS = HERE.parent / "tematy"
FEATURES = HERE.parent / "features"


def soup(path):
    return BeautifulSoup(path.read_text(), "lxml")


class RpTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.rp = soup(HERE / "index.html")
        cls.prev = {r["topic"]: r for r in csv.DictReader(open(FEATURES / "prevalence.csv", encoding="utf-8"))}

    def test_all_articles_and_chapters(self):
        ids = [a["id"] for a in self.rp.select(".art")]
        self.assertEqual(ids[0], "preambula-tekst")
        self.assertEqual([int(i[4:]) for i in ids[1:]], list(range(1, 244)))
        self.assertEqual(len(self.rp.select(".chapter")), 14)
        self.assertIn("pięcioletnią kadencję", self.rp.select_one("#art-127 .text").text)

    def test_article_chips_match_tags(self):
        chips = {a["href"].split("/")[-1][:-5] for a in self.rp.select("#art-127 .chip")}
        self.assertIn("hosterml", chips)
        for key in chips:
            self.assertEqual(self.prev[key]["poland"], "1")

    def test_missing_boxes_use_reviewed_gaps(self):
        box = self.rp.select_one("#rozdzial-xii .missing")
        self.assertIn("Przepisy niezmienialne", box.text)
        self.assertIn("brak w Konstytucji RP", box.text)

    def test_topic_pages_counts(self):
        pages = {p.stem for p in TOPICS.glob("*.html")} - {"index"}
        self.assertEqual(pages, set(self.prev))
        for key in ["unamend", "hosterml", "water", "em", "god"]:
            page = soup(TOPICS / f"{key}.html")
            expected = int(self.prev[key]["count"]) - int(self.prev[key]["poland"])
            self.assertEqual(len(page.select(".variant")), expected, key)
            self.assertFalse(page.select('.variant[data-pl="1"]'), key)
        self.assertIn("brak w Konstytucji RP", soup(TOPICS / "unamend.html").select_one(".poland").text)
        self.assertIn("Art. 127", soup(TOPICS / "hosterml.html").select_one(".poland").text)

    def test_local_links_resolve(self):
        for path in [HERE / "index.html", TOPICS / "index.html", TOPICS / "unamend.html", TOPICS / "hosterml.html"]:
            for a in soup(path).select("a[href]"):
                url = urlparse(a["href"])
                if url.scheme or not url.path:
                    continue
                self.assertTrue((path.parent / unquote(url.path)).resolve().exists(), f"{path.name}: {a['href']}")


if __name__ == "__main__":
    unittest.main()


class TranslationIntegrationTests(unittest.TestCase):
    def test_problem_pages_exist(self):
        import json as _json
        vocab = _json.loads((HERE.parent / "tlumaczenia/slowniki.json").read_text())
        pages = {p.stem for p in (HERE.parent / "problemy").glob("*.html")} - {"index"}
        self.assertEqual(pages, set(vocab["problemy"]))

    def test_translations_only_when_checks_pass(self):
        import sys as _sys
        _sys.path.insert(0, str(HERE.parent / "tlumaczenia"))
        import store
        for k, r in store.load({}).items():
            self.fail("store must ignore records without a matching source text")
        for page_path in TOPICS.glob("*.html"):
            page = soup(page_path)
            for block in page.select(".variant-text"):
                if block.select_one(".mt"):
                    self.assertTrue(block.select_one("details.orig p[lang=en]"), page_path.name)
                    self.assertFalse(block.select_one(".mt-note"), page_path.name)
            break

    def test_filters_present(self):
        page = soup(TOPICS / "unamend.html")
        self.assertTrue(page.select_one("#sila") and page.select_one("#prob"))
        self.assertIn("przekład", page.select_one(".note").text.lower() + " ".join(n.text.lower() for n in page.select(".note")))
