"""Check provenance and prevent misleading claims in the Polish adaptation view."""

import hashlib
import json
from pathlib import Path
import unittest
from urllib.parse import unquote, urlparse

from bs4 import BeautifulSoup

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]


class PolandViewTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.data = json.loads((HERE / "propozycje.json").read_text())
        cls.page = BeautifulSoup((HERE / "index.html").read_text(), "lxml")

    def test_editorial_scope_and_existing_polish_guarantees(self):
        items = {p["id"]: p for p in self.data["proposals"]}
        self.assertEqual(len(items), 24)
        self.assertEqual(len(self.page.select(".proposal")), 24)
        self.assertEqual(len(self.page.select(".avoid")), 8)
        self.assertEqual(sum(p["starter"] for p in items.values()), 6)
        self.assertEqual(items["P02"]["change"], "jest")
        self.assertEqual(items["P07"]["change"], "jest")
        self.assertIn("nie przyznaje", items["P19"]["poland"])
        self.assertIn("przepisach przejściowych", items["P06"]["poland"])
        self.assertIn("autorską", items["P13"]["implementation"])

    def test_every_inspiration_matches_the_archive_and_identifies_drafts(self):
        atlas = {e["id"]: e for e in json.loads((HERE.parent / "zapisy.json").read_text())}
        sources = [s for p in self.data["proposals"] for s in p["sources"]]
        sources += [s for p in self.data["avoid"] for s in p["source_entries"]]
        for source in sources:
            with self.subTest(source=source["id"]):
                self.assertEqual(source, atlas[source["id"]])
                path = ROOT / source["source_text_path"]
                self.assertEqual(hashlib.sha256(path.read_bytes()).hexdigest(), source["source_sha256"])
        self.assertEqual(atlas["A068"]["period"], "projekt")
        self.assertEqual(atlas["A069"]["period"], "projekt")
        self.assertEqual(atlas["A123"]["period"], "projekt")

    def test_every_local_link_and_html_fragment_exists(self):
        parsed = {HERE / "index.html": self.page}
        for node in self.page.select("a[href],script[src],link[href]"):
            href = node.get("href", node.get("src"))
            target = urlparse(href)
            if target.scheme:
                continue
            path = (HERE / unquote(target.path)).resolve() if target.path else HERE / "index.html"
            if path.is_dir():
                continue
            with self.subTest(link=href):
                self.assertTrue(path.is_file())
                if target.fragment and path.suffix == ".html":
                    if path not in parsed:
                        parsed[path] = BeautifulSoup(path.read_text(), "lxml")
                    self.assertIsNotNone(parsed[path].find(id=target.fragment))

    def test_polish_reference_is_official_consolidation_with_clear_limits(self):
        meta = json.loads((HERE / "sources/eli-metadata.json").read_text())
        self.assertEqual(meta["inForce"], "IN_FORCE")
        self.assertEqual({r["id"] for r in meta["references"]["Akty zmieniające"]}, {"DU/2006/1471", "DU/2009/946"})
        source = BeautifulSoup((HERE / "sources/konstytucja-rp.html").read_text(), "lxml")
        self.assertEqual(len(source.select("section[id^=art-]")), 243)
        self.assertIn("100 000", source.select_one("#art-118").get_text())
        self.assertIn("1/5", source.select_one("#art-235").get_text())
        validation = json.loads((HERE / "validation.json").read_text())
        self.assertFalse(validation["complete_legal_review"])
        self.assertFalse(validation["foreign_current_validity_verified"])


if __name__ == "__main__":
    unittest.main()
