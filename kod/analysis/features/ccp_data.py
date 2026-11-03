"""Shared loader for CCP topic data used by the map, country pages and comparison view."""
from __future__ import annotations

import csv
import json
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path

FEATURES = Path(__file__).resolve().parent


@dataclass
class CcpData:
    labels: dict          # topic key -> Polish label
    topics: dict          # topic key -> CCP English label
    docs: dict            # in-force doc id -> document metadata
    by_code: dict         # country code -> in-force document metadata
    prevalence: dict      # topic key -> prevalence row
    topic_keys: list      # topic keys sorted by Polish label
    tindex: dict          # topic key -> index in topic_keys
    sections: dict        # country code -> {topic index: [article label, section number]}

    def topic_rows(self):
        return [[k, self.labels[k], self.topics[k], int(self.prevalence[k]["count"]), int(self.prevalence[k]["count_eu27"])]
                for k in self.topic_keys]


def load() -> CcpData:
    labels = json.loads((FEATURES / "topic_labels_pl.json").read_text())
    meta = json.loads((FEATURES / "ccp_topics.json").read_text())
    docs = {d["id"]: d for d in meta["documents"] if d["status"] == "source_in_force"}
    by_code = {d["country_code"]: d for d in docs.values()}
    prevalence = {r["topic"]: r for r in csv.DictReader(open(FEATURES / "prevalence.csv", encoding="utf-8"))}
    topic_keys = sorted(meta["topics"], key=lambda k: labels[k].lower())
    tindex = {k: i for i, k in enumerate(topic_keys)}
    sections: dict = defaultdict(dict)
    with open(FEATURES / "ccp_sections.csv", encoding="utf-8") as fh:
        for row in csv.DictReader(fh):
            if row["doc_id"] in docs:
                d = sections[docs[row["doc_id"]]["country_code"]]
                i = tindex[row["topic"]]
                if i not in d:
                    d[i] = [row["article"].replace("Article", "art.").replace("Section", "sekcja"),
                            row["section_id"].split("/")[-1]]
    return CcpData(labels, meta["topics"], docs, by_code, prevalence, topic_keys, tindex, dict(sections))
