"""Every '+ Do teczki' marker carries valid metadata with a citation, and ids are unique per page."""

import json
from pathlib import Path
import unittest

from bs4 import BeautifulSoup

ANALYSIS = Path(__file__).resolve().parents[1]
PAGES = ["rp/index.html", "tematy/unamend.html", "tematy/hosterml.html", "polska/index.html"]


class TeczkaTests(unittest.TestCase):
    def test_markers(self):
        for rel in PAGES:
            soup = BeautifulSoup((ANALYSIS / rel).read_text(), "lxml")
            self.assertTrue(soup.select('script[src="../teczka/teczka.js"]'), rel)
            ids = []
            for el in soup.select("[data-teczka]"):
                meta = json.loads(el["data-teczka"])
                for field in ("id", "type", "title", "cite"):
                    self.assertTrue(meta.get(field), f"{rel}: {field} in {meta}")
                self.assertIn(meta["type"], {"rp", "wariant", "propozycja", "wynik", "atlas"})
                self.assertTrue(el.select("[data-teczka-text]") or el.has_attr("data-teczka-text"), f"{rel}: {meta['id']}")
                ids.append(meta["id"])
            self.assertEqual(len(ids), len(set(ids)), rel)
            self.assertTrue(ids, rel)

    def test_polish_citation(self):
        soup = BeautifulSoup((ANALYSIS / "rp/index.html").read_text(), "lxml")
        meta = json.loads(soup.select_one("#art-127")["data-teczka"])
        self.assertEqual(meta["title"], "Konstytucja RP, art. 127")
        self.assertIn("Dz.U. 1997 nr 78 poz. 483", meta["cite"])

    def test_search_page_wires_dynamic_results(self):
        html = (ANALYSIS / "panstwa/szukaj.html").read_text()
        self.assertIn("Teczka.attach(out)", html)
        self.assertIn("../teczka/teczka.js", html)


if __name__ == "__main__":
    unittest.main()
