#!/usr/bin/env python3
"""Reference data from the Comparative Constitutions Project for checking and filling the power model.

Elkins, Zachary and Tom Ginsburg. 2025. "Characteristics of National Constitutions, Version 5.0."
Comparative Constitutions Project. Expert coding, independent of our language-model extraction.
Melton, James and Tom Ginsburg. 2014. "Does De Jure Judicial Independence Really Matter?" Journal of Law and
Courts 2(2): replication data (de jure judicial independence index, 0-6).
Cheibub, José Antonio, Zachary Elkins and Tom Ginsburg. 2014. "Beyond Presidentialism and Parliamentarism." British
Journal of Political Science 44(3): replication data (regime type of 401 constitutional systems: 1 presidential,
2 parliamentary, 3 semi-presidential).

The CCP files carry no licence beyond a request to cite, so the extract (ccp_v5_2023.csv) stays in the private
repository; only derived comparisons are published.

  python3 analysis/wladza/ccp_ref.py CCPCNC_V5_SMALL.csv DJJI.txt BPP_REGIME.csv   # writes ccp_v5_2023.csv
  (BPP_REGIME.csv: cowcode,year,regime exported from ceg_bjps_replication_401.dta)
"""
from __future__ import annotations

import csv
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
OUT = HERE / "ccp_v5_2023.csv"
NAMES = {"Bolivia": "BO", "Brunei": "BN", "Cape Verde": "CV", "Cote d'Ivoire": "CI", "Czech Republic": "CZ",
         "Democratic Republic of the Congo": "CD", "Iran": "IR", "Kyrgyz Republic": "KG", "Laos": "LA", "Micronesia": "FM",
         "Moldova": "MD", "North Korea": "KP", "Russia": "RU", "Slovak Republic": "SK", "South Korea": "KR", "Taiwan": "TW",
         "Tanzania": "TZ", "Timor": "TL", "Turkey": "TR", "Venezuela": "VE", "Vietnam": "VN", "Yemen Arab Republic": "YE"}
COLS = (["execnum", "hoshog", "hoselect", "hogelect", "housenum", "legapp", "override", "overwho", "overpct", "legdiss", "em", "emdecl",
         "hosdec", "hogdec", "amndamaj", "judind", "judsal", "jrem", "conterm", "conlim", "jc"]
        + [f"leg_in_{i}" for i in (1, 2, 3)] + [f"amndprop_{i}" for i in (1, 2, 3)] + [f"challeg_{i}" for i in (1, 2, 3, 4, 5, 6, 8, 9)]
        + [f"cabdiss_{i}" for i in range(1, 7)] + [f"connom_{i}" for i in range(1, 8)] + [f"conap_{i}" for i in range(1, 8)]
        + [f"jremap_{i}" for i in range(1, 8)])


def iso_by_name():
    docs = json.loads((HERE.parent / "features" / "ccp_topics.json").read_text())["documents"]
    return {d["country"]: d["country_code"] for d in docs if d["status"] == "source_in_force"}


def main(ccp_csv: Path, djji_txt: Path | None, bpp_csv: Path | None = None):
    csv.field_size_limit(10 ** 9)
    ours = iso_by_name()
    djji = {}
    if djji_txt:
        for r in csv.DictReader(open(djji_txt, encoding="latin-1"), delimiter="\t"):
            if r["djji_ji"] not in ("", "."):
                cur = djji.get(r["cowcode"])
                if cur is None or int(r["year"]) > int(cur["year"]):
                    djji[r["cowcode"]] = r
    bpp = {(r["cowcode"], r["year"]): r["regime"] for r in csv.DictReader(open(bpp_csv))} if bpp_csv else {}
    rows = []
    for r in csv.DictReader(open(ccp_csv, encoding="latin-1")):
        if r["year"] != "2023":
            continue
        code = ours.get(r["country"]) or NAMES.get(r["country"])
        if not code:
            continue
        d = djji.get(r["cowcode"])
        same = d is not None and d["systyear"] == r["systyear"]  # DJJI coded the same constitution
        rows.append({"kod": code, "country": r["country"], "cowcode": r["cowcode"], "systyear": r["systyear"], "evntyear": r["evntyear"],
                     **{c: r.get(c, "") for c in COLS},
                     "djji_ji": d["djji_ji"] if same else "", "djji_year": d["year"] if same else "",
                     "bpp_regime": bpp.get((r["cowcode"], r["systyear"]), "")})  # same constitution: system year matches
    with open(OUT, "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(sorted(rows, key=lambda x: x["kod"]))
    print(json.dumps({"countries": len(rows), "djji_same_constitution": sum(1 for x in rows if x["djji_ji"]),
                      "bpp_same_constitution": sum(1 for x in rows if x["bpp_regime"])}))


def load():
    """kod -> row of the extract (empty dict if the extract is absent, e.g. in the public repository)."""
    if not OUT.exists():
        return {}
    return {r["kod"]: r for r in csv.DictReader(open(OUT, encoding="utf-8"))}


if __name__ == "__main__":
    main(Path(sys.argv[1]), Path(sys.argv[2]) if len(sys.argv) > 2 else None, Path(sys.argv[3]) if len(sys.argv) > 3 else None)
