#!/usr/bin/env python3
"""How far can the power model be trusted? Three checks, written to walidacja.json and wladza_walidacja_pola.csv.

1. Field agreement: our language-model readings vs the expert coding of the Comparative Constitutions Project
   (CCP v5, 2023), field by field, with Cohen's kappa. Also on the subset where both describe the same constitution
   year (CCP system year = Constitute year of enactment).
2. Convergent validity: our executive share (head of state + government) vs the CCP-style executive power index
   (0-7: initiate legislation, decrees, propose amendments, declare emergency, veto, challenge laws in court, dissolve
   parliament; Elkins, Ginsburg and Melton); our judicial-independence score vs the Melton-Ginsburg de jure index (0-6),
   only where it codes the same constitution. Spearman correlation with an approximate 95% interval.
3. Robustness: how the head-of-state ranking changes under alternative assumptions (model.VARIANTS).

Needs ccp_v5_2023.csv (see ccp_ref.py); without it only the robustness part is computed.
Usage: python3 analysis/wladza/walidacja.py
"""
from __future__ import annotations

import csv
import json
import math
import statistics
import sys
from collections import Counter
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "warianty"))
sys.path.insert(0, str(HERE))
import load as variants  # noqa: E402
import ccp_ref  # noqa: E402
import model  # noqa: E402

THRV = {"zwykla_lub_bezwzgledna": "1/2", "trzy_piate": "3/5", "dwie_trzecie": "2/3", "trzy_czwarte": "3/4", "weto_ostateczne": "absolutne"}
CCP_THR = {"1": "1/2", "2": "1/2", "3": "3/5", "4": "2/3", "5": "3/4"}


def yes(row, *cols):
    vals = [row.get(c, "") for c in cols]
    if all(v in ("", "99", "97", "96", "98", "90") for v in vals):
        return None
    return any(v == "1" for v in vals)


def ours(R, topic, code, field):
    r = R.get((topic, code))
    return None if r is None else r["values"].get(field)


def known(v):
    return v not in (None, "nie_wynika", "inny", "inne", [])


# (label, our value -> comparable or None, CCP row -> comparable or None)
FIELDS = [
    ("Liczba izb", lambda R, c: ours(R, "legapp", c, "izby") if ours(R, "legapp", c, "izby") in ("jedna", "dwie") else None,
     lambda x: {"2": "jedna", "3": "dwie"}.get(x.get("housenum"))),
    ("Głowa państwa może zawetować ustawę", lambda R, c: {"weto": True, "formalny_podpis": False, "tylko_sad": False}.get(ours(R, "legapp", c, "glowa_panstwa_ustawy")),
     lambda x: {"1": True, "3": True, "2": False, "4": False, "5": False}.get(x.get("legapp"))),
    ("Próg odrzucenia weta", lambda R, c: THRV.get(ours(R, "override", c, "prog_odrzucenia")), lambda x: CCP_THR.get(x.get("overpct"))),
    ("Głowa państwa może rozwiązać parlament", lambda R, c: ("glowa_panstwa" in ours(R, "legdiss", c, "kto_moze")) if known(ours(R, "legdiss", c, "kto_moze")) else None,
     lambda x: {"1": True, "3": True, "2": False, "4": False, "5": False}.get(x.get("legdiss"))),
    ("Kto ogłasza stan nadzwyczajny", lambda R, c: {"glowa_panstwa": "glowa", "rzad": "rzad", "parlament": "parlament"}.get(ours(R, "em", c, "kto_oglasza")),
     lambda x: {"1": "glowa", "2": "rzad", "4": "rzad", "5": "parlament", "6": "parlament", "7": "parlament"}.get(x.get("emdecl"))),
    ("Głowa państwa wydaje dekrety", lambda R, c: {"moc_ustawy": True, "wykonawcze": True}.get(ours(R, "hosdec", c, "moc")),
     lambda x: {"1": True, "2": False}.get(x.get("hosdec"))),
    ("Parlament wybiera sędziów TK", lambda R, c: ("parlament" in ours(R, "consel", c, "kto_wybiera")) if known(ours(R, "consel", c, "kto_wybiera")) else None,
     lambda x: yes(x, "connom_4", "connom_5", "conap_4", "conap_5")),
    ("Głowa państwa wybiera sędziów TK", lambda R, c: ("glowa_panstwa" in ours(R, "consel", c, "kto_wybiera")) if known(ours(R, "consel", c, "kto_wybiera")) else None,
     lambda x: yes(x, "connom_1", "conap_1")),
    ("Głowa państwa kieruje rządem", lambda R, c: {"glowa_panstwa": True, "odrebny_premier": False}.get(ours(R, "hogelect", c, "szef_rzadu")),
     lambda x: {"2": True, "3": False}.get(x.get("execnum"))),
    ("Parlament może odwołać rząd", lambda R, c: ("parlament" in ours(R, "cabdiss", c, "kto_odwoluje")) if ours(R, "cabdiss", c, "kto_odwoluje") is not None and (R.get(("cabdiss", c))) else None,
     lambda x: yes(x, "cabdiss_3", "cabdiss_5", "cabdiss_6", "hogadiss_2", "hogadiss_3", "hogadiss_4")),  # no-confidence is coded as HoG dismissal
    ("Głowa państwa może odwołać rząd", lambda R, c: ("glowa_panstwa" in ours(R, "cabdiss", c, "kto_odwoluje")) if R.get(("cabdiss", c)) else None,
     lambda x: yes(x, "hogpdiss_1") if x.get("execnum") == "3" else yes(x, "cabdiss_1")),  # dual executive: HoS starts the PM's dismissal
    ("Zmiana konstytucji wymaga większości kwalifikowanej", lambda R, c: {"zwykla_lub_bezwzgledna": False, "trzy_piate": True, "dwie_trzecie": True, "trzy_czwarte": True}.get(ours(R, "amend", c, "prog_parlament")),
     lambda x: {"1": True, "2": False}.get(x.get("amndamaj"))),
    ("Rząd ma inicjatywę ustawodawczą", lambda R, c: ("rzad" in ours(R, "legini", c, "kto_ma") or ("glowa_panstwa" in ours(R, "legini", c, "kto_ma") and ours(R, "hogelect", c, "szef_rzadu") == "glowa_panstwa"))
     if R.get(("legini", c)) else None,
     lambda x: yes(x, "leg_in_2", "leg_in_3") if x.get("execnum") != "2" else yes(x, "leg_in_1", "leg_in_2", "leg_in_3")),  # single executive: coded as HoS
]


def kappa(pairs):
    n = len(pairs)
    if not n:
        return None
    po = sum(a == b for a, b in pairs) / n
    ca, cb = Counter(a for a, _ in pairs), Counter(b for _, b in pairs)
    pe = sum(ca[k] * cb[k] for k in set(ca) | set(cb)) / n / n
    return None if pe >= 1 else round((po - pe) / (1 - pe), 3)


def ranks(xs):
    order = sorted(range(len(xs)), key=lambda i: xs[i])
    r = [0.0] * len(xs)
    i = 0
    while i < len(xs):
        j = i
        while j + 1 < len(xs) and xs[order[j + 1]] == xs[order[i]]:
            j += 1
        for k in range(i, j + 1):
            r[order[k]] = (i + j) / 2 + 1
        i = j + 1
    return r


def spearman(x, y):
    n = len(x)
    if n < 5:
        return None
    rx, ry = ranks(x), ranks(y)
    mx, my = statistics.fmean(rx), statistics.fmean(ry)
    num = sum((a - mx) * (b - my) for a, b in zip(rx, ry))
    den = math.sqrt(sum((a - mx) ** 2 for a in rx) * sum((b - my) ** 2 for b in ry))
    rho = num / den if den else 0.0
    z, se = math.atanh(max(min(rho, .9999), -.9999)), 1 / math.sqrt(n - 3)
    return {"rho": round(rho, 3), "n": n, "ci95": [round(math.tanh(z - 1.96 * se), 3), round(math.tanh(z + 1.96 * se), 3)]}


def exec_index(x):
    items = [yes(x, "leg_in_1", "leg_in_2", "leg_in_3"), (x.get("hosdec") == "1" or x.get("hogdec") == "1"),
             yes(x, "amndprop_1", "amndprop_2", "amndprop_3"), x.get("emdecl") in ("1", "2", "3", "4"),
             x.get("legapp") in ("1", "2", "3", "4"), yes(x, "challeg_1", "challeg_2", "challeg_3"), x.get("legdiss") in ("1", "2", "3", "4")]
    return sum(bool(i) for i in items)


def main():
    data = json.loads((HERE / "wladza.json").read_text())["countries"]
    ccp = ccp_ref.load()
    out = {"ccp": bool(ccp)}
    if ccp:
        R = variants.load()
        docs = {d["country_code"]: d for d in json.loads((HERE.parent / "features" / "ccp_topics.json").read_text())["documents"] if d["status"] == "source_in_force"}
        rows, diffs = [], []
        for label, f_ours, f_ccp in FIELDS:
            pairs, same = [], []
            for code, x in ccp.items():
                a, b = f_ours(R, code), f_ccp(x)
                if a is None or b is None:
                    continue
                pairs.append((a, b))
                if str(docs.get(code, {}).get("year_enacted")) == x["systyear"]:
                    same.append((a, b))
                if a != b:
                    diffs.append({"pole": label, "kod": code, "nasze": a, "ccp": b})
            agree = sum(a == b for a, b in pairs)
            rows.append({"pole": label, "n": len(pairs), "zgodne": agree, "zgodnosc": round(agree / len(pairs), 3) if pairs else None,
                         "kappa": kappa(pairs), "n_ta_sama_wersja": len(same),
                         "zgodnosc_ta_sama_wersja": round(sum(a == b for a, b in same) / len(same), 3) if same else None})
        out["pola"] = rows
        R0 = variants.load(skip_methods=("rozstrzygniecie",))  # readings before adjudicating disagreements with CCP
        p0 = [(f_ours(R0, c), f_ccp(x)) for _, f_ours, f_ccp in FIELDS for c, x in ccp.items()]
        p0 = [(a, b) for a, b in p0 if a is not None and b is not None]
        out["pola_przed_rozstrzygnieciem"] = {"n": len(p0), "zgodnosc": round(sum(a == b for a, b in p0) / len(p0), 3)}
        adj = [json.loads(line) for line in open(HERE / "rozstrzygniecia.jsonl", encoding="utf-8")] if (HERE / "rozstrzygniecia.jsonl").exists() else []
        K = json.loads((HERE.parent / "warianty" / "korekty.json").read_text())
        out["rozstrzygniecia"] = {"rozbieznosci": len(adj), "poprawki": sum(k.get("metoda") == "rozstrzygniecie" for k in K)}
        tot_n, tot_a = sum(r["n"] for r in rows), sum(r["zgodne"] for r in rows)
        out["pola_razem"] = {"n": tot_n, "zgodne": tot_a, "zgodnosc": round(tot_a / tot_n, 3)}
        out["roznice_pl"] = [d for d in diffs if d["kod"] == "PL"]
        with open(HERE / "wladza_walidacja_pola.csv", "w", newline="", encoding="utf-8") as fh:
            w = csv.DictWriter(fh, fieldnames=list(rows[0]))
            w.writeheader()
            w.writerows(rows)
        (HERE / "walidacja_roznice.json").write_text(json.dumps(diffs, ensure_ascii=False, indent=0), encoding="utf-8")  # private: review list

        # convergent validity
        ex, hs, idx, codes = [], [], [], []
        for code, m in data.items():
            if m["ranked"] and code in ccp:
                ex.append(m["profile"]["HS"] + m["profile"]["G"])
                hs.append(m["profile"]["HS"])
                idx.append(exec_index(ccp[code]))
                codes.append(code)
        out["wykonawcza"] = {"udzial_wykonawczej_vs_indeks": spearman(ex, idx), "udzial_glowy_vs_indeks": spearman(hs, idx),
                             "indeks_pl": exec_index(ccp["PL"]) if "PL" in ccp else None,
                             "srednia_indeksu_wg_typu": {t: round(statistics.fmean(exec_index(ccp[c]) for c in codes if data[c]["type"] == t), 2)
                                                        for t in sorted({data[c]["type"] for c in codes})}}
        # regime type vs Cheibub, Elkins and Ginsburg (2014), same constitution only
        grp = {"prezydencki": "prezydencki", "silna_glowa": "prezydencki", "polprezydencki": "polprezydencki", "parlamentarny": "parlamentarny"}
        bpp = {"1": "prezydencki", "2": "parlamentarny", "3": "polprezydencki"}
        pairs = [(grp.get(model.TYPE_GROUP.get(m["type"])), bpp[ccp[c]["bpp_regime"]]) for c, m in data.items()
                 if c in ccp and ccp[c].get("bpp_regime") in bpp and grp.get(model.TYPE_GROUP.get(m["type"]))]
        conf = Counter(pairs)
        out["typologia"] = {"n": len(pairs), "zgodnosc": round(sum(a == b for a, b in pairs) / len(pairs), 3) if pairs else None, "kappa": kappa(pairs),
                            "macierz": [[a, b, n] for (a, b), n in sorted(conf.items())],
                            "hs_wg_typu_cheibub": {t: round(statistics.fmean(data[c]["profile"]["HS"] for c in data if c in ccp and bpp.get(ccp[c].get("bpp_regime")) == t), 3)
                                                   for t in ("prezydencki", "polprezydencki", "parlamentarny")}}
        js, dj = [], []
        for code, m in data.items():
            if code in ccp and ccp[code].get("djji_ji") not in ("", None) and m["sady"]["score"] is not None:
                js.append(m["sady"]["score"])
                dj.append(float(ccp[code]["djji_ji"]))
        out["sady"] = {"indeks_vs_melton_ginsburg": spearman(js, dj), "djji_pl": ccp.get("PL", {}).get("djji_ji")}

    # robustness
    ranked = {k: m for k, m in data.items() if m.get("warianty")}
    base = {k: m["warianty"]["bazowy"]["HS"] for k, m in ranked.items()}
    rob = {}
    for v in model.VARIANTS:
        if v == "bazowy":
            continue
        ks = [k for k in ranked if ranked[k]["warianty"].get(v)]
        rob[v] = {"spearman_z_bazowym": spearman([base[k] for k in ks], [ranked[k]["warianty"][v]["HS"] for k in ks])}
    widths = [m["rank_range"][1] - m["rank_range"][0] for m in ranked.values()]
    out["wrazliwosc"] = {"warianty": rob, "mediana_rozpietosci_miejsca": statistics.median(widths),
                         "pl": {"miejsca": data["PL"]["rank_range"], "warianty": data["PL"]["warianty"]} if "PL" in data else None}
    (HERE / "walidacja.json").write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
    print(json.dumps({k: out[k] for k in ("pola_razem", "typologia", "wykonawcza", "sady") if k in out} | {"wrazliwosc": {k: v["spearman_z_bazowym"]["rho"] for k, v in rob.items()}}, ensure_ascii=False, indent=1))
    for r in out.get("pola", []):
        print(f'{r["pole"]:<55} n={r["n"]:<4} {r["zgodnosc"]}  kappa={r["kappa"]}  ta sama wersja: {r["zgodnosc_ta_sama_wersja"]} (n={r["n_ta_sama_wersja"]})')
    print("PL różnice:", out.get("roznice_pl"))


if __name__ == "__main__":
    main()
