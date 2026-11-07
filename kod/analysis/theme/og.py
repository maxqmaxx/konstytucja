#!/usr/bin/env python3
"""Share images (Open Graph, 1200x630) for each section of the site, plus the favicon and the touch icon.

Rendered from small HTML cards with the site's Playwright/Chromium. Outputs analysis/theme/og/<section>.png,
analysis/theme/favicon.svg and analysis/theme/apple-touch-icon.png. Run when the headline numbers change:
  python3 analysis/theme/og.py
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
from html import escape
from pathlib import Path

HERE = Path(__file__).resolve().parent
A = HERE.parent
OUT = HERE / "og"
# Playwright for Node and a Chromium build: PW_MODULE / PW_CHROME, else the first ones found under the home directory
NODE_PW = os.environ.get("PW_MODULE") or next((str(p) for p in sorted(Path.home().glob("projects/*/node_modules/@playwright/test"))), "@playwright/test")
CHROME = os.environ.get("PW_CHROME") or next((str(p) for p in sorted(Path.home().glob(".cache/ms-playwright/chromium_headless_shell-*/chrome-headless-shell-linux64/chrome-headless-shell"))), "")

FAVICON = """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 64 64"><rect width="64" height="64" rx="12" fill="#142d3b"/>
<text x="32" y="46" text-anchor="middle" font-family="Georgia,serif" font-size="42" font-weight="700" fill="#e4eddf">§</text>
<rect x="12" y="52" width="40" height="4" rx="2" fill="#a8d1ba"/></svg>"""


def wladza_bars():
    """Poland / EU / world power profile bars for the Władza card."""
    p = A / "wladza" / "wladza.json"
    if not p.exists():
        return ""
    data = json.loads(p.read_text())["countries"]
    eu = {"AT", "BE", "BG", "HR", "CY", "CZ", "DK", "EE", "FI", "FR", "DE", "GR", "HU", "IE", "IT", "LV", "LT", "LU", "MT", "NL", "PL", "PT", "RO", "SK", "SI", "ES", "SE"}
    R = {k: m for k, m in data.items() if m["ranked"]}
    mean = lambda ks: {o: sum(R[k]["profile"][o] for k in ks) / len(ks) for o in R["PL"]["profile"]}  # noqa: E731
    rows = [("Polska", R["PL"]["profile"]), ("UE", mean([k for k in R if k in eu])), ("Świat", mean(list(R)))]
    col = {"L1": "#2f9b82", "L2": "#8cc7b3", "G": "#d8a86f", "HS": "#e0784a", "P": "#9c8ad0", "CC": "#9fb0bb", "J": "#c5ced4"}
    out = ""
    for name, prof in rows:
        segs = "".join(f'<i style="width:{v * 100:.2f}%;background:{col[o]}"></i>' for o, v in prof.items() if v > .003)
        out += f'<div class="row"><span>{name}</span><div class="bar">{segs}</div><b>{prof["HS"] * 100:.0f}%</b></div>'
    return f'<div class="bars">{out}<div class="cap">udział głowy państwa w 11 decyzjach</div></div>'


CARDS = {
    "default": ("Konstytucje świata", "Warsztat do myślenia o lepszej konstytucji", "188 konstytucji · 331 rozwiązań · Konstytucja RP na tle świata"),
    "mapa": ("Mapa rozwiązań", "Które konstytucje to mają?", "188 obowiązujących konstytucji na mapie świata"),
    "rp": ("Konstytucja RP na tle świata", "Artykuł po artykule", "Jak częste są rozwiązania polskiej konstytucji na świecie i w UE"),
    "problemy": ("Problemy polskiej debaty", "Od pytania do rozwiązań innych państw", "Sądy, stany nadzwyczajne, demokracja bezpośrednia, samorząd…"),
    "tematy": ("331 tematów konstytucyjnych", "Jak to zapisały inne państwa", "Przepisy 188 konstytucji ze streszczeniem i siłą normy"),
    "konstruktor": ("Konstruktor", "Złóż własny zestaw rozwiązań", "Najbliższe konstytucje świata, różnice wobec RP, napięcia"),
    "statystyki": ("Statystyki", "Ile słów i które rozwiązania", "Długość konstytucji, najpopularniejsze rozwiązania, UE a świat"),
    "wladza": ("Kto rządzi, kto blokuje", "Podział władzy w 188 konstytucjach", "Indeks Shapleya-Shubika · weto · przejęcie instytucji"),
    "symulator": ("Symulator reform", "Co zmieni jedna reguła?", "Weto, Senat, wybór TK i KRS: jak przesuwa się siła w Polsce"),
    "panstwa": ("Państwa", "222 państwa i terytoria", "Wydania konstytucji, wersje językowe, źródła"),
    "polska": ("Dla Polski", "24 propozycje zmian", "Korzyści, ryzyka, zabezpieczenia i inspiracje z innych państw"),
    "atlas": ("Atlas", "130 nietypowych zapisów", "Oryginalne, ważne i niebezpieczne rozwiązania z całego świata"),
    "teczka": ("Teczka robocza", "Zbieraj przepisy i propozycje", "Notatki i eksport z przypisami, tylko w Twojej przeglądarce"),
}

CARD_CSS = """*{box-sizing:border-box;margin:0}body{width:1200px;height:630px;background:#142d3b;color:#fff;font-family:system-ui,'DejaVu Sans',sans-serif;
padding:64px 72px;display:flex;flex-direction:column;position:relative;overflow:hidden}
.brand{display:flex;align-items:center;gap:16px;font:600 30px Georgia,'DejaVu Serif',serif;color:#e4eddf}.brand svg{width:56px;height:56px}
.eyebrow{margin-top:54px;font:700 24px system-ui,sans-serif;letter-spacing:.12em;text-transform:uppercase;color:#a8d1ba}
h1{margin-top:14px;font:700 68px/1.08 Georgia,'DejaVu Serif',serif;max-width:1000px}
.sub{margin-top:22px;font-size:30px;line-height:1.35;color:#dbe5e8;max-width:960px}
.foot{margin-top:auto;font-size:24px;color:#b7c9d2}.accent{position:absolute;left:0;bottom:0;width:100%;height:12px;background:#006858}
.bars{position:absolute;right:72px;top:250px;width:470px}.row{display:grid;grid-template-columns:90px 1fr 60px;gap:12px;align-items:center;margin:14px 0;font-size:24px}
.bar{display:flex;height:30px;border-radius:4px;overflow:hidden;background:#24404f}.bar i{display:block;height:100%}.row b{text-align:right}
.cap{font-size:18px;color:#b7c9d2;margin-top:4px}.withbars h1{max-width:600px;font-size:50px}.withbars .sub{max-width:580px;font-size:26px}"""


def card(key, eyebrow, title, sub):
    bars = wladza_bars() if key == "wladza" else ""
    return (f'<!doctype html><html lang="pl"><head><meta charset="utf-8"><style>{CARD_CSS}</style></head><body class="{"withbars" if bars else ""}">'
            f'<div class="brand">{FAVICON}Konstytucje świata</div><div class="eyebrow">{escape(eyebrow)}</div><h1>{escape(title)}</h1>'
            f'<p class="sub">{escape(sub)}</p>{bars}<div class="foot">maxqmaxx.github.io/konstytucja</div><div class="accent"></div></body></html>')


def main():
    OUT.mkdir(exist_ok=True)
    (HERE / "favicon.svg").write_text(FAVICON, encoding="utf-8")
    with tempfile.TemporaryDirectory() as d:
        d = Path(d)
        jobs = []
        for key, (eyebrow, title, sub) in CARDS.items():
            (d / f"{key}.html").write_text(card(key, eyebrow, title, sub), encoding="utf-8")
            jobs.append([str(d / f"{key}.html"), str(OUT / f"{key}.png"), 1200, 630])
        (d / "icon.html").write_text(f'<!doctype html><html><body style="margin:0;width:180px;height:180px">{FAVICON.replace("<svg ", "<svg width=180 height=180 ")}</body></html>', encoding="utf-8")
        jobs.append([str(d / "icon.html"), str(HERE / "apple-touch-icon.png"), 180, 180])
        (d / "run.cjs").write_text(f"""const {{ chromium }} = require({json.dumps(NODE_PW)});
(async()=>{{const b=await chromium.launch({{headless:true{(",executablePath:" + json.dumps(CHROME)) if CHROME else ""}}});
for(const [src,dst,w,h] of {json.dumps(jobs)}){{const p=await b.newPage({{viewport:{{width:w,height:h}}}});await p.goto('file://'+src);await p.screenshot({{path:dst}});await p.close();}}
await b.close();}})();""")
        subprocess.run(["node", str(d / "run.cjs")], check=True)
    print(json.dumps({"cards": len(CARDS), "out": str(OUT)}))


if __name__ == "__main__":
    sys.exit(main())
