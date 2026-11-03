"""Regression checks for archive integrity and source metadata handling."""

import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import collect


class ArchiveTests(unittest.TestCase):
    def test_pdf_error_response_is_rejected(self):
        with self.assertRaises(ValueError):
            collect.validate_body(b"<html><body>Server error</body></html>", "pdf")

    def test_html_challenge_is_rejected(self):
        with self.assertRaises(ValueError):
            collect.validate_body(b"<html><title>Just a moment...</title>" + b"x" * 400, "html")

    def test_source_country_variants_resolve(self):
        for name, expected in [("United Kingdom of Great Britain and Northern Ireland  the", "GB"), ("Iran Islamic Rep of ", "IR"), ("Republic of Korea  the", "KR"), ("Lao People s Democratic Republic  the", "LA"), ("Congo the", "CG")]:
            with self.subTest(name=name):
                self.assertEqual(collect.country_code(name), expected)

    def test_constitute_navigation_is_not_document_text(self):
        body = b'<html><nav>Browse topics</nav><main id="constitution-content"><h1>Constitution</h1><p>Article 1. The Republic.</p><script>tracking()</script></main></html>'
        text = collect.html_text(body, "constitute")
        self.assertIn("Article 1", text)
        self.assertNotIn("Browse topics", text)
        self.assertNotIn("tracking", text)

    def test_resume_does_not_request_existing_verified_asset(self):
        with tempfile.TemporaryDirectory() as directory, patch.object(collect, "ROOT", Path(directory)):
            item = collect.record("example", "law-1997", "Poland", "Constitution", "pl", [{"url": "https://example.invalid/law.html", "format": "html"}])
            body = ("<html><title>Constitution</title><body>Article 1. " + "Legal text. " * 100 + "</body></html>").encode()
            with patch.object(collect, "get", return_value=(body, "text/html", item["source_url"])):
                first = collect.download_record(item)
            with patch.object(collect, "get", side_effect=AssertionError("Unexpected network request")):
                second = collect.download_record(item)
            self.assertEqual(first["assets"], second["assets"])
            self.assertEqual(second["download_status"], "complete")

    def test_un_baseline_counts_members_and_observers(self):
        with tempfile.TemporaryDirectory() as directory, patch.object(collect, "ROOT", Path(directory)):
            collect.save_json(collect.ROOT / "metadata/manifest.json", [])
            collect.report(True)
            report = json.loads((collect.ROOT / "reports/coverage.json").read_text())
            self.assertEqual(report["baseline_count"], 195)
            self.assertEqual(report["covered"], 0)

    def test_verify_detects_tampered_document(self):
        with tempfile.TemporaryDirectory() as directory, patch.object(collect, "ROOT", Path(directory)):
            item = collect.record("example", "law-1997", "Poland", "Constitution", "pl", [{"url": "https://example.invalid/law.html", "format": "html"}])
            body = ("<html><title>Constitution</title><body>Article 1. " + "Legal text. " * 100 + "</body></html>").encode()
            collect.save_json(collect.ROOT / "metadata/manifest.json", [item])
            with patch.object(collect, "get", return_value=(body, "text/html", item["source_url"])):
                result = collect.download_record(item)
            path = collect.ROOT / result["assets"][0]["path"]
            path.write_bytes(b"modified")
            with self.assertRaises(SystemExit):
                collect.report(True)

    def test_wipo_extracts_only_requested_language(self):
        body = b'<html><div id="en"><div class="htmlView">English law</div></div><div id="fr"><div class="htmlView">French law</div></div></html>'
        text = collect.html_text(body, "wipo", '[id="en"] .htmlView')
        self.assertEqual(text.strip(), "English law")


if __name__ == "__main__":
    unittest.main()
