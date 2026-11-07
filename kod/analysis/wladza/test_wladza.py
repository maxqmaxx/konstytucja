import json
import sys
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import model  # noqa: E402

LAW = lambda q, l2=None: ([{"req": ["HS"], "ch": {"L1": .5, **({"L2": .5} if l2 else {})}},
                          {"req": [], "ch": {"L1": q, **({"L2": q} if l2 else {})}}])


def rec(topic, **values):
    return {"values": values, "articles": ["Article 1"], "cytat": "x", "korekty": []}


class Games(unittest.TestCase):
    def assertShares(self, clauses, expected):
        sh = model.shapley(clauses)
        self.assertAlmostEqual(sum(sh.values()), 1.0, places=9)
        for k, v in expected.items():
            self.assertAlmostEqual(sh.get(k, 0), v, places=6, msg=f"{k}: {sh}")

    def test_single_chamber(self):
        self.assertShares([{"req": [], "ch": {"L1": .5}}], {"L1": 1})

    def test_dictator(self):
        self.assertShares([{"req": ["HS"], "ch": {}}], {"HS": 1})

    def test_unanimity(self):
        self.assertShares([{"req": ["HS", "G"], "ch": {}}], {"HS": .5, "G": .5})
        self.assertShares([{"req": ["G"], "ch": {"L1": .5}}], {"G": .5, "L1": .5})

    def test_veto_window(self):
        # veto overridden by 3/5: head of state holds the 50-60% window
        self.assertShares(LAW(.6), {"HS": .1, "L1": .9})
        self.assertShares(LAW(2 / 3), {"HS": 1 / 6, "L1": 5 / 6})
        self.assertShares(LAW(.5), {"HS": 0, "L1": 1})
        self.assertShares([{"req": ["HS"], "ch": {"L1": .5}}], {"HS": .5, "L1": .5})

    def test_two_chambers_and_president(self):
        self.assertShares(LAW(2 / 3, l2=True), {"HS": 1 / 6, "L1": 5 / 12, "L2": 5 / 12})

    def test_veto_and_blocking(self):
        amend = [{"req": [], "ch": {"L1": 2 / 3}}]
        self.assertAlmostEqual(model.blocking_minority(amend), 1 / 3, places=3)
        self.assertEqual(model.veto_players(LAW(.6)), ["L1"])
        self.assertAlmostEqual(model.blocking_minority(LAW(.6)), .5)
        self.assertAlmostEqual(model.blocking_minority(LAW(.6), without=("HS",)), .4)


class Countries(unittest.TestCase):
    def test_polish_like(self):
        R = {(t, "XX"): rec(t, **v) for t, v in {
            "legapp": dict(izby="dwie", druga_izba_weto="zawieszajace", prog_przelamania="bezwzgledna", glowa_panstwa_ustawy="weto"),
            "override": dict(prog_odrzucenia="trzy_piate", kto_ma_weto="glowa_panstwa"),
            "hospow": dict(kontrasygnata="z_wyjatkami", prerogatywy=["weto_ustaw", "rozwiazanie_parlamentu"]),
            "hogelect": dict(szef_rzadu="odrebny_premier", kto_wskazuje=["glowa_panstwa", "parlament"], inwestytura="nastepcza",
                             prog_inwestytury="bezwzgledna", skutek_porazki=["wybor_przez_parlament"]),
            "cabdiss": dict(kto_odwoluje=["parlament"], prog_wotum="bezwzgledna"),
            "budget": dict(kto_przygotowuje="rzad", skutek_nieuchwalenia=[], druga_izba_budzet="ograniczona", weto_budzetu="nie"),
            "legini": dict(wylaczna_inicjatywa_rzadu=["budzet"]),
            "amend": dict(prog_parlament="dwie_trzecie", referendum="fakultatywne"),
        }.items()}
        m = model.country_model("XX", R)
        d = m["decisions"]
        self.assertAlmostEqual(d["ustawa"]["shares"]["HS"], .1, places=4)
        self.assertNotIn("L2", d["ustawa"]["shares"])  # suspensive veto overridable by a majority: no power
        self.assertAlmostEqual(d["budzet"]["shares"]["G"], .5, places=4)
        self.assertNotIn("HS", d["powolanie_rzadu"]["shares"])  # parliament can elect alone at the same threshold
        self.assertEqual(m["type"], "parlamentarny")
        self.assertAlmostEqual(sum(m["profile"].values()), 1, places=3)
        self.assertIn(("odwolanie_rzadu", "G"), [(c["decision"], c["target"]) for c in m["control"]])

    def test_presidential_fallback(self):
        R = {("cabdiss", "YY"): rec("cabdiss", kto_odwoluje=[])}
        c = model.Country("YY", R, has_pm_office=False)
        self.assertTrue(c.president_heads_government())
        self.assertEqual(c.g(), "HS")


class Output(unittest.TestCase):
    def test_built_data(self):
        path = HERE / "wladza.json"
        if not path.exists():
            self.skipTest("run model.py first")
        data = json.loads(path.read_text())["countries"]
        for code, m in data.items():
            for dec, x in m["decisions"].items():
                self.assertAlmostEqual(sum(x["shares"].values()), 1, places=3, msg=f"{code} {dec}")
                self.assertIn(dec, model.DECISIONS)
        ranked = {k: m for k, m in data.items() if m["ranked"]}
        mean = lambda t: sum(m["profile"]["HS"] for m in ranked.values() if m["type"] == t) / max(1, sum(m["type"] == t for m in ranked.values()))
        self.assertGreater(mean("prezydencki"), 2 * mean("parlamentarny"))  # expectation written before computing
        for strong, weak in [("US", "DE"), ("BR", "PL"), ("SA", "DE"), ("RU", "HU")]:
            if strong in data and weak in data:
                self.assertGreater(data[strong]["profile"]["HS"], data[weak]["profile"]["HS"], f"{strong} vs {weak}")
        if "PL" in data:
            pl = data["PL"]["decisions"]
            self.assertAlmostEqual(pl["ustawa"]["shares"]["HS"], .1, places=3)  # art. 122 ust. 5: 3/5 override
            self.assertAlmostEqual(pl["konstytucja"]["blokujaca_mniejszosc"], 1 / 3, places=3)  # art. 235 ust. 4


if __name__ == "__main__":
    unittest.main()
