"""Country pages, comparison view and full-text query handling."""

import json
from pathlib import Path
import sqlite3
import sys
import tempfile
import unittest
from urllib.parse import unquote, urlparse

from bs4 import BeautifulSoup

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(ROOT / "analysis" / "szukaj"))
import search  # noqa: E402
from index import chunks  # noqa: E402


class PageTests(unittest.TestCase):
    def test_one_page_per_jurisdiction_and_index(self):
        codes = {json.loads(l)["country_code"] for l in open(ROOT / "catalog.jsonl", encoding="utf-8")}
        pages = {p.stem.upper() for p in HERE.glob("*.html") if "." not in p.stem} - {"INDEX", "POROWNAJ", "SZUKAJ"}
        self.assertEqual(pages, codes)
        index = BeautifulSoup((HERE / "index.html").read_text(), "lxml")
        self.assertEqual(len(index.select(".countries li")), len(codes))

    def test_local_links_resolve(self):
        for name in ["pl.html", "de.html", "fr.html", "dan.html", "index.html", "szukaj.html", "porownaj.html"]:
            soup = BeautifulSoup((HERE / name).read_text(), "lxml")
            for a in soup.select("a[href]"):
                url = urlparse(a["href"])
                if url.scheme or not url.path:
                    continue
                self.assertTrue((HERE / unquote(url.path)).resolve().exists(), f"{name}: {a['href']}")

    def test_poland_page(self):
        soup = BeautifulSoup((HERE / "pl.html").read_text(), "lxml")
        self.assertEqual(soup.h1.text, "Polska")
        self.assertIn("Konstytucja z dnia 2 kwietnia 1997 r.", soup.text)
        self.assertTrue(soup.select('a[href="../polska/index.html#p09"]'))

    def test_comparison_data(self):
        soup = BeautifulSoup((HERE / "porownaj.html").read_text(), "lxml")
        data = json.loads(soup.select_one("#data").string)
        self.assertEqual(len(data["countries"]), 188)
        self.assertEqual(len(data["topics"]), 331)


class QueryTests(unittest.TestCase):
    def test_query_is_quoted_and_safe(self):
        self.assertEqual(search.fts_query('stan "wyjątkowy rząd" konstytuc*'), '"stan" "wyjątkowy rząd" "konstytuc"*')
        self.assertEqual(search.fts_query("a OR b NEAR(c) col:x -y"), '"a" "OR" "b" "NEAR c" "col x" "y"')
        self.assertEqual(search.fts_query("ab*"), '"ab"')
        for bad in ["", "   ", '"" ***', "\x00"]:
            with self.assertRaises(search.QueryError):
                search.fts_query(bad)
        with self.assertRaises(search.QueryError):
            search.fts_query(" ".join(f"w{i}" for i in range(9)))

    def test_search_on_small_index(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "t.sqlite"
            db = sqlite3.connect(path)
            db.executescript("""CREATE TABLE docs(id, country_code, country, title, language, provider, status, year, text_path, original);
                CREATE VIRTUAL TABLE chunks USING fts5(body, doc UNINDEXED, line UNINDEXED, tokenize='unicode61 remove_diacritics 2');""")
            db.execute("INSERT INTO docs VALUES ('x','PL','Polska','Konstytucja','pl','eli-sejm','source_in_force','1997','a.txt','a.pdf')")
            text = "Art. 228\nW sytuacjach szczególnych zagrożeń może zostać wprowadzony stan wyjątkowy.\n\nArt. 229 inny tekst " + "x " * 80
            for line, body in chunks(text):
                db.execute("INSERT INTO chunks VALUES (?,?,?)", (body, 1, line))
            db.commit(); db.close()
            out = search.search({"q": "wyjatkowy"}, path)
            self.assertEqual(out["matching_documents"], 1)
            self.assertIn("\x02wyjątkowy\x03", out["results"][0]["hits"][0]["snippet"])
            self.assertEqual(search.search({"q": "wyjątkowy", "lang": "en"}, path)["matching_documents"], 0)
            with self.assertRaises(search.QueryError):
                search.search({"q": "x", "lang": "pl'; DROP"}, path)


if __name__ == "__main__":
    unittest.main()
