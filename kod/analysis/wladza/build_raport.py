#!/usr/bin/env python3
"""Separation-of-powers report (Markdown + standalone HTML) from wladza.json, with supporting quotes (private copy only).

  .venv/bin/python analysis/wladza/build_raport.py [--share DIR]
"""
from __future__ import annotations

import argparse
import html
import json
import re
import shutil
import statistics
import sys
from collections import Counter
from datetime import date
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "panstwa"))
from build import name_pl  # noqa: E402

SLUG = f"konstytucje-podzial-wladzy-{date.today().isoformat()}"
SITE = "http://localhost:8112/analysis/wladza/index.html"
EU27 = {"AT", "BE", "BG", "HR", "CY", "CZ", "DK", "EE", "FI", "FR", "DE", "GR", "HU", "IE", "IT",
        "LV", "LT", "LU", "MT", "NL", "PL", "PT", "RO", "SK", "SI", "ES", "SE"}
ORDER = ["L1", "L2", "G", "HS", "P", "CC", "J"]
COLORS = {"L1": "#006858", "L2": "#5fa58f", "G": "#c49260", "HS": "#b4532a", "P": "#6c5a9e", "CC": "#41525e", "J": "#8c9aa3"}
PL_ORG = {"L1": "Sejm", "L2": "Senat", "HS": "Prezydent", "G": "Rada Ministrów", "P": "Naród", "CC": "Trybunał Konstytucyjny", "J": "Trybunał Stanu / sądy"}


def pct(x):
    return f"{x * 100:.1f}".replace(".", ",") + "%"


def blk(x):
    if x is None:
        return "–"
    if x == -1:
        return "sprzeciwu nie da się odrzucić"
    if x == 0:
        return "izba nie blokuje"
    return "ponad " + pct(x).replace(",0%", "%")


def shares_txt(s, names):
    return ", ".join(f"{names[o]} {pct(s[o])}" for o in ORDER if s.get(o, 0) > .0005)


def mean_profile(ms):
    return {o: statistics.fmean(m["profile"][o] for m in ms) for o in ORDER}


PUBLIC_SITE = "https://maxqmaxx.github.io/konstytucja/wladza/index.html"


def build(data, public=False):
    """public=True: no quotes from the Constitute editions (publisher rights) and the public site address."""
    meta, C = data["meta"], data["countries"]
    short = meta["short"]
    R = {k: m for k, m in C.items() if m["ranked"]}
    n = len(R)
    pl = C["PL"]
    world, eu = mean_profile(list(R.values())), mean_profile([m for k, m in R.items() if k in EU27])
    hs_rank = sorted(R, key=lambda k: -R[k]["profile"]["HS"]).index("PL") + 1
    hhi_rank = sorted(R, key=lambda k: -R[k]["hhi"]).index("PL") + 1
    eu_r = sorted((k for k in R if k in EU27), key=lambda k: -R[k]["profile"]["HS"])
    types = Counter(m["type"] for m in R.values())
    by_type = {t: (types[t], mean_profile([m for m in R.values() if m["type"] == t])) for t in meta["types"] if types.get(t)}
    ov = Counter(m["decisions"]["ustawa"]["blokujaca_mniejszosc_bez_HS"] for m in R.values() if "ustawa" in m["decisions"])
    am = Counter(m["decisions"]["konstytucja"]["blokujaca_mniejszosc"] for m in R.values() if "konstytucja" in m["decisions"])
    parl = lambda m: m["profile"]["L1"] + m["profile"]["L2"]

    B = [("h", 1, "Kto rządzi, kto blokuje: podział władzy w 188 konstytucjach"),
         ("p", f"Stan danych: {date.today().isoformat()}. Wersja interaktywna (każde państwo, każda decyzja): {PUBLIC_SITE if public else SITE}"
               + (". Dane: dane/wladza_kraje.csv i dane/wladza_decyzje.csv; metoda: docs/metoda.md." if public else "")),
         ("p", "Raport opisuje, jak teksty obowiązujących konstytucji dzielą 11 kluczowych decyzji między parlament, głowę państwa, rząd, naród (referendum) i sądy. "
               "Każdą decyzję zapisano jako grę: które organy muszą się zgodzić i jaką większością. Z tego wynika udział siły każdego organu "
               "(indeks Shapleya-Shubika, w każdej decyzji suma 100%), kto ma weto i jaka mniejszość w parlamencie wystarczy do blokady."),
         ("h", 2, "Najważniejsze wnioski")]
    top = sorted(R.items(), key=lambda kv: -kv[1]["profile"]["HS"])[:8]
    low_hhi = sorted(R.items(), key=lambda kv: kv[1]["hhi"])[:8]
    B.append(("ul", [
        f"**Prezydent RP ma {pct(pl['profile']['HS'])} siły** (średnio w {len(pl['decisions'])} decyzjach). To {hs_rank}. miejsce z {n} od najsilniejszej głowy państwa (przy innych założeniach modelu {pl['rank_range'][0]}.–{pl['rank_range'][1]}.) "
        f"i {eu_r.index('PL') + 1}. z {len(eu_r)} w UE. Mediana świata: {pct(statistics.median(m['profile']['HS'] for m in R.values()))}, średnia UE: {pct(eu['HS'])}.",
        f"**Sejm i Senat razem: {pct(parl(pl))}**, rząd {pct(pl['profile']['G'])}. Senat ma {pct(pl['profile']['L2'])}: jego sprzeciw wobec ustaw Sejm odrzuca bezwzględną większością (art. 121 ust. 3), więc w modelu nie przesądza o wyniku zwykłej ustawy. Siłę Senatu daje zmiana konstytucji (art. 235).",
        f"**Weto prezydenta RP** (art. 122 ust. 5) daje mu 10% siły przy ustawie: Sejm odrzuca je większością 3/5, więc zablokować może ponad 40% posłów popierających prezydenta. "
        f"Na świecie częstszy jest próg 2/3 ({ov.get(0.3333, 0)} państw, blokuje ponad 1/3) albo zwykła większość, przy której weto niczego nie przesądza ({ov.get(0.5, 0)}). Próg 3/5: {ov.get(0.4, 0)} państwa; weto nie do odrzucenia: {ov.get(-1, 0)}.",
        f"**Budżet**: wyłączna inicjatywa Rady Ministrów (art. 221) czyni rząd drugim, obok Sejmu, organem bez którego budżetu nie ma (po 50%). Prezydent nie może budżetu zawetować (art. 224), a gdy budżetu nie ma, rząd działa na podstawie projektu (art. 219 ust. 4).",
        f"**Systemy prezydenckie** dają głowie państwa średnio {pct(by_type['prezydencki'][1]['HS'])} siły, parlamentarne {pct(by_type['parlamentarny'][1]['HS'])}. "
        f"Najsilniejsze głowy państwa: {', '.join(name_pl(k, k) + ' ' + pct(m['profile']['HS']) for k, m in top)}.",
        f"**Najbardziej rozproszona władza** (najniższa koncentracja HHI): {', '.join(name_pl(k, k) for k, _ in low_hhi)}. Polska: HHI {str(round(pl['hhi'], 2)).replace('.', ',')}, {hhi_rank}. miejsce z {n} od najbardziej skoncentrowanej.",
    ]))

    B += [("h", 2, "Polska: kto ile ma siły"),
          ("bars", [("Polska", pl["profile"]), (f"Unia Europejska ({len(eu_r)})", eu), (f"Świat ({n})", world)], short),
          ("p", "Udział w decyzjach (Shapley-Shubik), weto i mniejszość blokująca w Sejmie. „Gdy Prezydent przeciw”: ile posłów wystarczy, by utrzymać jego sprzeciw.")]
    rows = []
    for d, x in pl["decisions"].items():
        rows.append([meta["decisions"][d], shares_txt(x["shares"], PL_ORG), ", ".join(PL_ORG[o] for o in x["veto"]) or "–",
                     blk(x["blokujaca_mniejszosc"]) + ("" if x["blokujaca_mniejszosc_bez_HS"] in (None, x["blokujaca_mniejszosc"]) else f"; gdy Prezydent przeciw: {blk(x['blokujaca_mniejszosc_bez_HS'])}"),
                     "; ".join(x["flags"]) or ""])
    B.append(("table", ["Decyzja", "Podział siły", "Weto", "Mniejszość blokująca w Sejmie", "Założenia"], rows))

    B.append(("h", 2, "Polska: kto kogo blokuje i kontroluje"))
    bl = [f"**{PL_ORG[a]}** może zablokować: " + "; ".join(f"{PL_ORG[b]} ({', '.join(meta['decisions'][d].lower() for d in ds)})" for b, ds in bs.items())
          for a, bs in pl["blocks"].items()]
    lab = {"odwolanie_rzadu": "odwołuje rząd", "rozwiazanie": "rozwiązuje Sejm", "usuniecie_glowy": "usuwa Prezydenta", "sedziowie_tk": "wybiera sędziów TK"}
    ct = [f"{', '.join(PL_ORG[b] for b in k['by'] if b != k['target'])}: {lab[k['decision']]}" for k in pl["control"]]
    B.append(("ul", bl + ct))
    B.append(("p", "Ograniczenia hamujące: " + "; ".join(t for k, t in [("konstruktywne_wotum", "konstruktywne wotum nieufności (art. 158)"), ("opozycja_do_sadu", "50 posłów lub 30 senatorów może zaskarżyć ustawę do TK (art. 191)"),
                                                                        ("obywatel_do_sadu", "skarga konstytucyjna (art. 79)")] if pl["indicators"].get(k))
                + ". Prezydent może skrócić kadencję Sejmu tylko w dwóch sytuacjach (art. 155 ust. 2 i art. 225)."))

    B += [("h", 2, "Typy ustroju na świecie"),
          ("table", ["Typ (z tekstu)", "Państw", "Głowa państwa", "Rząd", "Parlament", "Naród i sądy"],
           [[meta["types"][t], c, pct(p["HS"]), pct(p["G"]), pct(p["L1"] + p["L2"]), pct(p["P"] + p["CC"] + p["J"])] for t, (c, p) in sorted(by_type.items(), key=lambda kv: -kv[1][0])])]

    B += [("h", 2, "Ranking: najsilniejsza i najsłabsza głowa państwa"),
          ("table", ["Państwo", "Typ", "Głowa państwa", "Rząd", "Parlament", "HHI"],
           [[name_pl(k, k), meta["types"][m["type"]], pct(m["profile"]["HS"]), pct(m["profile"]["G"]), pct(parl(m)), f"{m['hhi']:.2f}".replace(".", ",")]
            for k, m in sorted(R.items(), key=lambda kv: -kv[1]["profile"]["HS"])[:20]]),
          ("p", "Najsłabsza głowa państwa (udział bliski zera: działa na wniosek rządu albo nie uczestniczy w kluczowych decyzjach): "
           + ", ".join(name_pl(k, k) for k, m in sorted(R.items(), key=lambda kv: kv[1]["profile"]["HS"]) if m["profile"]["HS"] < .02) + "."),
          ("h", 2, "Unia Europejska"),
          ("table", ["Państwo", "Typ", "Głowa państwa", "Rząd", "Parlament", "Inne", "HHI"],
           [[name_pl(k, k), meta["types"][R[k]["type"]], pct(R[k]["profile"]["HS"]), pct(R[k]["profile"]["G"]), pct(parl(R[k])),
             pct(R[k]["profile"]["P"] + R[k]["profile"]["CC"] + R[k]["profile"]["J"]), f"{R[k]['hhi']:.2f}".replace(".", ",")] for k in eu_r])]

    B += [("h", 2, "Progi blokady"),
          ("table", ["Próg", "Odrzucenie weta: państw", "Zmiana konstytucji: państw"],
           [[blk(v), ov.get(v, 0), am.get(v, 0)] for v in sorted(set(ov) | set(am), key=lambda v: (v is None, -(v or 0)))]),
          ("p", "Odrzucenie weta: ile mandatów wystarczy, by utrzymać sprzeciw głowy państwa wobec ustawy („–”: głowa państwa nie ma weta lub tekst tego nie określa). "
                "Zmiana konstytucji: ile mandatów pierwszej izby blokuje zmianę, gdy pozostałe organy są za.")]

    srcs = []
    for d, x in pl["decisions"].items():
        for t, s in x["sources"].items():
            srcs.append([meta["decisions"][d], t, ", ".join(s["articles"][:6]), s["cytat"], "; ".join(s["korekty"])])
    if public:
        B += [("h", 2, "Podstawa dla Polski"),
              ("table", ["Decyzja", "Temat", "Artykuły we fragmencie", "Ręczna korekta"], [[r[0], r[1], r[2], r[4]] for r in srcs])]
    else:
        B += [("h", 2, "Podstawa dla Polski (cytaty z wydania angielskiego)"),
              ("table", ["Decyzja", "Temat", "Artykuły we fragmencie", "Cytat (EN)", "Ręczna korekta"], srcs)]

    # ---- capture of institutions ----
    LV = {"S1": "zwykła większość w izbie", "S2": "większość i głowa państwa", "S3": "3/5 mandatów", "S4": "2/3 mandatów",
          "poza_polityka": "poza zasięgiem samej polityki", "ustawa": "decyduje ustawa (zwykła większość)"}
    inst = meta["institutions"]
    B += [("h", 2, "Kto może sam przejąć instytucje"),
          ("p", "Dla każdej instytucji opisanej w konstytucji: najsłabszy obóz polityczny, który sam wybiera wszystkich jej członków. "
                "„Decyduje ustawa”: konstytucja nie mówi, kto wybiera. „Poza zasięgiem samej polityki”: współdecydują sędziowie, naród albo opozycja."),
          ("table", ["Instytucja", "Polska", "Państw z tą instytucją", "Zwykła większość lub ustawa", "Potrzebna większość kwalifikowana lub sędziowie"],
           [[label, LV.get(pl["przejecie"].get(k, {}).get("level"), "nie ma w konstytucji"),
             sum(1 for m in R.values() if k in m["przejecie"]),
             pct(sum(1 for m in R.values() if m["przejecie"].get(k, {}).get("level") in ("S1", "S2", "ustawa")) / max(1, sum(1 for m in R.values() if k in m["przejecie"]))),
             pct(sum(1 for m in R.values() if m["przejecie"].get(k, {}).get("level") in ("S3", "S4", "poza_polityka")) / max(1, sum(1 for m in R.values() if k in m["przejecie"])))]
            for k, label in inst.items()]),
          ("p", "W Polsce sędziów Trybunału wybiera Sejm bez większości kwalifikowanej (art. 194), a konstytucja nie mówi, kto wybiera sędziów-członków KRS (art. 187 ust. 4 odsyła do ustawy). "
                "Te dwie instytucje może więc obsadzić sama większość sejmowa. Prezesa NBP powołuje Sejm na wniosek Prezydenta (art. 227), więc potrzebna jest ich zgoda. Zmiana konstytucji wymaga 2/3 Sejmu i Senatu (art. 235).")]
    # ---- judicial independence ----
    js = {k: m["sady"]["score"] for k, m in R.items() if m["sady"]["score"] is not None}
    eu_j = sorted((k for k in js if k in EU27), key=lambda k: -js[k])
    B += [("h", 2, "Niezależność sądów zapisana w konstytucji"),
          ("p", f"Indeks: odsetek z 10 gwarancji obecnych w tekście (spośród tych, które dotyczą danej konstytucji). Polska: {js.get('PL', 0):.0f} na 100, mediana świata {statistics.median(js.values()):.0f}, średnia UE {statistics.fmean(js[k] for k in eu_j):.0f}. "
                "Brakuje dwóch: sędziów TK wybiera jeden organ zwykłą większością, a konstytucja nie mówi, że sędziów-członków KRS wybierają sędziowie."),
          ("table", ["Gwarancja", "Polska", "Odsetek konstytucji"],
           [[t, "tak" if pl["sady"]["components"].get(k) else ("nie dotyczy" if pl["sady"]["components"].get(k) is None else "nie"),
             pct(sum(1 for m in R.values() if m["sady"]["components"].get(k)) / max(1, sum(1 for m in R.values() if m["sady"]["components"].get(k) is not None)))]
            for k, t in meta["judicial"].items()]),
          ("table", ["Państwo UE", "Indeks"], [[name_pl(k, k), f"{js[k]:.0f}"] for k in eu_j])]
    # ---- reform scenarios for Poland (simulator, same code as the web page) ----
    sims = simulate(meta)
    if sims:
        B += [("h", 2, "Jak reformy zmieniłyby układ sił w Polsce"),
              ("p", "Wynik symulatora (strona Władza → Symulator) dla gotowych zestawów. „Instytucje”: ile z pięciu (TK, KRS, RPO, NBP, zmiana konstytucji) może obsadzić sama zwykła większość, z Prezydentem lub bez."),
              ("table", ["Zestaw", "Sejm", "Senat", "Rząd", "Prezydent", "Naród", "Instytucje w zasięgu zwykłej większości"],
               [[lbl, pct(p["L1"]), pct(p["L2"]), pct(p["G"]), pct(p["HS"]), pct(p["P"]), f"{cap} z 5"] for lbl, p, cap in sims])]
    # ---- trust ----
    W = json.loads((HERE / "walidacja.json").read_text()) if (HERE / "walidacja.json").exists() else {}
    if W.get("pola"):
        ty, sd, wy, wr = W["typologia"], W["sady"]["indeks_vs_melton_ginsburg"], W["wykonawcza"]["udzial_wykonawczej_vs_indeks"], W["wrazliwosc"]
        f3 = lambda v: str(v).replace(".", ",")  # noqa: E731
        B += [("h", 2, "Na ile ufać tym liczbom"), ("ul", [
            f"**Odczyty a eksperci.** W {W['pola_razem']['n']} porównaniach z ręcznym kodowaniem Comparative Constitutions Project (wersja 5) zgodność wynosiła {pct(W['pola_przed_rozstrzygnieciem']['zgodnosc'])}. "
            f"Każdą z {W['rozstrzygniecia']['rozbieznosci']} rozbieżności rozstrzygnęliśmy na tekście (pytanie w naszej definicji, bez wskazania, czyja odpowiedź jest czyja, z dosłownym cytatem); {W['rozstrzygniecia']['poprawki']} odczytów poprawiliśmy, po czym zgodność wynosi {pct(W['pola_razem']['zgodnosc'])}. "
            "Pola strukturalne: liczba izb 97%, próg odrzucenia weta 99%, rozwiązanie parlamentu 97%. Najsłabiej: kto odwołuje rząd (ok. 70%), bo CCP liczy też formalne odwołanie ministrów przez głowę państwa.",
            f"**Typ ustroju.** Zgodność z klasyfikacją Cheibuba, Elkinsa i Ginsburga (2014): {pct(ty['zgodnosc'])} ({ty['n']} konstytucji, kappa {f3(ty['kappa'])}). "
            f"Udział głowy państwa w naszym modelu rośnie zgodnie z ich typem: parlamentarne {pct(ty['hs_wg_typu_cheibub']['parlamentarny'])}, półprezydenckie {pct(ty['hs_wg_typu_cheibub']['polprezydencki'])}, prezydenckie {pct(ty['hs_wg_typu_cheibub']['prezydencki'])}.",
            f"**Niezależność sądów.** Korelacja rang z indeksem Meltona i Ginsburga (2014): ρ = {f3(sd['rho'])} (95%: {f3(sd['ci95'][0])}–{f3(sd['ci95'][1])}). Umiarkowana: ich indeks dotyczy sądu najwyższego, nasz głównie TK i rady sądownictwa.",
            f"**Indeks władzy wykonawczej CCP** (7 uprawnień) koreluje z naszym udziałem głowy państwa i rządu słabo (ρ = {f3(wy['rho'])}). Ten indeks liczy uprawnienia całej władzy wykonawczej, także premiera, i prawie nie różnicuje typów ustroju, więc mierzy co innego.",
            f"**Założenia.** Przy innych założeniach (wagi decyzji, bez reguły dla monarchii, łatwe lub nieosiągalne większości kwalifikowane, tylko decyzje bez założeń) korelacja rang z modelem bazowym wynosi {f3(min(x['spearman_z_bazowym']['rho'] for x in wr['warianty'].values()))}–{f3(max(x['spearman_z_bazowym']['rho'] for x in wr['warianty'].values()))}, "
            f"ale pojedyncze miejsce przesuwa się typowo o {wr['mediana_rozpietosci_miejsca']:.0f} pozycji. Dlatego podajemy przedziały.",
        ])]
    B += [("h", 2, "Metoda i ograniczenia"), ("ul", [
        "Dane: 49 tematów wariantów odczytanych modelem językowym (Claude) z angielskich wydań Constitute dla 188 obowiązujących konstytucji. Kod sprawdza, że cytat występuje w tekście; odpowiedzi bez zgodnego cytatu pominięto. Wartości dla Polski sprawdzono ręcznie (korekty z podstawą prawną w korekty.json).",
        "Indeks Shapleya-Shubika: organy jednoosobowe są graczami, izba to duża grupa równych posłów. Weto odrzucane większością q daje głowie państwa udział równy szerokości okna między 50% a q. Liczone dokładnie, bez losowania. Profil państwa to średnia z decyzji, które da się zbudować z tekstu.",
        "Organy są jednolite: model nie zna partii, koalicji, kohabitacji ani praktyki. Kolejność działania (kto proponuje pierwszy) nie daje siły, liczy się tylko, czyja zgoda jest potrzebna. Obie izby głosują tą samą większością.",
        "Liczbę izb i próg odrzucenia weta, gdy nie wynikały z odczytu, oraz sposób wyboru głowy państwa (do typologii) wzięto z kodowania CCP (Elkins i Ginsburg 2025).",
        "Gdy tekst czegoś nie określa, przyjęto założenie wypisane przy decyzji. Do rankingów trafiają państwa z co najmniej 6 decyzjami bez niewiadomych w strukturze (" + f"{n} ze {len(C)}).",
        "Wydania Constitute mogą nie uwzględniać najnowszych zmian. Raport nie obejmuje ustaw, regulaminów ani orzecznictwa.",
    ])]
    return B


def simulate(meta):
    """Run the simulator's own JavaScript (symulator.py) in Node for the preset reform packages."""
    import shutil
    import subprocess
    import tempfile
    sys.path.insert(0, str(HERE))
    import symulator
    if not shutil.which("node"):
        return []
    with tempfile.TemporaryDirectory() as d:
        f = Path(d) / "sim.js"
        f.write_text(symulator.js(meta, {}) + """
const out=[];for(const [id,label,set] of PRESETS){const k={};KNOBS.forEach(([n,,o])=>k[n]=(set[n]||o[0][0]));const a=analyse(k);
out.push([label,a.prof,a.cap.filter(r=>['S1','S2','ustawa'].includes(r[1])).length]);}console.log(JSON.stringify(out));""")
        res = subprocess.run(["node", str(f)], capture_output=True, text=True)
    if res.returncode:
        return []
    return [(lbl, {o: p.get(o, 0) for o in ORDER}, cap) for lbl, p, cap in json.loads(res.stdout)]


def md(B):
    out = []
    for b in B:
        if b[0] == "h":
            out.append("#" * b[1] + " " + b[2])
        elif b[0] == "p":
            out.append(b[1])
        elif b[0] == "ul":
            out.append("\n".join("- " + x for x in b[1]))
        elif b[0] == "table":
            esc = lambda s: str(s).replace("|", "\\|").replace("\n", " ")  # noqa: E731
            out.append("\n".join(["| " + " | ".join(b[1]) + " |", "|" + "---|" * len(b[1])] + ["| " + " | ".join(esc(c) for c in r) + " |" for r in b[2]]))
        elif b[0] == "bars":
            out.append("\n".join(f"- **{lbl}**: " + shares_txt(p, b[2]) for lbl, p in b[1]))
    return "\n\n".join(out) + "\n"


CSS = """
:root{--bg:#fbfaf7;--fg:#1d1d1b;--muted:#6b6862;--line:#e3e0d8;--card:#fff;--accent:#8a3b12;--th:#f2efe8}
@media (prefers-color-scheme:dark){:root:not([data-theme=light]){--bg:#161615;--fg:#ecebe6;--muted:#a4a19a;--line:#33322f;--card:#1f1f1d;--accent:#e49a6a;--th:#262624}}
:root[data-theme=dark]{--bg:#161615;--fg:#ecebe6;--muted:#a4a19a;--line:#33322f;--card:#1f1f1d;--accent:#e49a6a;--th:#262624}
*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--fg);font:16px/1.55 system-ui,-apple-system,"Segoe UI",sans-serif}
main{max-width:1100px;margin:0 auto;padding:24px 16px 64px}h1{font-size:1.9rem;line-height:1.2;margin:.2em 0 .4em}
h2{font-size:1.35rem;margin:2em 0 .5em;padding-top:.6em;border-top:1px solid var(--line)}p,li{max-width:80ch;overflow-wrap:anywhere}li{margin:.35em 0}
a{color:var(--accent)}.wrap{overflow-x:auto;margin:.6em 0 1em}table{border-collapse:collapse;width:100%;font-size:.92rem;background:var(--card)}
th,td{border:1px solid var(--line);padding:6px 8px;text-align:left;vertical-align:top}th{background:var(--th);font-weight:600}
.bars{display:grid;grid-template-columns:minmax(120px,200px) 1fr;gap:8px 12px;align-items:center;margin:1em 0}
.stack{display:flex;height:26px;border-radius:3px;overflow:hidden;background:var(--th)}.stack i{display:block;height:100%}
.legend{display:flex;flex-wrap:wrap;gap:4px 14px;font-size:.85rem;color:var(--muted)}.legend i{display:inline-block;width:11px;height:11px;border-radius:2px;margin-right:5px;vertical-align:-1px}
.small{font-size:.85rem;color:var(--muted)}
"""


def render_html(B):
    para = lambda t: re.sub(r"(https?://[^\s<]+)", r'<a href="\1">\1</a>', re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", html.escape(t)))  # noqa: E731
    out = []
    for b in B:
        if b[0] == "h":
            out.append(f"<h{b[1]}>{html.escape(b[2])}</h{b[1]}>")
        elif b[0] == "p":
            out.append(f"<p>{para(b[1])}</p>")
        elif b[0] == "ul":
            out.append("<ul>" + "".join(f"<li>{para(x)}</li>" for x in b[1]) + "</ul>")
        elif b[0] == "table":
            h = "".join(f"<th>{html.escape(x)}</th>" for x in b[1])
            rows = "".join("<tr>" + "".join(f"<td>{html.escape(str(c))}</td>" for c in r) + "</tr>" for r in b[2])
            out.append(f'<div class="wrap"><table><thead><tr>{h}</tr></thead><tbody>{rows}</tbody></table></div>')
        elif b[0] == "bars":
            names = b[2]
            g = "".join(f'<div><b>{html.escape(lbl)}</b><div class="small">{html.escape(shares_txt(p, names))}</div></div><div class="stack" role="img" aria-label="{html.escape(shares_txt(p, names))}">'
                        + "".join(f'<i style="width:{p[o] * 100:.2f}%;background:{COLORS[o]}" title="{html.escape(names[o])} {pct(p[o])}"></i>' for o in ORDER if p[o] > .0005) + "</div>"
                        for lbl, p in b[1])
            leg = "".join(f'<span><i style="background:{COLORS[o]}"></i>{html.escape(names[o])}</span>' for o in ORDER)
            out.append(f'<div class="bars">{g}</div><p class="legend">{leg}</p>')
    return (f'<!doctype html><html lang="pl"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">'
            f"<title>Podział władzy</title><style>{CSS}</style></head><body><main>{''.join(out)}</main></body></html>\n")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--share", type=Path)
    args = ap.parse_args()
    data = json.loads((HERE / "wladza.json").read_text())
    B = build(data)
    (HERE / "raport.md").write_text(md(B), encoding="utf-8")
    (HERE / "raport.html").write_text(render_html(B), encoding="utf-8")
    (HERE / "raport_publiczny.md").write_text(md(build(data, public=True)), encoding="utf-8")
    print(json.dumps({"blocks": len(B)}))
    if args.share:
        for ext in ("md", "html"):
            dst = args.share / f"{SLUG}.{ext}"
            shutil.copyfile(HERE / f"raport.{ext}", dst)
            dst.chmod(0o600)
            print(dst)


if __name__ == "__main__":
    main()
