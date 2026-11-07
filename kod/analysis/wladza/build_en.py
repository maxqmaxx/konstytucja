#!/usr/bin/env python3
"""English summary of the separation-of-powers analysis: analysis/wladza/en.html (site page) and summary_en.md.

All numbers come from wladza.json and walidacja.json. Usage: python3 analysis/wladza/build_en.py
"""
from __future__ import annotations

import html
import json
import re
import statistics
import sys
from collections import Counter
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "panstwa"))
from build import page  # noqa: E402
from babel import Locale  # noqa: E402

EN = Locale("en")
EU27 = {"AT", "BE", "BG", "HR", "CY", "CZ", "DK", "EE", "FI", "FR", "DE", "GR", "HU", "IE", "IT",
        "LV", "LT", "LU", "MT", "NL", "PL", "PT", "RO", "SK", "SI", "ES", "SE"}
ORDER = ["L1", "L2", "G", "HS", "P", "CC", "J"]
COLORS = {"L1": "#006858", "L2": "#5fa58f", "G": "#c49260", "HS": "#b4532a", "P": "#6c5a9e", "CC": "#41525e", "J": "#8c9aa3"}
ORG = {"L1": "First chamber", "L2": "Second chamber", "G": "Government", "HS": "Head of state", "P": "The people", "CC": "Constitutional court", "J": "Judiciary"}
DEC = {"ustawa": "Ordinary law", "budzet": "Budget", "konstytucja": "Constitutional amendment", "powolanie_rzadu": "Appointing the head of government",
       "odwolanie_rzadu": "Removing the government", "rozwiazanie": "Dissolving parliament", "sedziowie_tk": "Constitutional judges",
       "stan_nadzwyczajny": "State of emergency", "wojna": "War and troops", "ratyfikacja": "Treaty ratification", "usuniecie_glowy": "Removing the head of state"}
TYPES = {"prezydencki": "Presidential", "prezydent_z_parlamentu": "President elected by parliament heads government",
         "polprezydencki_premierowski": "Semi-presidential, premier-presidential", "polprezydencki_prezydencko_parlamentarny": "Semi-presidential, president-parliamentary",
         "parlamentarny": "Parliamentary republic", "monarchia_parlamentarna": "Parliamentary monarchy",
         "podwojna_odpowiedzialnosc": "Government answers to parliament and an indirectly chosen head of state",
         "rzad_glowy_panstwa": "Government answers only to the head of state", "nieustalony": "Not determinable from the text"}
INST = {"tk": "Constitutional court", "krs": "Judicial council", "rpo": "Ombudsman", "bank": "Central bank", "prokurator": "Prosecutor general",
        "wybory": "Electoral body", "konstytucja": "Amending the constitution"}
LV = {"S1": "simple majority in the chamber", "S2": "majority + head of state", "S3": "3/5 of seats", "S4": "2/3 of seats",
      "poza_polityka": "beyond politics alone", "ustawa": "left to ordinary law"}
SITE = "https://maxqmaxx.github.io/konstytucja/"


def name(c):
    return EN.territories.get(c) or c


def pct(x):
    return f"{x * 100:.1f}%"


def mean_profile(ms):
    return {o: statistics.fmean(m["profile"][o] for m in ms) for o in ORDER}


def build():
    D = json.loads((HERE / "wladza.json").read_text())["countries"]
    W = json.loads((HERE / "walidacja.json").read_text()) if (HERE / "walidacja.json").exists() else {}
    R = {k: m for k, m in D.items() if m["ranked"]}
    n, pl = len(R), D["PL"]
    world, eu = mean_profile(list(R.values())), mean_profile([m for k, m in R.items() if k in EU27])
    types = Counter(m["type"] for m in R.values())
    by_type = {t: mean_profile([m for m in R.values() if m["type"] == t]) for t in TYPES if types.get(t)}
    rank = sorted(R, key=lambda k: -R[k]["profile"]["HS"]).index("PL") + 1
    ov = Counter(m["decisions"]["ustawa"]["blokujaca_mniejszosc_bez_HS"] for m in R.values() if "ustawa" in m["decisions"])
    js = {k: m["sady"]["score"] for k, m in R.items() if m["sady"]["score"] is not None}
    top = sorted(R.items(), key=lambda kv: -kv[1]["profile"]["HS"])[:8]
    B = []
    B += [("h1", "Who governs, who blocks: the separation of powers in 188 constitutions"),
          ("p", "We read the texts of all 188 constitutions in force (English editions from the Constitute Project) and wrote each of 11 key decisions as a simple game: "
                "which bodies must agree and by what majority. From that we compute each body's share of decision power (the Shapley-Shubik index), "
                "the veto players, and the minority of seats that can block. The interactive version (in Polish) covers every country and decision: "
                f"{SITE}wladza/index.html, with a reform simulator for Poland: {SITE}wladza/symulator.html."),
          ("h2", "Key findings"),
          ("ul", [
              f"**Poland's President holds {pct(pl['profile']['HS'])} of decision power** across {len(pl['decisions'])} decisions: rank {rank} of {n} "
              f"(between {pl['rank_range'][0]} and {pl['rank_range'][1]} under alternative assumptions). World median for heads of state: {pct(statistics.median(m['profile']['HS'] for m in R.values()))}; EU average {pct(eu['HS'])}.",
              f"**Presidential veto.** The Sejm overrides the President's veto with 3/5 of votes (Art. 122(5)), so 40% of deputies can sustain it, worth 10% of power over ordinary law. "
              f"Only {ov.get(0.4, 0)} constitutions use 3/5; {ov.get(0.3333, 0)} use 2/3, and in {ov.get(0.5, 0)} a simple majority overrides the veto.",
              f"**Regime type matters most.** Heads of state hold on average {pct(by_type['prezydencki']['HS'])} of power in presidential systems, "
              f"{pct(by_type['polprezydencki_premierowski']['HS'])} in premier-presidential systems such as Poland or France, and {pct(by_type['parlamentarny']['HS'])} in parliamentary republics. "
              f"The strongest: {', '.join(name(k) + ' ' + pct(m['profile']['HS']) for k, m in top)}.",
              "**Capture.** In Poland a bare Sejm majority can fill the Constitutional Tribunal (Art. 194: no qualified majority) and the judges' seats on the National Council of the Judiciary "
              "(Art. 187: the Constitution leaves the choice to statute). Four of five key institutions are within reach of a simple majority, with or without the President.",
              f"**Judicial independence on paper.** Poland's constitution contains 8 of 10 guarantees (score {js.get('PL', 0):.0f}; world median {statistics.median(js.values()):.0f}, EU average {statistics.fmean(v for k, v in js.items() if k in EU27):.0f}). "
              "Missing: selection of constitutional judges by more than one body or a supermajority, and a rule that judges elect the judges on the judicial council.",
          ]),
          ("h2", "Poland, the EU and the world"),
          ("bars", [("Poland", pl["profile"]), (f"EU average ({sum(1 for k in R if k in EU27)})", eu), (f"World average ({n})", world)]),
          ("table", ["Decision", "Power shares in Poland", "Veto players", "Blocking minority in the Sejm"],
           [[DEC[d], ", ".join(f"{ORG[o]} {pct(v)}" for o, v in x["shares"].items()), ", ".join(ORG[o] for o in x["veto"]) or "–",
             "–" if x["blokujaca_mniejszosc"] is None else ("cannot block" if x["blokujaca_mniejszosc"] == 0 else f"more than {pct(x['blokujaca_mniejszosc'])}")]
            for d, x in pl["decisions"].items()]),
          ("h2", "Regime types"),
          ("table", ["Type (from the text and CCP coding)", "Countries", "Head of state", "Government", "Parliament"],
           [[TYPES[t], types[t], pct(p["HS"]), pct(p["G"]), pct(p["L1"] + p["L2"])] for t, p in sorted(by_type.items(), key=lambda kv: -types[kv[0]])]),
          ("h2", "Who can capture institutions"),
          ("p", "For each institution named in a constitution: the weakest political camp that fills it on its own. Share of ranked countries that have the institution in their constitution."),
          ("table", ["Institution", "Countries", "Simple majority or ordinary law", "Supermajority or judges needed", "Poland"],
           [[INST[k], sum(1 for m in R.values() if k in m["przejecie"]),
             pct(sum(1 for m in R.values() if m["przejecie"].get(k, {}).get("level") in ("S1", "S2", "ustawa")) / max(1, sum(1 for m in R.values() if k in m["przejecie"]))),
             pct(sum(1 for m in R.values() if m["przejecie"].get(k, {}).get("level") in ("S3", "S4", "poza_polityka")) / max(1, sum(1 for m in R.values() if k in m["przejecie"]))),
             LV.get(pl["przejecie"].get(k, {}).get("level"), "not in the constitution")] for k in INST])]
    if W.get("pola"):
        ty, sd, wy, wr = W["typologia"], W["sady"]["indeks_vs_melton_ginsburg"], W["wykonawcza"]["udzial_wykonawczej_vs_indeks"], W["wrazliwosc"]
        B += [("h2", "How far to trust these numbers"), ("ul", [
            f"**Readings vs experts.** Our language-model readings (with verbatim quotes checked in code) agree with the hand coding of the Comparative Constitutions Project (v5, 2023) "
            f"in {pct(W['pola_przed_rozstrzygnieciem']['zgodnosc'])} of {W['pola_razem']['n']} comparisons; structural fields reach 97–99% (chambers, veto override threshold, dissolution). "
            f"Each of the {W['rozstrzygniecia']['rozbieznosci']} disagreements was then adjudicated against the text (question in our definition, blind to who answered what, verbatim quote required): "
            f"{W['rozstrzygniecia']['poprawki']} readings were corrected, giving {pct(W['pola_razem']['zgodnosc'])}.",
            f"**Regime types** agree with Cheibub, Elkins and Ginsburg (2014) in {pct(ty['zgodnosc'])} of {ty['n']} constitutions (kappa {ty['kappa']}). "
            f"Our head-of-state share falls in their order: presidential {pct(ty['hs_wg_typu_cheibub']['prezydencki'])}, semi-presidential {pct(ty['hs_wg_typu_cheibub']['polprezydencki'])}, parliamentary {pct(ty['hs_wg_typu_cheibub']['parlamentarny'])}.",
            f"**Judicial index** correlates moderately with the Melton-Ginsburg de jure index (Spearman ρ = {sd['rho']}, 95% CI {sd['ci95'][0]}–{sd['ci95'][1]}).",
            f"**CCP executive power index** (7 powers) correlates weakly with our executive share (ρ = {wy['rho']}): it counts powers of the whole executive, including prime ministers, and barely separates regime types, so it measures something else.",
            f"**Robustness.** Under alternative assumptions the ranking correlates {min(x['spearman_z_bazowym']['rho'] for x in wr['warianty'].values())}–{max(x['spearman_z_bazowym']['rho'] for x in wr['warianty'].values())} with the baseline, "
            f"but a single country typically moves {wr['mediana_rozpietosci_miejsca']:.0f} places, so we report ranges.",
        ])]
    B += [("h2", "Limits"), ("ul", [
        "Text only: no statutes, standing orders, case law or practice. Bodies are treated as unitary; the model knows nothing about parties, coalitions or cohabitation.",
        "Chambers are modelled as large bodies of equal members; agenda-setting (who proposes first) carries no power, only whose consent is needed.",
        "Where the text is silent, the assumption is listed next to the decision; a missing provision is not proof of absence.",
        "Data and code: github.com/maxqmaxx/konstytucja (dane/wladza_*.csv, kod/analysis/wladza/). CCP data: Elkins and Ginsburg, Characteristics of National Constitutions v5 (2025).",
    ])]
    return B


def md(B):
    out = []
    for b in B:
        if b[0] == "h1":
            out.append("# " + b[1])
        elif b[0] == "h2":
            out.append("## " + b[1])
        elif b[0] == "p":
            out.append(b[1])
        elif b[0] == "ul":
            out.append("\n".join("- " + x for x in b[1]))
        elif b[0] == "table":
            out.append("\n".join(["| " + " | ".join(b[1]) + " |", "|" + "---|" * len(b[1])] + ["| " + " | ".join(str(c) for c in r) + " |" for r in b[2]]))
        elif b[0] == "bars":
            out.append("\n".join(f"- **{lbl}**: " + ", ".join(f"{ORG[o]} {pct(p[o])}" for o in ORDER if p[o] > .0005) for lbl, p in b[1]))
    return "\n\n".join(out) + "\n"


def to_html(B):
    para = lambda t: re.sub(r"(https?://[^\s<,]+[^\s<,.])", r'<a href="\1">\1</a>', re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", html.escape(t)))  # noqa: E731
    out = []
    for b in B:
        if b[0] == "h1":
            out.append(f"<p class=\"crumbs\"><a href=\"index.html\">Władza</a> / English</p><h1>{html.escape(b[1])}</h1>")
        elif b[0] == "h2":
            out.append(f"<h2>{html.escape(b[1])}</h2>")
        elif b[0] == "p":
            out.append(f'<p class="sub">{para(b[1])}</p>' if not out[1:] else f"<p>{para(b[1])}</p>")
        elif b[0] == "ul":
            out.append('<div class="box"><ul class="flags" style="color:inherit;font-size:15px">' + "".join(f"<li>{para(x)}</li>" for x in b[1]) + "</ul></div>")
        elif b[0] == "table":
            out.append('<div class="box"><div class="tablewrap"><table class="w"><thead><tr>' + "".join(f"<th>{html.escape(h)}</th>" for h in b[1]) + "</tr></thead><tbody>"
                       + "".join("<tr>" + "".join(f"<td>{html.escape(str(c))}</td>" for c in r) + "</tr>" for r in b[2]) + "</tbody></table></div></div>")
        elif b[0] == "bars":
            rows = "".join(f'<tr><td>{html.escape(lbl)}</td><td style="min-width:220px"><div class="stack">' + "".join(
                f'<i style="width:{p[o] * 100:.2f}%;background:{COLORS[o]}" title="{ORG[o]} {pct(p[o])}"></i>' for o in ORDER if p[o] > .0005)
                + f'</div></td><td class="n">{pct(p["HS"])}</td><td class="n">{pct(p["G"])}</td><td class="n">{pct(p["L1"] + p["L2"])}</td></tr>' for lbl, p in b[1])
            leg = "".join(f'<span><i style="background:{COLORS[o]}"></i>{ORG[o]}</span>' for o in ORDER)
            out.append(f'<div class="box"><div class="tablewrap"><table class="w"><thead><tr><th></th><th>Power shares</th><th>Head of state</th><th>Government</th><th>Parliament</th></tr></thead><tbody>{rows}</tbody></table></div><p class="legend">{leg}</p></div>')
    return "\n".join(out)


def main():
    import importlib.util
    spec = importlib.util.spec_from_file_location("wladza_build", HERE / "build.py")  # this folder's build.py (styles)
    wb = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(wb)
    W_CSS = wb.CSS
    B = build()
    (HERE / "summary_en.md").write_text(md(B), encoding="utf-8")
    doc = page("Separation of powers in 188 constitutions", to_html(B), description="Who governs and who blocks in 188 constitutions: Shapley-Shubik power shares, veto players, capture of institutions, judicial independence; Poland in focus.",
               css="../panstwa/style.css", current="wladza").replace("</head>", f"<style>{W_CSS}p,li{{overflow-wrap:anywhere}}</style></head>").replace('<html lang="pl">', '<html lang="en">')
    (HERE / "en.html").write_text(doc, encoding="utf-8")
    print(json.dumps({"blocks": len(B)}))


if __name__ == "__main__":
    main()
