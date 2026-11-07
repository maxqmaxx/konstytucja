"""Load extracted variants: latest record per (topic, country) with a verified quote, plus documented manual corrections (korekty.json)."""
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
FACETS = {k: v for k, v in json.loads((HERE / "facets.json").read_text()).items() if not k.startswith("_")}


def load(skip_methods=()) -> dict:
    """skip_methods: ignore corrections with these "metoda" values (e.g. "rozstrzygniecie" to see readings before adjudication)."""
    recs = {}
    path = HERE / "warianty.jsonl"
    if path.exists():
        for line in path.open(encoding="utf-8"):
            r = json.loads(line)
            if r["ok"] and r["cytat_ok"]:
                r["korekty"] = []
                recs[(r["topic"], r["country_code"])] = r
    for c in json.loads((HERE / "korekty.json").read_text()):
        if c.get("metoda") in skip_methods:
            continue
        r = recs.get((c["topic"], c["country_code"]))
        if r is not None and c["field"] in FACETS[c["topic"]]["fields"]:
            r["values"][c["field"]] = c["value"]
            r["korekty"].append(c)
    return recs
