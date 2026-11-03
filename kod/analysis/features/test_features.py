"""Integrity checks for CCP topic prevalence and the manual review of Polish gaps."""

import csv
import json
from pathlib import Path
import unittest

HERE = Path(__file__).resolve().parent


class FeatureTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.meta = json.loads((HERE / "ccp_topics.json").read_text())
        cls.prev = {r["topic"]: r for r in csv.DictReader(open(HERE / "prevalence.csv", encoding="utf-8"))}
        cls.review = {r["topic"]: r for r in csv.DictReader(open(HERE / "poland_gap_review.csv", encoding="utf-8"))}
        cls.evidence = json.loads((HERE / "proposals_evidence.json").read_text())

    def test_one_in_force_edition_per_country(self):
        docs = [d for d in self.meta["documents"] if d["status"] == "source_in_force"]
        codes = [d["country_code"] for d in docs]
        self.assertEqual(len(codes), len(set(codes)))
        self.assertEqual(len(docs), self.evidence["sample"]["documents"])
        self.assertTrue(all(d["tagged_sections"] > 0 for d in self.meta["documents"]))

    def test_known_facts_about_poland(self):
        self.assertEqual(self.prev["unamend"]["poland"], "0")
        self.assertEqual(self.prev["hosterml"]["poland"], "1")
        self.assertIn("Article 127", self.prev["hosterml"]["poland_articles"])
        self.assertEqual(self.prev["hogdlim"]["poland"], "1")
        self.assertIn("Article 158", self.prev["hogdlim"]["poland_articles"])
        self.assertEqual(self.prev["amend"]["count"], str(self.evidence["sample"]["documents"]))

    def test_review_covers_only_untagged_topics_with_reasons(self):
        allowed = {"luka", "luka_celowa", "inna_technika", "czesciowo", "artefakt", "nie_dotyczy"}
        for topic, row in self.review.items():
            self.assertEqual(self.prev[topic]["poland"], "0", topic)
            self.assertIn(row["verdict"], allowed)
            self.assertTrue(row["note"].strip())

    def test_every_untagged_topic_shown_on_cards_is_reviewed(self):
        for pid, items in self.evidence["proposals"].items():
            for item in items:
                if item["poland"] == "0":
                    self.assertIn(item["topic"], self.review, f"{pid} {item['topic']}")

    def test_shares_are_consistent(self):
        s = self.evidence["sample"]
        for r in self.prev.values():
            self.assertAlmostEqual(float(r["share"]), int(r["count"]) / s["documents"], places=3)
            self.assertAlmostEqual(float(r["share_eu27"]), int(r["count_eu27"]) / s["eu27"], places=3)


if __name__ == "__main__":
    unittest.main()
