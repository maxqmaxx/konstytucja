"""Integrity and regression checks for the constitutional atlas."""

import csv
import hashlib
import json
from pathlib import Path
import unittest
from urllib.parse import unquote, urlparse

from bs4 import BeautifulSoup

import atlas


class AtlasTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.entries = json.loads((atlas.OUT / "zapisy.json").read_text())
        cls.sources = json.loads((atlas.OUT / "normalized-sources.json").read_text())
        cls.html = BeautifulSoup((atlas.OUT / "ATLAS.html").read_text(), "lxml")

    def test_editorial_entries_and_rendered_cards_agree(self):
        self.assertEqual(len(self.entries), len(atlas.selections()))
        self.assertEqual(len(self.entries), len(self.html.select("article.card")))
        self.assertEqual(len(self.entries), len({r["id"] for r in self.entries}))
        self.assertEqual(set(atlas.CATEGORIES), {category for r in self.entries for category in r["categories"]})

    def test_source_hashes_and_local_source_lines(self):
        for entry in self.entries:
            with self.subTest(entry=entry["id"]):
                path = atlas.ROOT / entry["source_text_path"]
                body = path.read_bytes()
                self.assertEqual(hashlib.sha256(body).hexdigest(), entry["source_sha256"])
                self.assertGreater(entry["source_line"], 0)
                self.assertLessEqual(entry["source_line"], len(body.decode().splitlines()))

    def test_html_fragments_exist_in_archived_originals(self):
        for entry in self.entries:
            if not entry.get("original_source_html"):
                continue
            with self.subTest(entry=entry["id"]):
                body = (atlas.ROOT / entry["original_source_html"]).read_bytes()
                self.assertEqual(hashlib.sha256(body).hexdigest(), entry["original_source_html_sha256"])
                fragment = urlparse(entry["source_url"]).fragment
                self.assertTrue(fragment)
                self.assertIn(('id="' + fragment + '"').encode(), body)

    def test_local_download_links_exist(self):
        for node in self.html.select("a[href]"):
            target = urlparse(node["href"])
            if target.scheme or node["href"].startswith("#"):
                continue
            with self.subTest(link=node["href"]):
                self.assertTrue((atlas.OUT / unquote(target.path)).resolve().is_file())

    def test_complete_coverage_register_and_no_false_full_review_claim(self):
        with (atlas.OUT / "pokrycie.csv").open(encoding="utf-8-sig") as stream:
            rows = list(csv.DictReader(stream))
        self.assertEqual(len(rows), len(atlas.catalog()))
        selected = {r["document_id"] for r in self.entries}
        self.assertEqual(len(selected), sum(bool(row["selected_clause_ids"]) for row in rows))
        report = json.loads((atlas.OUT / "validation.json").read_text())
        self.assertFalse(report["full_semantic_review_of_all_documents"])
        self.assertFalse(report["source_versions_current_validity_verified"])

    def test_normalization_preserves_list_items_and_repairs_pdf_issue(self):
        bhutan = (atlas.ROOT / self.sources["constitute:en:Bhutan_2008"]["path"]).read_text()
        honduras = (atlas.ROOT / self.sources["constitute:en:Honduras_2013"]["path"]).read_text()
        self.assertIn("forest cover", bhutan)
        self.assertIn("Gross National Happiness", bhutan)
        self.assertIn("advocates its amendment", honduras)
        self.assertNotIn("PDF generated:", bhutan)

    def test_critical_exceptions_and_historical_scope_are_explicit(self):
        entries = {e["id"]: e for e in self.entries}
        self.assertIn("14A", entries["A011"]["provision"])
        self.assertIn("wyłączenie", entries["A011"]["meaning"])
        self.assertIn("wyraźnej zgody", entries["A012"]["meaning"])
        self.assertEqual(entries["A022"]["provision"], "art. 84C")
        self.assertEqual(entries["A023"]["provision"], "art. 84B")
        self.assertEqual(entries["A068"]["period"], "projekt")
        self.assertEqual(entries["A123"]["period"], "projekt")
        self.assertTrue(entries["A101"]["period"].startswith("historyczny"))


if __name__ == "__main__":
    unittest.main()
