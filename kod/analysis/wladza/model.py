#!/usr/bin/env python3
"""Who decides and who blocks: decision games built from the extracted constitutional variants (no LLM here).

Each constitution gives up to 11 decisions (ordinary law, budget, constitutional amendment, appointing and removing the
government, dissolving parliament, constitutional judges, emergency, war, treaties, removing the head of state).
A decision is a simple game: a list of winning clauses. A clause names the single-actor organs that must agree
(head of state, government, the people in a referendum, courts) and, for each chamber, the share of members that must
vote for it (0.5 = majority, 0.6 = three fifths, ...).

Power = Shapley-Shubik index. Single-actor organs are players; a chamber is a large body of equal members
(oceanic players), so a veto that a chamber can override with a 3/5 majority gives the head of state the width of the
window between 50% and 60% of the chamber: 10% of the decision. Computed exactly (integrals of polynomials), not sampled.
Blocking minority: the smallest share of the first chamber that can stop the decision when every other organ agrees.

Input: analysis/warianty/load.py (records with a verified quote, plus documented corrections).
Output: wladza.json, wladza_kraje.csv, wladza_decyzje.csv.
Usage: python3 analysis/wladza/model.py
"""
from __future__ import annotations

import csv
import json
import re
import sys
from itertools import combinations
from math import comb
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "warianty"))
import load as variants  # noqa: E402

PM_WORDS = re.compile(r"prime minister|chancellor|\bpremier\b|head of (the )?government|chief minister|first minister|minister of state"
                      r"|(president|chair(man|person)?) of the (council of ministers|government|cabinet|executive yuan)", re.I)
# the monarch is not responsible, ministers are: countersigned acts of the monarch are the government's decisions
FORMAL_MONARCH = re.compile(r"\b(king|queen|monarch|grand duke|emperor|sultan|emir)\b[^.;]{0,60}\b(inviolable|immune|sacred|sacrosanct|irresponsible"
                            r"|not (be )?(held )?(accountable|answerable|responsible|liable))|ministers?,? and not the (king|queen|monarch|grand duke),? (shall be|are) responsible", re.I)
MONARCH = re.compile(r"\b(grand duke|the king|the queen|emir|sultan|reigning prince|the crown)\b", re.I)

ORGANS = {"L1": "Izba pierwsza (lub jedyna)", "L2": "Druga izba", "HS": "Głowa państwa", "G": "Rząd i premier",
          "P": "Naród (referendum)", "CC": "Sąd konstytucyjny", "J": "Sądownictwo"}
SHORT = {"L1": "Izba pierwsza", "L2": "Druga izba", "HS": "Głowa państwa", "G": "Rząd", "P": "Naród", "CC": "Sąd konst.", "J": "Sądy"}
CHAMBERS = ("L1", "L2")
DECISIONS = {
    "ustawa": "Uchwalenie ustawy zwykłej",
    "budzet": "Uchwalenie budżetu",
    "konstytucja": "Zmiana konstytucji",
    "powolanie_rzadu": "Powołanie szefa rządu",
    "odwolanie_rzadu": "Odwołanie rządu",
    "rozwiazanie": "Rozwiązanie parlamentu",
    "sedziowie_tk": "Wybór sędziów sądu konstytucyjnego",
    "stan_nadzwyczajny": "Stan nadzwyczajny",
    "wojna": "Wojna i użycie wojska",
    "ratyfikacja": "Ratyfikacja umów",
    "usuniecie_glowy": "Usunięcie głowy państwa",
}
# decisions that act on an organ: (decision, target) -> "who controls whom"
TARGET = {"odwolanie_rzadu": "G", "rozwiazanie": "L1", "usuniecie_glowy": "HS", "sedziowie_tk": "CC"}
THR = {"zwykla": .5, "zwykla_lub_bezwzgledna": .5, "bezwzgledna": .5, "trzy_piate": .6, "dwie_trzecie": 2 / 3, "trzy_czwarte": .75}
UNKNOWN = (None, "nie_wynika", "inny", "inne")
MIN_DECISIONS = 6  # countries with fewer complete decisions are shown but not ranked


# ---------------- game theory ----------------
def tau(clauses, present):
    """Smallest chamber share at which the game is won when exactly the single actors in `present` agree (inf if never)."""
    best = float("inf")
    for c in clauses:
        if set(c["req"]) <= present:
            best = min(best, max(c["ch"].values(), default=0.0))
    return best


def _int_poly(s, m, a, b):
    """Integral of t^s (1-t)^m over [a, b]."""
    a, b = max(0.0, min(1.0, a)), max(0.0, min(1.0, b))
    if b <= a:
        return 0.0
    return sum(comb(m, j) * (-1) ** j * (b ** (s + j + 1) - a ** (s + j + 1)) / (s + j + 1) for j in range(m + 1))


def shapley(clauses):
    """Shapley-Shubik shares for single actors and oceanic chambers. Returns {organ: share}, shares sum to 1."""
    units = sorted({a for c in clauses for a in c["req"]})
    chambers = sorted({ch for c in clauses for ch in c["ch"]})
    n = len(units)
    out = {a: 0.0 for a in units + chambers}
    for i in units:
        others = [u for u in units if u != i]
        for k in range(len(others) + 1):
            for S in combinations(others, k):
                S = set(S)
                hi, lo = tau(clauses, S), tau(clauses, S | {i})
                out[i] += _int_poly(k, n - 1 - k, lo, min(hi, 1.0))
    for k in range(n + 1):
        for S in combinations(units, k):
            S = set(S)
            t = tau(clauses, S)
            if not 0 < t <= 1:
                continue
            at_t = {ch for c in clauses if set(c["req"]) <= S and c["ch"] and max(c["ch"].values()) == t
                    for ch, v in c["ch"].items() if v == t}
            # a chamber is pivotal only if dropping the clauses that need it at t would raise the threshold
            binding = {ch for ch in at_t
                       if tau([c for c in clauses if c["ch"].get(ch) != t], S) > t} or at_t
            w = t ** k * (1 - t) ** (n - k)
            for ch in binding:
                out[ch] += w / len(binding)
    total = sum(out.values())
    return {a: v / total for a, v in out.items()} if total > 0 else out


def veto_players(clauses):
    """Organs present in every winning clause (a chamber counts if every clause needs some share of it)."""
    sets = [set(c["req"]) | set(c["ch"]) for c in clauses]
    return sorted(set.intersection(*sets)) if sets else []


def blocking_minority(clauses, without=()):
    """Smallest share of the first chamber that blocks when every single actor except `without` agrees: 1 - threshold."""
    units = {a for c in clauses for a in c["req"]} - set(without)
    t = float("inf")
    for c in clauses:
        if set(c["req"]) <= units:
            t = min(t, c["ch"].get("L1", 0.0) if "L1" in c["ch"] else 0.0)
    if t == float("inf"):
        return None  # cannot be won at all without those actors
    return round(1 - t, 4) if t > 0 else 0.0


# ---------------- building decisions from variants ----------------
class Country:
    def __init__(self, code, R, has_pm_office=True, formal_monarch=False):
        self.code, self.R, self.sources, self.flags = code, R, {}, {}
        self.has_pm_office, self.formal_monarch = has_pm_office, formal_monarch

    def v(self, topic, field):
        r = self.R.get((topic, self.code))
        if r is None:
            return None
        return r["values"].get(field)

    def has(self, topic):
        return (topic, self.code) in self.R

    def use(self, dec, *topics):
        for t in topics:
            r = self.R.get((t, self.code))
            if r is not None:
                self.sources.setdefault(dec, {})[t] = {"articles": r.get("articles", []), "cytat": r["cytat"],
                                                       "korekty": [k["basis"] for k in r.get("korekty", [])]}

    def flag(self, dec, text):
        self.flags.setdefault(dec, []).append(text)

    # --- structure ---
    def bicameral(self):
        return self.v("legapp", "izby") == "dwie"

    def president_heads_government(self):
        v = self.v("hogelect", "szef_rzadu")
        if v in UNKNOWN and not self.has_pm_office:
            return True  # the text never names a prime minister or similar office
        return v == "glowa_panstwa"

    def g(self):
        """Government as an organ; in systems where the head of state runs the government it is the head of state."""
        return "HS" if self.president_heads_government() else "G"

    def hs_needs_government(self, prerogative):
        """Countersignature: does an act of the head of state need the government (or is it done on its advice)?"""
        if self.president_heads_government():
            return None
        k = self.v("hospow", "kontrasygnata")
        prer = self.v("hospow", "prerogatywy") or []
        if k == "dziala_na_wniosek":
            return "advice"
        if k == "ogolna" or (k == "z_wyjatkami" and prerogative not in prer):
            return "advice" if self.formal_monarch else "countersign"
        return None

    def hs_act(self, dec, prerogative, extra=()):
        """Clause requirements when the head of state acts: alone, with countersignature, or formally on advice."""
        mode = self.hs_needs_government(prerogative)
        if mode == "advice":
            self.flag(dec, "monarcha nie odpowiada, odpowiadają ministrowie (kontrasygnata): decyduje rząd" if self.formal_monarch
                      else "głowa państwa działa na wniosek rządu: decyduje rząd")
            return ["G", *extra]
        if mode == "countersign":
            return ["HS", "G", *extra]
        return ["HS", *extra]


def unit_name(c, value):
    return {"glowa_panstwa": "HS", "rzad": c.g(), "parlament": "L1", "sadownictwo": "J", "rada_sadownictwa": "J",
            "sad_konstytucyjny": "CC", "sad_specjalny": "J", "sad_najwyzszy": "J", "referendum": "P"}.get(value)


def chambers_at(c, thr, both=True):
    ch = {"L1": thr}
    if both and c.bicameral():
        ch["L2"] = thr
    return ch


def thr_of(c, dec, value, default=.5, what="próg"):
    if value in THR:
        return THR[value]
    c.flag(dec, f"{what} nie podany, przyjęto {fmt_thr(default)}")
    return default


def fmt_thr(t):
    return {.5: "większość", .6: "3/5", 2 / 3: "2/3", .75: "3/4"}.get(t, f"{t:.0%}")


def law_clauses(c, dec, l2_mode=None, hs_veto=None):
    """Ordinary-law style game: chambers, second-chamber veto, head-of-state veto with override."""
    l2 = l2_mode or c.v("legapp", "druga_izba_weto")
    base = [{"req": [], "ch": {"L1": .5}}]
    if c.bicameral():
        if l2 in ("bezwzgledne",):
            base = [{"req": [], "ch": {"L1": .5, "L2": .5}}]
        elif l2 in ("zawieszajace", "tylko_niektore"):
            p = c.v("legapp", "prog_przelamania")
            p = THR.get(p, .5)
            base = [{"req": [], "ch": {"L1": .5, "L2": .5}}, {"req": [], "ch": {"L1": p}}]
        elif l2 in UNKNOWN:
            c.flag(dec, "siła drugiej izby nie wynika z tekstu: przyjęto, że nie blokuje")
    rola = c.v("legapp", "glowa_panstwa_ustawy") if hs_veto is None else hs_veto
    weto = rola == "weto" or (rola in UNKNOWN and c.v("override", "kto_ma_weto") == "glowa_panstwa")
    if not weto:
        if rola in UNKNOWN and not c.has("override"):
            c.flag(dec, "rola głowy państwa przy ustawach nie wynika z tekstu")
        return base
    mode = c.hs_needs_government("weto_ustaw")
    actor = "G" if mode == "advice" else "HS"
    prog = c.v("override", "prog_odrzucenia")
    if prog == "weto_ostateczne":
        return [{"req": [actor], "ch": dict(cl["ch"])} for cl in base]
    q = thr_of(c, dec, prog, default=.5, what="próg odrzucenia weta")
    out = [{"req": [actor], "ch": dict(cl["ch"])} for cl in base]
    out += [{"req": [], "ch": {ch: max(v, q) for ch, v in cl["ch"].items()}} for cl in base]
    return out


def build(c: Country):
    D = {}
    # 1. ordinary law
    if c.has("legapp") or c.has("override"):
        c.use("ustawa", "legapp", "override", "hospow")
        D["ustawa"] = law_clauses(c, "ustawa")
    # 2. budget
    if c.has("budget") or c.has("legapp"):
        c.use("budzet", "budget", "legini", "legapp", "override")
        l2 = {"rowna": "bezwzgledne", "ograniczona": "zawieszajace", "brak": "brak"}.get(c.v("budget", "druga_izba_budzet"))
        hs = "brak" if c.v("budget", "weto_budzetu") == "nie" else None
        cl = law_clauses(c, "budzet", l2_mode=l2, hs_veto=hs)
        excl = c.v("legini", "wylaczna_inicjatywa_rzadu") or []
        prep = c.v("budget", "kto_przygotowuje")
        if "budzet" in excl or prep in ("rzad", "glowa_panstwa"):
            who = c.g() if prep != "glowa_panstwa" else "HS"
            cl = [{"req": sorted(set(x["req"]) | {who}), "ch": x["ch"]} for x in cl]
        if "projekt_wchodzi" in (c.v("budget", "skutek_nieuchwalenia") or []):
            c.flag("budzet", "gdy parlament nie uchwali budżetu, władza wykonawcza działa na podstawie swojego projektu")
        if "rozwiazanie_parlamentu" in (c.v("budget", "skutek_nieuchwalenia") or []):
            c.flag("budzet", "nieuchwalenie budżetu pozwala rozwiązać parlament")
        D["budzet"] = cl
    # 3. amendment
    if c.has("amend"):
        c.use("konstytucja", "amend")
        t = thr_of(c, "konstytucja", c.v("amend", "prog_parlament"), default=2 / 3)
        req = ["P"] if c.v("amend", "referendum") == "zawsze" else []
        if c.v("amend", "referendum") == "dla_czesci":
            c.flag("konstytucja", "referendum tylko dla części zmian: nie wliczono")
        D["konstytucja"] = [{"req": req, "ch": chambers_at(c, t, both=c.v("legapp", "druga_izba_weto") != "brak")}]
    # 4. appointing the head of government; where the head of state runs the government, forming the cabinet
    if c.president_heads_government():
        c.use("powolanie_rzadu", "hogelect", "cabdiss")
        if "parlament" in (c.v("hogelect", "kto_wskazuje") or []):
            D["powolanie_rzadu"] = [{"req": [], "ch": {"L1": .5}}]
            c.flag("powolanie_rzadu", "szefa rządu (prezydenta) wybiera parlament")
        else:
            D["powolanie_rzadu"] = [{"req": ["HS"], "ch": {}}]
            c.flag("powolanie_rzadu", "głowa państwa kieruje rządem i dobiera ministrów; zatwierdzanie ministrów przez izbę nie jest modelowane")
    elif c.has("hogelect"):
        c.use("powolanie_rzadu", "hogelect", "hospow")
        who = c.v("hogelect", "kto_wskazuje") or []
        inv = c.v("hogelect", "inwestytura")
        t = THR.get(c.v("hogelect", "prog_inwestytury"), .5)
        cl = []
        if "glowa_panstwa" in who:
            hs = c.hs_act("powolanie_rzadu", "powolanie_premiera")
            cl.append({"req": hs, "ch": {"L1": t} if inv in ("uprzednia", "nastepcza") else {}})
        if "parlament" in who or "wybor_przez_parlament" in (c.v("hogelect", "skutek_porazki") or []):
            cl.append({"req": [], "ch": {"L1": t}})
        if not cl:
            c.flag("powolanie_rzadu", "kto wskazuje premiera nie wynika z tekstu")
            cl = [{"req": [], "ch": {"L1": t}}] if inv in ("uprzednia", "nastepcza") else []
        if inv in UNKNOWN or inv is None:
            c.flag("powolanie_rzadu", "czy parlament głosuje nad rządem, nie wynika z tekstu")
        if cl:
            D["powolanie_rzadu"] = cl
    # 5. removing the government
    if c.has("cabdiss") or c.president_heads_government():
        c.use("odwolanie_rzadu", "cabdiss", "hogdlim")
        who = c.v("cabdiss", "kto_odwoluje") or []
        t = thr_of(c, "odwolanie_rzadu", c.v("cabdiss", "prog_wotum"), default=.5, what="próg wotum nieufności") if "parlament" in who else .5
        cl = []
        if "parlament" in who:
            cl.append({"req": [], "ch": {"L1": t}})
        if "druga_izba" in who:
            cl.append({"req": [], "ch": {"L2": t}})
        if c.president_heads_government() or ("glowa_panstwa" in who and not c.formal_monarch):
            cl.append({"req": ["HS"], "ch": {}})  # the head of state dismisses the prime minister or his own ministers
        elif "glowa_panstwa" in who:
            c.flag("odwolanie_rzadu", "formalne odwołanie przez monarchę (odpowiadają ministrowie) pominięto")
        if c.v("hogdlim", "konstruktywne_wotum") == "tak":
            c.flag("odwolanie_rzadu", "konstruktywne wotum: ta sama większość musi wskazać następcę")
        if c.v("cabdiss", "rozwiazanie_zamiast_dymisji") == "tak":
            c.flag("odwolanie_rzadu", "po wotum nieufności można rozwiązać parlament zamiast dymisji rządu")
        if cl:
            D["odwolanie_rzadu"] = cl
    # 6. dissolving parliament
    if c.has("legdiss"):
        c.use("rozwiazanie", "legdiss", "hospow")
        who = c.v("legdiss", "kto_moze") or []
        cl = []
        if "glowa_panstwa" in who:
            req = c.hs_act("rozwiazanie", "rozwiazanie_parlamentu")
            if "rzad" in who and "G" not in req:
                req = req + [c.g()] if c.g() != "HS" else req
            cl.append({"req": sorted(set(req)), "ch": {}})
        elif "rzad" in who:
            cl.append({"req": [c.g()], "ch": {}})
        if "parlament_sam" in who:
            cl.append({"req": [], "ch": {"L1": 2 / 3}})
            c.flag("rozwiazanie", "samorozwiązanie: przyjęto próg 2/3, jeśli tekst nie podaje innego")
        if "referendum" in who:
            cl.append({"req": ["P"], "ch": {}})
        if c.v("legdiss", "tylko_w_okreslonych_sytuacjach") == "tak":
            c.flag("rozwiazanie", "tylko w określonych sytuacjach (np. nieuchwalenie budżetu, brak rządu)")
        if cl:
            D["rozwiazanie"] = cl
    # 7. constitutional judges: k selectors -> 1/k each (same Shapley value whether they nominate jointly or by quota)
    if c.has("consel"):
        c.use("sedziowie_tk", "consel")
        sel = sorted({unit_name(c, x) for x in (c.v("consel", "kto_wybiera") or []) if unit_name(c, x)})
        if sel:
            D["sedziowie_tk"] = [{"req": [s for s in sel if s not in CHAMBERS],
                                   "ch": {s: (2 / 3 if c.v("consel", "wiekszosc_kwalifikowana") == "tak" else .5) for s in sel if s in CHAMBERS}}]
            if len(sel) > 1:
                c.flag("sedziowie_tk", "kilka organów: wspólny wybór albo podział puli, w obu przypadkach udział po równo")
    # 8. emergency
    if c.has("em"):
        c.use("stan_nadzwyczajny", "em", "hospow")
        who = unit_name(c, c.v("em", "kto_oglasza"))
        appr = c.v("em", "zatwierdzenie_parlamentu")
        if who is None:
            c.flag("stan_nadzwyczajny", "kto ogłasza, nie wynika z tekstu")
        elif who == "L1":
            D["stan_nadzwyczajny"] = [{"req": [], "ch": {"L1": .5}}]
        else:
            req = c.hs_act("stan_nadzwyczajny", "-") if who == "HS" else [who]
            ch = {"L1": .5} if appr in ("przed", "po_w_terminie", "moze_uchylic") else {}
            if appr == "moze_uchylic":
                c.flag("stan_nadzwyczajny", "parlament może tylko uchylić stan (słabsza kontrola niż zatwierdzenie)")
            if appr in UNKNOWN:
                c.flag("stan_nadzwyczajny", "udział parlamentu nie wynika z tekstu")
            D["stan_nadzwyczajny"] = [{"req": sorted(set(req)), "ch": ch}]
    # 9. war
    if c.has("war"):
        c.use("wojna", "war", "hospow")
        who = c.v("war", "kto_decyduje") or []
        t = 2 / 3 if c.v("war", "wiekszosc_kwalifikowana") == "tak" else .5
        req, ch = set(), {}
        for x in who:
            u = unit_name(c, x)
            if u == "L1":
                ch["L1"] = t
            elif u == "HS":
                req |= set(c.hs_act("wojna", "wojsko"))
            elif u:
                req.add(u)
        if c.v("war", "zgoda_parlamentu") in ("uprzednia", "nastepcza"):
            ch["L1"] = t
        if req or ch:
            D["wojna"] = [{"req": sorted(req), "ch": ch}]
    # 10. treaties
    if c.has("treat"):
        c.use("ratyfikacja", "treat", "hospow")
        who = unit_name(c, c.v("treat", "kto_ratyfikuje"))
        t = 2 / 3 if c.v("treat", "wiekszosc_kwalifikowana") == "tak" else .5
        req = set(c.hs_act("ratyfikacja", "-")) if who == "HS" else ({who} if who and who != "L1" else set())
        ch = chambers_at(c, t, both=c.v("legapp", "druga_izba_weto") == "bezwzgledne") if (who == "L1" or c.v("treat", "zgoda_parlamentu") in ("zawsze", "dla_kategorii")) else {}
        if t > .5:
            c.flag("ratyfikacja", "większość kwalifikowana (często tylko dla części umów, np. przekazania kompetencji)")
        if c.v("treat", "zgoda_parlamentu") == "dla_kategorii":
            c.flag("ratyfikacja", "zgoda parlamentu tylko dla części umów: model pokazuje umowy wymagające zgody")
        if req or ch:
            D["ratyfikacja"] = [{"req": sorted(req), "ch": ch}]
    # 11. removing the head of state
    if c.has("hosdiss"):
        c.use("usuniecie_glowy", "hosdiss")
        t = thr_of(c, "usuniecie_glowy", c.v("hosdiss", "prog_oskarzenia"), default=2 / 3, what="próg oskarżenia")
        judge = c.v("hosdiss", "kto_orzeka")
        ch, req = {"L1": t}, []
        if judge == "parlament" and c.bicameral():
            ch["L2"] = 2 / 3
        elif judge in ("sad_konstytucyjny", "sad_specjalny", "sad_najwyzszy", "referendum"):
            req = [unit_name(c, judge)]
        elif judge in UNKNOWN:
            c.flag("usuniecie_glowy", "kto orzeka, nie wynika z tekstu")
        D["usuniecie_glowy"] = [{"req": req, "ch": ch}]
    return D


def gov_type(c: Country):
    """Typology from the text: who the government answers to."""
    if c.president_heads_government():
        if "parlament" in (c.v("hogelect", "kto_wskazuje") or []):
            return "prezydent_z_parlamentu"
        return "prezydencki"
    who = [w for w in (c.v("cabdiss", "kto_odwoluje") or []) if not (w == "glowa_panstwa" and c.formal_monarch)]
    parl = "parlament" in who or "druga_izba" in who
    if c.v("hogelect", "szef_rzadu") != "odrebny_premier":
        return "nieustalony"
    if parl and "glowa_panstwa" in who:
        return "podwojna_odpowiedzialnosc"
    if parl:
        return "parlamentarny"
    if "glowa_panstwa" in who:
        return "rzad_glowy_panstwa"
    return "nieustalony"


TYPES = {"parlamentarny": "Rząd odpowiada przed parlamentem",
         "prezydent_z_parlamentu": "Prezydent kieruje rządem, ale wybiera go parlament",
         "podwojna_odpowiedzialnosc": "Rząd odpowiada przed parlamentem i głową państwa",
         "rzad_glowy_panstwa": "Premier zależny tylko od głowy państwa",
         "prezydencki": "Głowa państwa kieruje rządem",
         "nieustalony": "Nie wynika z tekstu"}


def indicators(c: Country, D):
    jrem = c.v("jrem", "kto_decyduje") or []
    access = c.v("conpow", "kto_moze_wniesc") or []
    diss = c.v("legdiss", "kto_moze") or []
    return {
        "opozycja_do_sadu": "mniejszosc_parlamentarna" in access or "kazdy_actio_popularis" in access,
        "obywatel_do_sadu": "obywatel_skarga" in access or "kazdy_actio_popularis" in access,
        "egzekutywa_odwoluje_sedziow": bool({"glowa_panstwa", "rzad"} & set(jrem)) and "rada_sadownictwa" not in jrem and "sadownictwo" not in jrem,
        "parlament_rozwiazywalny_swobodnie": bool({"glowa_panstwa", "rzad"} & set(diss)) and c.v("legdiss", "tylko_w_okreslonych_sytuacjach") == "nie",
        "konstruktywne_wotum": c.v("hogdlim", "konstruktywne_wotum") == "tak",
        "dekrety_z_moca_ustawy": c.v("hosdec", "moc") == "moc_ustawy",
    }


def country_model(code, R, has_pm_office=True, formal_monarch=False):
    c = Country(code, R, has_pm_office, formal_monarch)
    D = build(c)
    decisions = {}
    for dec, clauses in D.items():
        sh = shapley(clauses)
        hs_present = any("HS" in cl["req"] for cl in clauses)
        decisions[dec] = {
            "clauses": [{"req": cl["req"], "ch": {k: round(v, 4) for k, v in cl["ch"].items()}} for cl in clauses],
            "shares": {k: round(v, 4) for k, v in sorted(sh.items(), key=lambda x: -x[1]) if v > 1e-9},
            "veto": veto_players(clauses),
            "blokujaca_mniejszosc": blocking_minority(clauses) if any("L1" in cl["ch"] for cl in clauses) else None,
            # -1: the head of state's objection cannot be overcome
            "blokujaca_mniejszosc_bez_HS": (lambda b: -1 if b is None else b)(blocking_minority(clauses, without=("HS",)))
            if hs_present and any("L1" in cl["ch"] for cl in clauses) else None,
            "flags": c.flags.get(dec, []),
            "sources": c.sources.get(dec, {}),
        }
    complete = [d for d, x in decisions.items() if not any("nie wynika" in f for f in x["flags"])]
    profile = {o: 0.0 for o in ORGANS}
    for x in decisions.values():
        for o, s in x["shares"].items():
            profile[o] += s / len(decisions)
    blocks = {}
    for dec, x in decisions.items():
        for a in x["veto"]:
            for b, s in x["shares"].items():
                if b != a and s > 0:
                    blocks.setdefault(a, {}).setdefault(b, []).append(dec)
    control = [{"decision": dec, "target": c.g() if TARGET[dec] == "G" else TARGET[dec], "by": sorted(x["shares"])}
               for dec, x in decisions.items() if dec in TARGET]
    hhi = sum(v * v for v in profile.values())
    return {"code": code, "type": gov_type(c), "decisions": decisions, "complete": complete,
            "ranked": len(complete) >= MIN_DECISIONS,
            "profile": {k: round(v, 4) for k, v in profile.items()}, "hhi": round(hhi, 4),
            "blocks": blocks, "control": control, "indicators": indicators(c, D)}


def main():
    R = variants.load()
    codes = sorted({c for _, c in R})
    art = json.loads((HERE.parent / "warianty" / "articles_cache.json").read_text())
    # fallback for "who heads the government": no prime-minister-like office and no monarch in the whole text
    pm = {d["country_code"]: any(PM_WORDS.search(t) or MONARCH.search(t) for _, t in d["articles"]) for d in art.values()}
    formal = {d["country_code"]: any(FORMAL_MONARCH.search(t) for _, t in d["articles"]) for d in art.values()}
    out = {code: country_model(code, R, pm.get(code, True), formal.get(code, False)) for code in codes}
    out = {k: v for k, v in out.items() if v["decisions"]}
    meta = {"organs": ORGANS, "short": SHORT, "decisions": DECISIONS, "types": TYPES, "min_decisions": MIN_DECISIONS}
    (HERE / "wladza.json").write_text(json.dumps({"meta": meta, "countries": out}, ensure_ascii=False, indent=0), encoding="utf-8")
    with open(HERE / "wladza_kraje.csv", "w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(["kod", "typ", "decyzje", "kompletne", "w_rankingu", *[f"sila_{o}" for o in ORGANS], "hhi"])
        for code, m in out.items():
            w.writerow([code, m["type"], len(m["decisions"]), len(m["complete"]), int(m["ranked"]),
                        *[f'{m["profile"][o]:.4f}' for o in ORGANS], f'{m["hhi"]:.4f}'])
    with open(HERE / "wladza_decyzje.csv", "w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(["kod", "decyzja", *[f"sila_{o}" for o in ORGANS], "weto", "blokujaca_mniejszosc_izby", "blokujaca_mniejszosc_gdy_glowa_przeciw", "uwagi"])
        for code, m in out.items():
            for dec, x in m["decisions"].items():
                w.writerow([code, dec, *[f'{x["shares"].get(o, 0):.4f}' for o in ORGANS], " ".join(x["veto"]),
                            "" if x["blokujaca_mniejszosc"] is None else f'{x["blokujaca_mniejszosc"]:.4f}',
                            {None: "", -1: "nie_do_odrzucenia"}.get(x["blokujaca_mniejszosc_bez_HS"], f'{x["blokujaca_mniejszosc_bez_HS"]:.4f}' if x["blokujaca_mniejszosc_bez_HS"] is not None else ""),
                            "; ".join(x["flags"])])
    print(json.dumps({"countries": len(out), "ranked": sum(m["ranked"] for m in out.values())}))


if __name__ == "__main__":
    main()
