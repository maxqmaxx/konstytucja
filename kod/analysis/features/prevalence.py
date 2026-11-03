"""Prevalence of CCP topics in constitutions in force, and Poland against the world.

Input: ``ccp_sections.csv`` and ``ccp_topics.json`` from ``ccp_topics.py``.
Sample: one Constitute English edition per country with publisher status
``source_in_force`` (188 documents, one per country).

Outputs:
- ``prevalence.csv``: topic, label, counts and shares (all / enacted 2000+ / EU-27),
  whether Poland's edition carries the tag, and Polish article labels.
- ``proposals_evidence.json``: for each Polish proposal (P01-P24), the mapped CCP
  topics with their prevalence and example countries.

A missing tag means "CCP coders did not attach this topic", not "the constitution
is silent". Every Polish gap that is shown to readers must be checked by hand
(see ``poland_gap_review.csv``).
"""
from __future__ import annotations

import csv
import json
from collections import defaultdict
from pathlib import Path

from babel import Locale

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]

EU27 = {"AT", "BE", "BG", "HR", "CY", "CZ", "DK", "EE", "FI", "FR", "DE", "GR", "HU", "IE", "IT",
        "LV", "LT", "LU", "MT", "NL", "PL", "PT", "RO", "SK", "SI", "ES", "SE"}

# Proposal -> CCP topics that measure the same mechanism (or its closest coded proxy).
# "proxy": the CCP topic is broader than the proposal; prevalence is an upper bound.
PROPOSAL_TOPICS = {
    "P01": [("unamend", "direct")],
    "P02": [("dignity", "direct"), ("binding", "proxy")],
    "P03": [("amparo", "direct")],
    "P04": [("jc", "direct"), ("judind", "direct"), ("judsal", "direct"), ("conrem", "proxy")],
    "P05": [("em", "proxy")],
    "P06": [("hosterml", "direct")],
    "P07": [("hogdlim", "proxy")],
    "P08": [("sub", "proxy"), ("mun", "proxy")],
    "P09": [("balbudgt", "proxy")],
    "P10": [("science", "proxy"), ("scifree", "direct"), ("acfree", "proxy")],
    "P11": [("resrce", "direct")],
    "P13": [("privacy", "proxy")],
    "P14": [("infoacc", "direct")],
    "P15": [("env", "proxy")],
    "P16": [("water", "direct")],
    "P17": [("standliv", "proxy"), ("shelter", "proxy"), ("health", "proxy")],
    "P18": [("equalgr9", "direct")],
    "P19": [("initiat", "proxy")],
    "P20": [("referen", "proxy")],
    "P23": [("civil", "direct"), ("assets", "proxy")],
    "P24": [("hospow", "proxy"), ("hogpow", "proxy")],
}
UNMAPPED = {"P12": "Brak tematu CCP dla raportu o dobrostanie.",
            "P21": "Brak tematu CCP dla budżetu partycypacyjnego.",
            "P22": "Brak tematu CCP dla ciągłości państwa po utracie infrastruktury."}


def year(value):
    try:
        return int(str(value)[:4])
    except (TypeError, ValueError):
        return None


def main() -> int:
    meta = json.loads((HERE / "ccp_topics.json").read_text())
    docs = {d["id"]: d for d in meta["documents"] if d["status"] == "source_in_force"}
    by_country = defaultdict(list)
    for d in docs.values():
        by_country[d["country_code"]].append(d["id"])
    dup = {k: v for k, v in by_country.items() if len(v) > 1}
    if dup:
        raise SystemExit(f"more than one in-force edition per country: {dup}")
    poland = by_country["PL"][0]
    recent = {i for i, d in docs.items() if (year(d["year_enacted"]) or 0) >= 2000}
    eu = {i for i, d in docs.items() if d["country_code"] in EU27}

    has = defaultdict(set)
    pl_articles = defaultdict(list)
    for row in csv.DictReader(open(HERE / "ccp_sections.csv", encoding="utf-8")):
        if row["doc_id"] not in docs:
            continue
        has[row["topic"]].add(row["doc_id"])
        if row["doc_id"] == poland and row["article"] not in pl_articles[row["topic"]]:
            pl_articles[row["topic"]].append(row["article"])

    n, nr, ne = len(docs), len(recent), len(eu)
    rows = []
    for topic, label in meta["topics"].items():
        ids = has[topic]
        rows.append({
            "topic": topic, "label": label,
            "count": len(ids), "share": round(len(ids) / n, 4),
            "count_2000plus": len(ids & recent), "share_2000plus": round(len(ids & recent) / nr, 4),
            "count_eu27": len(ids & eu), "share_eu27": round(len(ids & eu) / ne, 4),
            "poland": int(poland in ids), "poland_articles": "; ".join(pl_articles[topic]),
        })
    rows.sort(key=lambda r: (-r["share"], r["topic"]))
    with open(HERE / "prevalence.csv", "w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)

    index = {r["topic"]: r for r in rows}
    territories = Locale("pl").territories
    names = {d["id"]: territories.get(d["country_code"], d["country"]) for d in docs.values()}
    evidence = {}
    for pid, topics in PROPOSAL_TOPICS.items():
        evidence[pid] = []
        for topic, kind in topics:
            r = index[topic]
            examples = sorted(names[i] for i in has[topic] & eu)[:8] or sorted(names[i] for i in has[topic])[:8]
            evidence[pid].append({**r, "match": kind, "examples": examples})
    out = {
        "sample": {"documents": n, "enacted_2000plus": nr, "eu27": ne, "poland_doc": poland,
                   "definition": "Constitute EN, status source_in_force, jedna edycja na państwo"},
        "caveat": "Brak tagu CCP nie dowodzi braku przepisu. Temat 'proxy' jest szerszy niż propozycja.",
        "proposals": evidence, "unmapped": UNMAPPED,
    }
    (HERE / "proposals_evidence.json").write_text(json.dumps(out, ensure_ascii=False, indent=1))
    print(json.dumps({"documents": n, "recent": nr, "eu27": ne, "topics": len(rows),
                      "poland_topics": sum(r["poland"] for r in rows)}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
