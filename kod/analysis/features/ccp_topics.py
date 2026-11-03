"""Extract Comparative Constitutions Project topic tags from saved Constitute HTML.

Constitute annotates each section of its English editions with expert-coded CCP
topics (``<span class="topic" data-topic="KEY">Label</span>``). This script turns
those annotations into a long table: one row per (document, topic, section).

Outputs (in this directory):
- ``ccp_sections.csv``: document x topic x section, with article label and text.
- ``ccp_topics.json``: topic key -> label, plus per-document metadata.

Prevalence is computed separately (``prevalence.py``). No network access.
Run from the project root: ``python3 analysis/features/ccp_topics.py``.
"""
from __future__ import annotations

import csv
import hashlib
import json
import re
import sys
from pathlib import Path

from bs4 import BeautifulSoup

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent
ARTICLE_RE = re.compile(r"^\s*(article|art\.?|section|amendment|chapter|part|title|preamble)\b", re.I)


def records():
    with open(ROOT / "catalog.jsonl", encoding="utf-8") as fh:
        for line in fh:
            rec = json.loads(line)
            if rec["provider"] != "constitute" or rec["language"] != "en":
                continue
            html = [a for a in rec.get("assets") or [] if a["path"].endswith(".html")]
            if html:
                yield rec, ROOT / html[0]["path"], html[0]["sha256"]


def clean(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


def parse(path: Path, limit: int | None = 1500, include_untagged: bool = False):
    """Tagged sections (one row per topic). With include_untagged, also untagged sections (topic None), for full-article context."""
    soup = BeautifulSoup(path.read_text(encoding="utf-8", errors="replace"), "lxml")
    article = "preamble"
    rows = []
    # Walk in document order; headings update the current article label.
    for node in soup.find_all(["h1", "h2", "h3", "h4", "h5", "h6", "div", "li", "p"]):
        if node.name.startswith("h"):
            label = clean(node.get_text(" "))
            if ARTICLE_RE.match(label) and len(label) < 80:
                article = label
            continue
        if not node.get("data-id", "").startswith("section/"):
            continue
        topic_box = node.find("div", class_="section-topic", recursive=False)
        spans = topic_box.find_all("span", class_="topic") if topic_box is not None else []
        if not spans and not include_untagged:
            continue
        # Section text without the topic box and without nested tagged sections.
        copy = BeautifulSoup(str(node), "lxml").find(node.name)
        for box in copy.find_all("div", class_="section-topic"):
            box.decompose()
        heading = copy.find(re.compile("^h[1-6]$"))
        if heading is not None:
            label = clean(heading.get_text(" "))
            if ARTICLE_RE.match(label) and len(label) < 80:
                article = label
            heading.decompose()
        full = clean(copy.get_text(" "))
        for nested in copy.find_all(attrs={"data-id": re.compile("^section/")}):
            nested.decompose()
        # Tags on an article or chapter title carry no own text: fall back to the nested content.
        text = clean(copy.get_text(" ")) or full
        for span in spans or [None]:
            if span is None:
                own = clean(copy.get_text(" "))
                if own:
                    rows.append({"section_id": node["data-id"], "article": article, "topic": None, "topic_label": "", "text": own})
                continue
            rows.append({
                "section_id": node["data-id"],
                "article": article,
                "topic": span["data-topic"],
                "topic_label": clean(span.get_text(" ")),
                "text": text[:limit] if limit else text,
            })
    return rows


def main() -> int:
    topics: dict[str, str] = {}
    docs = []
    out_rows = []
    for rec, path, sha in records():
        if not path.exists():
            print(f"missing {path}", file=sys.stderr)
            continue
        if hashlib.sha256(path.read_bytes()).hexdigest() != sha:
            print(f"sha mismatch {path}", file=sys.stderr)
            return 1
        rows = parse(path)
        docs.append({
            "id": rec["id"], "country_code": rec["country_code"], "country": rec["country"],
            "title": rec["title"], "status": rec["status"], "year_enacted": rec["year_enacted"],
            "year_revised": rec["year_revised"], "html": str(path.relative_to(ROOT)), "html_sha256": sha,
            "tagged_sections": len({r["section_id"] for r in rows}), "topics": len({r["topic"] for r in rows}),
        })
        for r in rows:
            topics.setdefault(r["topic"], r["topic_label"])
            out_rows.append({"doc_id": rec["id"], "country_code": rec["country_code"], **r})
    with open(HERE / "ccp_sections.csv", "w", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=["doc_id", "country_code", "section_id", "article", "topic", "topic_label", "text"])
        writer.writeheader()
        writer.writerows(out_rows)
    (HERE / "ccp_topics.json").write_text(json.dumps(
        {"source": "Constitute Project HTML topic annotations (Comparative Constitutions Project coding)",
         "topics": dict(sorted(topics.items())), "documents": docs}, ensure_ascii=False, indent=1))
    untagged = [d["id"] for d in docs if d["tagged_sections"] == 0]
    print(json.dumps({"documents": len(docs), "rows": len(out_rows), "topics": len(topics), "untagged": untagged[:10], "untagged_n": len(untagged)}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
