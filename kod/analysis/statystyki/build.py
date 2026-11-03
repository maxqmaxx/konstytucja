#!/usr/bin/env python3
"""Statystyki: how long constitutions are and how popular the 331 solutions are (world, since 2000, EU), with Poland marked.

Charts are inline SVG generated here (no libraries), with a hover tooltip and a table fallback.
Lengths are word counts of the English editions on Constitute (comparable across countries); they are computed
from analysis/warianty/articles_cache.json when present and kept in dlugosci.csv.
Usage: python3 analysis/statystyki/build.py
"""
from __future__ import annotations

import csv
import json
import math
import statistics
import sys
from html import escape
from pathlib import Path

HERE = Path(__file__).resolve().parent
A = HERE.parent
sys.path.insert(0, str(A / "features"))
sys.path.insert(0, str(A / "panstwa"))
import ccp_data  # noqa: E402
from build import page, name_pl  # noqa: E402

EU27 = {"AT", "BE", "BG", "HR", "CY", "CZ", "DK", "EE", "FI", "FR", "DE", "GR", "HU", "IE", "IT",
        "LV", "LT", "LU", "MT", "NL", "PL", "PT", "RO", "SK", "SI", "ES", "SE"}
LEN_CSV = HERE / "dlugosci.csv"

CSS = """
.stat-hero{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:1px;background:var(--line);border:1px solid var(--line);margin:18px 0 8px}
.stat-hero div{background:#fff;padding:14px 16px}.stat-hero b{display:block;font:600 30px/1.1 Georgia,serif}.stat-hero span{font-size:13px;color:var(--muted)}
.chart{background:#fff;border:1px solid var(--line);padding:14px 16px 10px;margin:14px 0 22px}
.chart h3{font:600 18px/1.3 Georgia,serif;margin:0 0 2px}.chart .note{margin:2px 0 8px}
.chart svg{width:100%;height:auto;display:block;overflow:visible}
.chart text{font:12px system-ui,sans-serif;fill:#5a666d}.chart .lbl{fill:#1d2a35;font-weight:600}
.chart .axis{stroke:#9aa69c;stroke-width:1}.chart .grid{stroke:#e3e8df;stroke-width:1}
.chart .m{fill:#006858}.chart .m2{fill:#c8d1c6}.chart .pl{fill:#b4532a}.chart .neg{fill:#c49260}
.chart .dot{fill:#006858;fill-opacity:.5;stroke:#fff;stroke-width:1}.chart .dot.pl{fill:#b4532a;fill-opacity:1;stroke:#fff;stroke-width:2}
.chart [data-tip]:hover{opacity:.75;cursor:default}.chart .hit{fill:transparent}
.legend{display:flex;flex-wrap:wrap;gap:6px 16px;font-size:13px;color:var(--muted);margin:4px 0}.legend i{display:inline-block;width:12px;height:12px;border-radius:2px;margin-right:6px;vertical-align:-1px}
.legend .k1{background:#006858}.legend .k2{background:#c8d1c6}.legend .k3{background:#b4532a}.legend .k4{background:#c49260}
#tip{position:fixed;z-index:60;pointer-events:none;background:#1d2a35;color:#fff;font:13px/1.4 system-ui,sans-serif;padding:7px 10px;border-radius:4px;max-width:320px;box-shadow:0 4px 14px #0003}
.two{display:grid;grid-template-columns:1fr 1fr;gap:18px}
.chart table{width:100%;border-collapse:collapse;font-size:13px}.chart td,.chart th{padding:4px 6px;border-bottom:1px solid var(--line);text-align:left}.chart td.n{text-align:right;font-variant-numeric:tabular-nums}
@media (max-width:800px){.stat-hero{grid-template-columns:1fr 1fr}.two{grid-template-columns:1fr}}
"""

TIP_JS = """(()=>{const t=document.createElement('div');t.id='tip';t.hidden=true;document.body.appendChild(t);
document.addEventListener('mouseover',e=>{const el=e.target.closest('[data-tip]');if(!el){t.hidden=true;return;}t.textContent=el.dataset.tip;t.hidden=false;});
document.addEventListener('mousemove',e=>{if(t.hidden)return;const x=Math.min(e.clientX+14,innerWidth-t.offsetWidth-8);t.style.left=x+'px';t.style.top=(e.clientY+14)+'px';});
document.addEventListener('focusin',e=>{const el=e.target.closest('[data-tip]');if(el){const r=el.getBoundingClientRect();t.textContent=el.dataset.tip;t.hidden=false;t.style.left=r.left+'px';t.style.top=(r.bottom+6)+'px';}});
document.addEventListener('focusout',()=>t.hidden=true);})();"""


def lengths(ccp):
    cache = A / "warianty" / "articles_cache.json"
    if cache.exists():
        art = json.loads(cache.read_text())
        rows = []
        for doc_id, d in sorted(art.items()):
            c = d["country_code"]
            if c not in ccp.by_code:
                continue
            words = sum(len(t.split()) for _, t in d["articles"])
            arts = sum(1 for label, _ in d["articles"] if label.lower().startswith(("article", "art", "section")))
            rows.append({"kod": c, "slowa": words, "artykuly": arts})
        with open(LEN_CSV, "w", encoding="utf-8", newline="") as fh:
            w = csv.DictWriter(fh, fieldnames=["kod", "slowa", "artykuly"])
            w.writeheader()
            w.writerows(rows)
    return {r["kod"]: {"words": int(r["slowa"]), "arts": int(r["artykuly"])} for r in csv.DictReader(open(LEN_CSV, encoding="utf-8"))}


def year(d):
    y = str(d.get("year_enacted") or "")[:4]
    return int(y) if y.isdigit() else None


def fmt(n):
    return f"{n:,}".replace(",", " ")


def tip(s):
    return escape(s, quote=True)


def chart(title, note, svg, extra=""):
    return f'<figure class="chart"><h3>{escape(title)}</h3><p class="note">{note}</p>{svg}{extra}</figure>'


def histogram_lengths(L, ccp):
    bins = [(0, 5000, "< 5"), (5000, 10000, "5–10"), (10000, 15000, "10–15"), (15000, 20000, "15–20"), (20000, 30000, "20–30"),
            (30000, 50000, "30–50"), (50000, 100000, "50–100"), (100000, 10 ** 9, "> 100")]
    groups = [[c for c, v in L.items() if lo <= v["words"] < hi] for lo, hi, _ in bins]
    W, H, l, b, top = 720, 260, 40, 34, 26
    mx = max(map(len, groups))
    bw = (W - l - 10) / len(bins)
    parts = [f'<line class="axis" x1="{l}" x2="{W - 10}" y1="{H - b}" y2="{H - b}"/>']
    for k in range(0, mx + 1, 10):
        y = H - b - k / mx * (H - b - top)
        parts.append(f'<line class="grid" x1="{l}" x2="{W - 10}" y1="{y:.1f}" y2="{y:.1f}"/><text x="{l - 6}" y="{y + 4:.1f}" text-anchor="end">{k}</text>')
    for i, ((lo, hi, lab), g) in enumerate(zip(bins, groups)):
        x = l + i * bw + 3
        h = len(g) / mx * (H - b - top)
        names = ", ".join(sorted(name_pl(c, c) for c in g))
        cls = "m"
        parts.append(f'<rect class="{cls}" x="{x:.1f}" y="{H - b - h:.1f}" width="{bw - 6:.1f}" height="{h:.1f}" rx="4" data-tip="{tip(f"{lab} tys. słów: {len(g)} konstytucji. {names}")}" tabindex="0"/>')
        parts.append(f'<text x="{x + (bw - 6) / 2:.1f}" y="{H - b - h - 6:.1f}" text-anchor="middle" class="lbl">{len(g)}</text>')
        parts.append(f'<text x="{x + (bw - 6) / 2:.1f}" y="{H - b + 16}" text-anchor="middle">{lab}</text>')
        if "PL" in g:
            parts.append(f'<text x="{x + (bw - 6) / 2:.1f}" y="{H - b - h - 22:.1f}" text-anchor="middle" class="lbl" style="fill:#b4532a">▼ Polska</text>')
    parts.append(f'<text x="{W / 2}" y="{H - 2}" text-anchor="middle">tysiące słów (wydanie angielskie)</text>')
    return f'<svg viewBox="0 0 {W} {H}" role="img" aria-label="Histogram długości konstytucji">{"".join(parts)}</svg>'


def scatter_year(L, ccp):
    W, H, l, b, top, r = 720, 330, 52, 34, 12, 14
    pts = [(c, year(ccp.by_code[c]), v["words"]) for c, v in L.items() if (year(ccp.by_code[c]) or 0) >= 1780]
    x0, x1 = 1780, 2030
    y0, y1 = math.log10(2000), math.log10(400000)
    X = lambda yr: l + (yr - x0) / (x1 - x0) * (W - l - r)
    Y = lambda w: H - b - (math.log10(w) - y0) / (y1 - y0) * (H - b - top)
    parts = [f'<line class="axis" x1="{l}" x2="{W - r}" y1="{H - b}" y2="{H - b}"/>']
    for w in (2000, 5000, 10000, 20000, 50000, 100000, 200000):
        parts.append(f'<line class="grid" x1="{l}" x2="{W - r}" y1="{Y(w):.1f}" y2="{Y(w):.1f}"/><text x="{l - 6}" y="{Y(w) + 4:.1f}" text-anchor="end">{w // 1000} tys.</text>')
    for yr in range(1800, 2030, 25):
        parts.append(f'<text x="{X(yr):.1f}" y="{H - b + 16}" text-anchor="middle">{yr}</text>')
    labelled = {"PL", "US", "IN", "LY", "BR", "DE", "MC"}
    for c, yr, w in sorted(pts, key=lambda p: p[0] == "PL"):
        cls = "dot pl" if c == "PL" else "dot"
        rad = 6 if c == "PL" else 4
        parts.append(f'<circle class="{cls}" cx="{X(yr):.1f}" cy="{Y(w):.1f}" r="{rad}" data-tip="{tip(f"{name_pl(c, c)}: {yr}, {fmt(w)} słów")}"/>')
        if c in labelled:
            parts.append(f'<text x="{X(yr) + 8:.1f}" y="{Y(w) + 4:.1f}" class="lbl"{" style=\"fill:#b4532a\"" if c == "PL" else ""}>{escape(name_pl(c, c))}</text>')
    parts.append(f'<text x="{(W + l) / 2}" y="{H - 2}" text-anchor="middle">rok uchwalenia obowiązującej konstytucji</text>')
    return f'<svg viewBox="0 0 {W} {H}" role="img" aria-label="Długość konstytucji a rok uchwalenia">{"".join(parts)}</svg>'


def popularity_bins(ccp, pl_topics):
    W, H, l, b, top = 720, 270, 40, 34, 16
    bins = [[0, 0] for _ in range(10)]
    members = [[[], []] for _ in range(10)]
    for k in ccp.topic_keys:
        s = float(ccp.prevalence[k]["share"])
        i = min(9, int(s * 10))
        j = 0 if k in pl_topics else 1
        bins[i][j] += 1
        members[i][j].append(ccp.labels[k])
    mx = max(a + c for a, c in bins)
    bw = (W - l - 10) / 10
    parts = [f'<line class="axis" x1="{l}" x2="{W - 10}" y1="{H - b}" y2="{H - b}"/>']
    for k in range(0, mx + 1, 20):
        y = H - b - k / mx * (H - b - top)
        parts.append(f'<line class="grid" x1="{l}" x2="{W - 10}" y1="{y:.1f}" y2="{y:.1f}"/><text x="{l - 6}" y="{y + 4:.1f}" text-anchor="end">{k}</text>')
    for i, (has, no) in enumerate(bins):
        x = l + i * bw + 3
        h1 = has / mx * (H - b - top)
        h2 = no / mx * (H - b - top)
        rng = f"{i * 10}–{i * 10 + 10}%"
        parts.append(f'<rect class="m" x="{x:.1f}" y="{H - b - h1:.1f}" width="{bw - 6:.1f}" height="{max(0, h1):.1f}" rx="2" data-tip="{tip(f"{rng} konstytucji: {has} rozwiązań, które ma Konstytucja RP")}"/>')
        parts.append(f'<rect class="m2" x="{x:.1f}" y="{H - b - h1 - h2 - (2 if has and no else 0):.1f}" width="{bw - 6:.1f}" height="{max(0, h2):.1f}" rx="2" data-tip="{tip(f"{rng} konstytucji: {no} rozwiązań bez tagu w Konstytucji RP: " + ", ".join(members[i][1][:14]) + ("…" if len(members[i][1]) > 14 else ""))}"/>')
        parts.append(f'<text x="{x + (bw - 6) / 2:.1f}" y="{H - b - h1 - h2 - 6:.1f}" text-anchor="middle" class="lbl">{has}/{has + no}</text>')
        parts.append(f'<text x="{x + (bw - 6) / 2:.1f}" y="{H - b + 16}" text-anchor="middle">{i * 10}–{i * 10 + 10}%</text>')
    parts.append(f'<text x="{W / 2}" y="{H - 2}" text-anchor="middle">odsetek konstytucji świata, które mają rozwiązanie</text>')
    legend = '<p class="legend"><span><i class="k1"></i>Konstytucja RP ma (oznaczenie CCP)</span><span><i class="k2"></i>Konstytucja RP nie ma oznaczenia</span><span>etykieta: ma / wszystkie w przedziale</span></p>'
    return f'<svg viewBox="0 0 {W} {H}" role="img" aria-label="Rozkład popularności rozwiązań">{"".join(parts)}</svg>{legend}'


def hbars(rows, maxv, signed=False, unit="%"):
    """rows: (label, value, pl_has, tip, href). Horizontal bars; signed -> diverging around a centre line,
    with the label on the opposite side of the bar so labels never overlap bars."""
    rowh = 24
    if signed:
        W, zero, span = 860, 430, 330
    else:
        W, zero, span = 720, 300, 360
    H = rowh * len(rows) + 8
    parts = [f'<line class="axis" x1="{zero}" x2="{zero}" y1="0" y2="{H}"/>'] if signed else []
    for i, (lab, v, pl, t, href) in enumerate(rows):
        y = i * rowh + 4
        wv = abs(v) / maxv * span
        x = zero if v >= 0 else zero - wv
        cls = "m" if v >= 0 else "neg"
        short = escape(lab[:46] + ("…" if len(lab) > 46 else ""))
        if signed:
            lx, anchor = (zero - 8, "end") if v >= 0 else (zero + 8, "start")
        else:
            lx, anchor = zero - 10, "end"
        parts.append(f'<a href="{href}"><text x="{lx}" y="{y + 14}" text-anchor="{anchor}" class="lbl">{short}</text></a>')
        parts.append(f'<rect class="{cls}" x="{x:.1f}" y="{y + 3}" width="{max(wv, 1):.1f}" height="{rowh - 9}" rx="3" data-tip="{tip(t)}"/>')
        val = f"{'+' if signed and v > 0 else ''}{v:.0f}{unit}{' · RP' if pl else ''}"
        tx, ta = (x + wv + 6, "start") if v >= 0 else (x - 6, "end")
        parts.append(f'<text x="{tx:.1f}" y="{y + 14}" text-anchor="{ta}">{val}</text>')
    return f'<svg viewBox="0 0 {W} {H}" role="img">{"".join(parts)}</svg>'


def main() -> int:
    ccp = ccp_data.load()
    L = lengths(ccp)
    pl_topics = {k for k in ccp.topic_keys if ccp.prevalence[k]["poland"] == "1"}
    words = sorted(v["words"] for v in L.values())
    med = statistics.median(words)
    rank = sorted(L, key=lambda c: -L[c]["words"]).index("PL") + 1
    eu = sorted((c for c in L if c in EU27), key=lambda c: -L[c]["words"])
    eu_rank = eu.index("PL") + 1
    years = [year(ccp.by_code[c]) for c in L if year(ccp.by_code[c])]
    hero = (f'<div class="stat-hero"><div><b>{len(L)}</b><span>obowiązujących konstytucji</span></div>'
            f'<div><b>{fmt(int(med))}</b><span>słów ma typowa konstytucja (mediana)</span></div>'
            f'<div><b>{fmt(L["PL"]["words"])}</b><span>słów ma Konstytucja RP: {rank}. miejsce od najdłuższej na świecie, {eu_rank}. z {len(eu)} w UE</span></div>'
            f'<div><b>{int(statistics.median(years))}</b><span>mediana roku uchwalenia; połowa konstytucji świata jest młodsza</span></div></div>')

    longest = sorted(L, key=lambda c: -L[c]["words"])[:10]
    shortest = sorted(L, key=lambda c: L[c]["words"])[:10]
    tbl = lambda cs: "<table><tbody>" + "".join(f'<tr><td><a href="../panstwa/{c.lower()}.html">{escape(name_pl(c, c))}</a></td><td class="n">{fmt(L[c]["words"])}</td><td class="n">{year(ccp.by_code[c]) or ""}</td></tr>' for c in cs) + "</tbody></table>"
    eu_tbl = "<table><thead><tr><th>Państwo UE</th><th>słowa</th><th>rok</th></tr></thead><tbody>" + "".join(
        f'<tr{" style=\"font-weight:700\"" if c == "PL" else ""}><td>{escape(name_pl(c, c))}</td><td class="n">{fmt(L[c]["words"])}</td><td class="n">{year(ccp.by_code[c]) or ""}</td></tr>' for c in eu) + "</tbody></table>"

    # popularity: top solutions; trend since 2000; EU vs world
    top = sorted(ccp.topic_keys, key=lambda k: -float(ccp.prevalence[k]["share"]))[:25]
    top_rows = [(ccp.labels[k], float(ccp.prevalence[k]["share"]) * 100, k in pl_topics,
                 f'{ccp.labels[k]}: {ccp.prevalence[k]["count"]} z 188; od 2000 r. {ccp.prevalence[k]["count_2000plus"]} z 49; UE {ccp.prevalence[k]["count_eu27"]}/27', f"../tematy/{k}.html") for k in top]

    per_country = {c: {ccp.topic_keys[i] for i in d} for c, d in ccp.sections.items()}
    old = [c for c in L if (year(ccp.by_code[c]) or 0) < 2000]
    new = [c for c in L if (year(ccp.by_code[c]) or 0) >= 2000]

    def share(cs, k):
        return sum(1 for c in cs if k in per_country.get(c, set())) / max(1, len(cs)) * 100
    delta = [(k, share(new, k) - share(old, k)) for k in ccp.topic_keys if int(ccp.prevalence[k]["count"]) >= 10]
    up = sorted(delta, key=lambda x: -x[1])[:14]
    down = sorted(delta, key=lambda x: x[1])[:8]
    trend_rows = [(ccp.labels[k], d, k in pl_topics, f"{ccp.labels[k]}: {share(old, k):.0f}% konstytucji sprzed 2000 r., {share(new, k):.0f}% uchwalonych od 2000 r.", f"../tematy/{k}.html")
                  for k, d in up + sorted(down, key=lambda x: -x[1])]
    eu_delta = [(k, float(ccp.prevalence[k]["share_eu27"]) * 100 - float(ccp.prevalence[k]["share"]) * 100) for k in ccp.topic_keys]
    eu_up = sorted(eu_delta, key=lambda x: -x[1])[:12]
    eu_down = sorted(eu_delta, key=lambda x: x[1])[:8]
    eu_rows = [(ccp.labels[k], d, k in pl_topics, f'{ccp.labels[k]}: UE {ccp.prevalence[k]["count_eu27"]}/27, świat {ccp.prevalence[k]["count"]}/188', f"../tematy/{k}.html")
               for k, d in eu_up + sorted(eu_down, key=lambda x: -x[1])]
    mx_trend = max(abs(d) for _, d, *_ in trend_rows)
    mx_eu = max(abs(d) for _, d, *_ in eu_rows)

    pl_std = sum(1 for k in ccp.topic_keys if float(ccp.prevalence[k]["share"]) >= .75 and k in pl_topics)
    n_std = sum(1 for k in ccp.topic_keys if float(ccp.prevalence[k]["share"]) >= .75)
    body = f'''<p class="crumbs">Statystyki</p><h1>Ile słów i które rozwiązania</h1>
<p class="sub">Długość obowiązujących konstytucji i popularność 331 rozwiązań: na świecie, w konstytucjach uchwalonych od 2000 r. i w Unii Europejskiej. Konstytucja RP jest zaznaczona. Najedź na słupek lub punkt, aby zobaczyć szczegóły; nazwy rozwiązań prowadzą do tematów.</p>
{hero}
<h2>Długość</h2>
{chart("Jak długie są konstytucje", f"Liczba słów angielskiego wydania w Constitute, które pozwala porównywać państwa niezależnie od języka. Konstytucja RP ({fmt(L['PL']['words'])} słów) jest nieco dłuższa od typowej ({fmt(int(med))}). Najdłuższe zestawienia, np. Wielkiej Brytanii, to zbiory ustaw ustrojowych, a nie jedna konstytucja.", histogram_lengths(L, ccp))}
{chart("Długość a rok uchwalenia", "Każdy punkt to obowiązująca konstytucja; skala pionowa jest logarytmiczna. Nowsze konstytucje są zwykle dłuższe: regulują więcej praw i instytucji.", scatter_year(L, ccp) + '<p class="note">Poza wykresem: Wielka Brytania (zbiór ustaw ustrojowych, najstarsze z 1215 r.).</p>')}
<div class="two">{chart("Najdłuższe", "słowa · rok uchwalenia", tbl(longest))}{chart("Najkrótsze", "słowa · rok uchwalenia", tbl(shortest))}</div>
<details class="chart"><summary>Państwa UE od najdłuższej konstytucji</summary>{eu_tbl}</details>
<h2>Popularność rozwiązań</h2>
{chart("Jak częste są rozwiązania", f"331 rozwiązań według odsetka konstytucji świata, które je mają. Konstytucja RP ma {pl_std} z {n_std} rozwiązań obecnych w co najmniej 75% konstytucji. Brak oznaczenia CCP nie zawsze oznacza brak przepisu (luki sprawdzono ręcznie na stronach tematów).", popularity_bins(ccp, pl_topics))}
{chart("25 najpopularniejszych rozwiązań", "Odsetek 188 obowiązujących konstytucji; „RP” oznacza, że ma je Konstytucja RP.", hbars(top_rows, 100))}
{chart("Co zyskuje, a co traci popularność", f"Różnica w punktach procentowych między konstytucjami uchwalonymi od 2000 r. ({len(new)}) a starszymi ({len(old)}). Tylko rozwiązania obecne w co najmniej 10 konstytucjach. Na górze najbardziej zyskujące, na dole tracące.", hbars(trend_rows, mx_trend, signed=True, unit=" pp"), '<p class="legend"><span><i class="k1"></i>częstsze w nowych konstytucjach</span><span><i class="k4"></i>rzadsze w nowych konstytucjach</span></p>')}
{chart("Czym Unia różni się od świata", "Różnica w punktach procentowych między odsetkiem w 27 konstytucjach UE a odsetkiem na świecie. Na górze rozwiązania częstsze w UE, na dole rzadsze.", hbars(eu_rows, mx_eu, signed=True, unit=" pp"), '<p class="legend"><span><i class="k1"></i>częstsze w UE</span><span><i class="k4"></i>rzadsze w UE</span></p>')}
<p class="note">Źródła: oznaczenia tematów Comparative Constitutions Project (przez Constitute), wydania angielskie Constitute; obliczenia własne. Częstość nie mówi, czy rozwiązanie działa. Dane: <code>dane/rozwiazania_swiat.csv</code>, <code>dane/dlugosci_konstytucji.csv</code> w repozytorium.</p>
<script>{TIP_JS}</script>'''
    html = page("Statystyki: długość konstytucji i popularność rozwiązań", body, description="Jak długie są konstytucje świata i które rozwiązania są najpopularniejsze; Konstytucja RP na tym tle.",
                css="../panstwa/style.css", current="statystyki").replace("</head>", f"<style>{CSS}</style></head>")
    (HERE / "index.html").write_text(html, encoding="utf-8")
    print(json.dumps({"countries": len(L), "median_words": med, "pl_words": L["PL"]["words"], "pl_rank": rank, "eu_rank": eu_rank, "old": len(old), "new": len(new)}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
