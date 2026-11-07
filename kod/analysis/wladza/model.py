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
sys.path.insert(0, str(HERE))
import ccp_ref  # noqa: E402

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
CCP_OVERPCT = {"2": .5, "3": .6, "4": 2 / 3, "5": .75}


class Country:
    def __init__(self, code, R, has_pm_office=True, formal_monarch=False, ccp=None):
        self.code, self.R, self.sources, self.flags = code, R, {}, {}
        self.has_pm_office, self.formal_monarch = has_pm_office, formal_monarch
        self.ccp = ccp or {}  # expert coding (CCP v5, 2023): fills only what our reading left open, always flagged

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
        v = self.v("legapp", "izby")
        if v in UNKNOWN and self.ccp.get("housenum") in ("2", "3"):
            return self.ccp["housenum"] == "3"  # CCP: 2 = one chamber, 3 = two
        return v == "dwie"

    def hs_selection(self):
        """CCP HOSELECT: dziedziczna / wybory / wybor_posredni / None."""
        return {"1": "dziedziczna", "2": "wybory", "3": "wybor_posredni"}.get(self.ccp.get("hoselect"))

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
    if prog in UNKNOWN and c.ccp.get("overpct") in CCP_OVERPCT:
        q = CCP_OVERPCT[c.ccp["overpct"]]
        c.flag(dec, f"próg odrzucenia weta ({fmt_thr(q)}) uzupełniony z kodowania CCP")
        out = [{"req": [actor], "ch": dict(cl["ch"])} for cl in base]
        return out + [{"req": [], "ch": {ch: max(v, q) for ch, v in cl["ch"].items()}} for cl in base]
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
    """Typology from the text (who heads the government, whom it answers to) and, from CCP, how the head of state is chosen."""
    sel = c.hs_selection()
    if c.president_heads_government():
        if "parlament" in (c.v("hogelect", "kto_wskazuje") or []):  # CCP's "elite group" also covers electoral colleges
            return "prezydent_z_parlamentu"
        return "prezydencki"
    who = [w for w in (c.v("cabdiss", "kto_odwoluje") or []) if not (w == "glowa_panstwa" and c.formal_monarch)]
    parl = "parlament" in who or "druga_izba" in who
    hs = "glowa_panstwa" in who
    if c.v("hogelect", "szef_rzadu") != "odrebny_premier" and not (sel and (parl or hs)):
        return "nieustalony"
    if sel == "dziedziczna" or c.formal_monarch:
        return "monarchia_parlamentarna" if parl else ("rzad_glowy_panstwa" if hs else "nieustalony")
    if sel == "wybory":
        if parl and hs:
            return "polprezydencki_prezydencko_parlamentarny"
        if parl:
            return "polprezydencki_premierowski"
    if parl and hs:
        return "podwojna_odpowiedzialnosc"
    if parl:
        return "parlamentarny"
    if hs:
        return "rzad_glowy_panstwa"
    return "nieustalony"


TYPES = {"parlamentarny": "Parlamentarny (głowa państwa wybierana pośrednio)",
         "monarchia_parlamentarna": "Monarchia parlamentarna",
         "polprezydencki_premierowski": "Półprezydencki: prezydent z wyborów, rząd odpowiada przed parlamentem",
         "polprezydencki_prezydencko_parlamentarny": "Półprezydencki: rząd odpowiada przed parlamentem i prezydentem",
         "podwojna_odpowiedzialnosc": "Rząd odpowiada przed parlamentem i głową państwa (głowa wybierana pośrednio)",
         "prezydencki": "Prezydencki: głowa państwa kieruje rządem",
         "prezydent_z_parlamentu": "Prezydent kieruje rządem, ale wybiera go parlament",
         "rzad_glowy_panstwa": "Rząd zależny tylko od głowy państwa",
         "nieustalony": "Nie wynika z tekstu"}
# coarse groups used for comparisons and sanity checks
TYPE_GROUP = {"prezydencki": "prezydencki", "prezydent_z_parlamentu": "prezydencki", "rzad_glowy_panstwa": "silna_glowa",
              "polprezydencki_premierowski": "polprezydencki", "polprezydencki_prezydencko_parlamentarny": "polprezydencki",
              "parlamentarny": "parlamentarny", "monarchia_parlamentarna": "parlamentarny", "podwojna_odpowiedzialnosc": "polprezydencki",
              "nieustalony": "nieustalony"}


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


# ---------------- capture: what a political majority can take over on its own ----------------
SCENARIOS = [("S1", "Większość w pierwszej izbie (i rząd)", .5, False), ("S2", "Większość i głowa państwa", .5, True),
             ("S3", "3/5 mandatów (z głową państwa, jeśli współdecyduje)", .6, True), ("S4", "2/3 mandatów (z głową państwa, jeśli współdecyduje)", 2 / 3, True)]
INSTITUTIONS = {"tk": "Sąd konstytucyjny", "krs": "Rada sądownictwa", "rpo": "Rzecznik praw (ombudsman)", "bank": "Bank centralny",
                "prokurator": "Prokurator generalny", "wybory": "Organ wyborczy", "konstytucja": "Zmiana konstytucji"}
NONPOLITICAL = {"J", "P", "O"}  # judges, the people, opposition/parties: a ruling majority does not control them


def capture(c: Country):
    """For each institution named in the constitution: who selects it and at what majority, and the weakest scenario
    in which a ruling camp controls every selector. 'ustawa': the constitution names the institution but leaves the
    selection to ordinary law, so the legislative majority decides."""
    gmap = {"parlament": "L1", "glowa_panstwa": "HS", "rzad": c.g(), "sadownictwo": "J", "rada_sadownictwa": "J", "sady": "J",
            "sedziowie": "J", "partie": "O", "rada_prokuratorska": "J", "inne": None}
    out = {}

    def add(key, topic, sel, thr=.5, note=""):
        if not c.has(topic):
            return
        sel = [x for x in sel if x]
        if not sel:
            out[key] = {"selectors": [], "thr": None, "level": "ustawa", "note": "konstytucja nie określa, kto wybiera: decyduje ustawa"}
            return
        out[key] = {"selectors": sorted(set(sel)), "thr": thr, "note": note}
    sel = [gmap.get(x) for x in (c.v("consel", "kto_wybiera") or [])]
    add("tk", "consel", sel, 2 / 3 if c.v("consel", "wiekszosc_kwalifikowana") == "tak" else .5)
    jc = c.v("jc", "kto_wybiera_sedziow_czlonkow")
    add("krs", "jc", {"sedziowie": ["J"], "parlament": ["L1"], "mieszany": ["J", "L1"]}.get(jc, []))
    om = c.v("ombuds", "kto_wybiera")
    add("rpo", "ombuds", {"parlament": ["L1"], "glowa_panstwa": ["HS"], "rzad": [c.g()], "mieszany": ["L1", "HS"]}.get(om, []))
    add("bank", "bank", [gmap.get(x) for x in (c.v("bank", "kto_powoluje_prezesa") or [])])
    add("prokurator", "atgen", [gmap.get(x) for x in (c.v("atgen", "kto_powoluje") or [])])
    add("wybory", "ecom", [gmap.get(x) for x in (c.v("ecom", "kto_powoluje") or [])])
    if c.has("amend"):
        t = THR.get(c.v("amend", "prog_parlament"), 2 / 3)
        out["konstytucja"] = {"selectors": ["L1"] + (["P"] if c.v("amend", "referendum") == "zawsze" else []), "thr": t, "note": ""}

    def controlled(actor, q, hs_allied):
        if actor == "L1":
            return True
        if actor == "HS":
            return hs_allied or c.hs_needs_government("-") == "advice"
        if actor == "G":
            return hs_allied or (not c.president_heads_government() and q >= .5)
        return False
    for key, x in out.items():
        if x.get("level") == "ustawa":
            continue
        x["level"] = "poza_polityka"
        for sid, _, q, allied in SCENARIOS:
            if (x["thr"] or .5) <= q + 1e-9 and all(controlled(a, q, allied) for a in x["selectors"]):
                x["level"] = sid
                break
        x["czesciowo"] = x["level"] == "poza_polityka" and any(a not in NONPOLITICAL for a in x["selectors"])
        x["thr"] = None if x["thr"] is None else round(x["thr"], 4)
    return out


# ---------------- de jure judicial independence (text only) ----------------
JUD = {"tk_wybor_wielu": "Sędziów TK wybiera więcej niż jeden organ albo większość kwalifikowana",
       "tk_kadencja": "Kadencja sędziów TK co najmniej 9 lat albo do wieku emerytalnego",
       "tk_jedna_kadencja": "Sędzia TK nie może być wybrany ponownie",
       "rada_sedziowie": "Rada sądownictwa z większością sędziów",
       "rada_wybor_sedziow": "Sędziowie-członkowie rady wybierani przez sędziów",
       "nieusuwalnosc": "Nieusuwalność sędziów",
       "odwolanie_sadowe": "O odwołaniu sędziego decyduje organ sądowy",
       "przyczyny": "Odwołanie tylko z przyczyn określonych w ustawie",
       "dostep": "Mniejszość parlamentarna lub obywatel może zaskarżyć ustawę do TK",
       "wyroki": "Wyrok TK uchyla niekonstytucyjny przepis"}


def judicial(c: Country):
    sel = {x for x in (c.v("consel", "kto_wybiera") or [])}
    term = c.v("conterm", "lata")
    jr = set(c.v("jrem", "kto_decyduje") or [])
    acc = set(c.v("conpow", "kto_moze_wniesc") or [])
    has_cc, has_jc, has_rem = c.has("consel") or c.has("conpow") or c.has("conterm"), c.has("jc"), c.has("jrem")
    comp = {
        "tk_wybor_wielu": len(sel) >= 2 or c.v("consel", "wiekszosc_kwalifikowana") == "tak",
        "tk_kadencja": (isinstance(term, (int, float)) and term >= 9) or c.v("conterm", "dozywotnio_lub_do_wieku") == "tak",
        "tk_jedna_kadencja": c.v("conlim", "ponowny_wybor") == "zakazany",
        "rada_sedziowie": c.v("jc", "sedziowie_wiekszoscia") == "tak",
        "rada_wybor_sedziow": c.v("jc", "kto_wybiera_sedziow_czlonkow") == "sedziowie",
        "nieusuwalnosc": c.v("jrem", "nieusuwalnosc") == "tak",
        "odwolanie_sadowe": bool(jr) and jr <= {"sadownictwo", "rada_sadownictwa"},
        "przyczyny": c.v("jrem", "tylko_z_przyczyn_w_ustawie") == "tak",
        "dostep": bool(acc & {"mniejszosc_parlamentarna", "obywatel_skarga", "kazdy_actio_popularis"}),
        "wyroki": c.v("conpow", "skutek_wyroku") == "utrata_mocy",
    }
    # components about an institution the constitution does not have are not counted (e.g. no constitutional court)
    na = set()
    if not has_cc:
        na |= {"tk_wybor_wielu", "tk_kadencja", "tk_jedna_kadencja", "dostep", "wyroki"}
    if not has_jc:
        na |= {"rada_sedziowie", "rada_wybor_sedziow"}
    if not has_rem:
        na |= {"nieusuwalnosc", "odwolanie_sadowe", "przyczyny"}
    app = [k for k in comp if k not in na]
    comp = {k: (None if k in na else v) for k, v in comp.items()}
    score = round(sum(bool(comp[k]) for k in app) / len(app) * 100, 1) if len(app) >= 4 else None
    return {"components": comp, "score": score, "applicable": len(app)}


# ---------------- robustness variants ----------------
WEIGHTS = {"ustawa": 3, "budzet": 3, "konstytucja": 2, "powolanie_rzadu": 2, "odwolanie_rzadu": 2}
VARIANTS = {"bazowy": "Model bazowy",
            "wagi": "Wagi decyzji (ustawa i budżet x3, konstytucja i rząd x2)",
            "bez_reguly_monarchy": "Bez reguły dla monarchii (kontrasygnata zawsze dzieli siłę)",
            "progi_latwe": "Większości kwalifikowane łatwe (każdy próg jak zwykła większość)",
            "progi_trudne": "Większości kwalifikowane nieosiągalne",
            "tylko_kompletne": "Tylko decyzje bez założeń"}


def transform(clauses, mode):
    if mode == "progi_latwe":
        return [{"req": c["req"], "ch": {k: min(v, .5) for k, v in c["ch"].items()}} for c in clauses]
    if mode == "progi_trudne":
        return [{"req": c["req"], "ch": {k: (1.0 if v > .5 else v) for k, v in c["ch"].items()}} for c in clauses]
    return clauses


def profile_variant(code, R, pm, formal, ccp, variant):
    c = Country(code, R, pm, False if variant == "bez_reguly_monarchy" else formal, ccp)
    D = build(c)
    if variant == "tylko_kompletne":
        D = {d: cl for d, cl in D.items() if not c.flags.get(d)}
    if not D:
        return None
    prof, tot = {o: 0.0 for o in ORGANS}, 0
    for d, cl in D.items():
        w = WEIGHTS.get(d, 1) if variant == "wagi" else 1
        for o, v in shapley(transform(cl, variant)).items():
            prof[o] += v * w
        tot += w
    return {o: v / tot for o, v in prof.items()}


def country_model(code, R, has_pm_office=True, formal_monarch=False, ccp=None):
    c = Country(code, R, has_pm_office, formal_monarch, ccp)
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
    return {"code": code, "type": gov_type(c), "hs_selection": c.hs_selection(), "decisions": decisions, "complete": complete,
            "przejecie": capture(c), "sady": judicial(c),
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
    ccp = ccp_ref.load()
    out = {code: country_model(code, R, pm.get(code, True), formal.get(code, False), ccp.get(code)) for code in codes}
    out = {k: v for k, v in out.items() if v["decisions"]}
    # robustness: head-of-state share and rank under each variant (ranked countries only)
    ranked = [k for k, m in out.items() if m["ranked"]]
    var = {}
    for v in VARIANTS:
        profs = {k: profile_variant(k, R, pm.get(k, True), formal.get(k, False), ccp.get(k), v) for k in ranked}
        order = sorted((k for k in ranked if profs[k]), key=lambda k: -profs[k]["HS"])
        var[v] = {k: {"HS": round(profs[k]["HS"], 4), "parl": round(profs[k]["L1"] + profs[k]["L2"], 4), "rank": order.index(k) + 1}
                  for k in order}
    for k in ranked:
        out[k]["warianty"] = {v: var[v].get(k) for v in VARIANTS}
        rs = [x["rank"] for x in out[k]["warianty"].values() if x]
        out[k]["rank_range"] = [min(rs), max(rs)]
    meta = {"organs": ORGANS, "short": SHORT, "decisions": DECISIONS, "types": TYPES, "type_group": TYPE_GROUP,
            "min_decisions": MIN_DECISIONS, "institutions": INSTITUTIONS, "scenarios": [[a, b] for a, b, *_ in SCENARIOS],
            "judicial": JUD, "variants": VARIANTS, "ccp": bool(ccp)}
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
    with open(HERE / "wladza_przejecie.csv", "w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(["kod", "instytucja", "kto_wybiera", "prog_izby", "poziom_przejecia", "czesciowo", "uwagi"])
        for code, m in out.items():
            for inst, x in m["przejecie"].items():
                w.writerow([code, inst, " ".join(x["selectors"]), "" if x["thr"] is None else f'{x["thr"]:.4f}', x["level"], int(x.get("czesciowo", False)), x["note"]])
    with open(HERE / "wladza_sady.csv", "w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(["kod", "indeks_0_100", *JUD])
        for code, m in out.items():
            w.writerow([code, "" if m["sady"]["score"] is None else m["sady"]["score"],
                        *["" if m["sady"]["components"][k] is None else int(m["sady"]["components"][k]) for k in JUD]])
    with open(HERE / "wladza_warianty.csv", "w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(["kod", *[f"{v}_{x}" for v in VARIANTS for x in ("sila_HS", "miejsce")]])
        for code in ranked:
            w.writerow([code, *[y for v in VARIANTS for y in ((f'{out[code]["warianty"][v]["HS"]:.4f}', out[code]["warianty"][v]["rank"]) if out[code]["warianty"][v] else ("", ""))]])
    print(json.dumps({"countries": len(out), "ranked": sum(m["ranked"] for m in out.values()), "ccp": len(ccp)}))


if __name__ == "__main__":
    main()
