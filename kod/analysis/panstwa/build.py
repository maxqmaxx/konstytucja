#!/usr/bin/env python3
"""Build static country pages, the country index and the comparison view.

Inputs: catalog.jsonl, CCP data (../features), atlas entries (../zapisy.json),
Polish proposals (../polska/propozycje.json). No network. Offline-readable output.
Run from the project root: python3 analysis/panstwa/build.py
"""
from __future__ import annotations

import json
import sys
from collections import Counter, defaultdict
from html import escape
from pathlib import Path

from babel import Locale

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(HERE.parent / "features"))
import ccp_data  # noqa: E402

PL = Locale("pl")
HISTORICAL = {"BAD": "Badenia", "BAY": "Bawaria", "UAR": "Zjednoczona Republika Arabska", "MAN": "Mandżukuo",
              "CRE": "Państwo Kreteńskie", "DAN": "Wolne Miasto Gdańsk", "DD": "Niemiecka Republika Demokratyczna",
              "PRU": "Prusy", "TAN": "Strefa Międzynarodowa Tangeru", "MEM": "Kraj Kłajpedy", "XS": "Somaliland",
              "SU": "Związek Radziecki", "CS": "Czechosłowacja", "TRI": "Wolne Terytorium Triestu",
              "GCO": "Wielka Kolumbia", "YU": "Jugosławia"}
FORMER = set(HISTORICAL) - {"XS"}
PROVIDERS = {"constitute": "Constitute", "wipo": "WIPO Lex", "mjp": "Digithèque MJP", "sejm-library": "Biblioteka Sejmowa",
             "uk-legislation": "legislation.gov.uk", "eli-sejm": "ELI, Dziennik Ustaw", "canada-justice": "Justice Laws (Kanada)",
             "nz-legislation": "NZ Legislation"}
STATUS = {"source_in_force": "obowiązująca według źródła", "source_edition_unverified": "aktualność niepotwierdzona",
          "historical_or_replaced": "historyczna lub zastąpiona", "draft": "projekt",
          "official_edition_unverified": "wydanie urzędowe, aktualność niepotwierdzona",
          "official_publication_unverified": "publikacja urzędowa, aktualność niepotwierdzona"}
LANG_EXTRA = {"mul": "wielojęzyczny", "cjk": "chiński/japoński/koreański", "cnr": "czarnogórski", "rom": "romski",
              "jiv": "shuar", "kj": "kuanyama", "kmb": "kimbundu", "brx": "bodo", "doi": "dogri", "mni": "manipuri"}
NAV_ITEMS = [("mapa/index.html", "Mapa", "mapa"), ("rp/index.html", "Konstytucja RP", "rp"), ("problemy/index.html", "Problemy", "problemy"), ("tematy/index.html", "Tematy", "tematy"),
             ("konstruktor/index.html", "Konstruktor", "konstruktor"), ("statystyki/index.html", "Statystyki", "statystyki"),
             ("panstwa/index.html", "Państwa", "panstwa"), ("ATLAS.html", "Atlas", "atlas"), ("polska/index.html", "Dla Polski", "polska"),
             ("wizualizacje/index.html", "Pracownia", "wizualizacje")]



from report import REPO, issue_link  # noqa: E402,F401

def nav(up="../", current="panstwa"):
    links = "".join(f'<a href="{up}{href}"{" aria-current=\"page\"" if key == current else ""}>{label}</a>' for href, label, key in NAV_ITEMS)
    return f'<nav class="site-nav" aria-label="Serwis"><a class="brand" href="{up}ATLAS.html">Konstytucje świata</a>{links}</nav>'


SEARCH_PAGE = """<p class="crumbs"><a href="index.html">Państwa</a> / Szukaj</p><h1>Szukaj w tekstach</h1>
<p class="sub">Pełny tekst 2141 dokumentów we wszystkich językach archiwum. Polskie znaki są opcjonalne. Wszystkie słowa muszą wystąpić w akapicie; frazę ujmij w cudzysłów, a gwiazdka na końcu szuka początku słowa, np. <code>konstytuc*</code>. Brak odmiany wyrazów: szukaj także innych form.</p>
<form class="controls search-form" id="f" role="search"><label class="wide">Zapytanie<input id="q" name="q" type="search" required placeholder='np. "stan wyjątkowy", referendum, sumienia' autocomplete="off"></label>
<label>Język<select name="lang"><option value="">wszystkie</option>@@LANGS@@</select></label>
<label>Państwo<select name="kraj"><option value="">wszystkie</option>@@COUNTRIES@@</select></label>
<label>Status<select name="status"><option value="">wszystkie</option>@@STATUS@@</select></label>
<button class="button" type="submit">Szukaj</button></form>
<p class="summary" id="summary" aria-live="polite"></p><ol class="results" id="results"></ol>
<p class="note">Wyniki to akapity roboczych odczytów tekstu z numerem wiersza. Rozstrzyga oryginał. Skany bez warstwy tekstowej nie są przeszukiwane.</p>
<script>(()=>{const P=@@PROVIDERS@@,S=@@STATUSMAP@@,L=@@LANGMAP@@;const f=document.getElementById('f'),out=document.getElementById('results'),sum=document.getElementById('summary');
const esc=v=>String(v??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const mark=(s,m)=>esc(s).split(m[0]).join('<mark>').split(m[1]).join('</mark>');
function fill(){try{const p=new URLSearchParams(location.hash.slice(1));for(const [k,v] of p){const el=f.elements[k];if(el)el.value=v;}return p.get('q');}catch{return null;}}
async function run(){const fd=new FormData(f);const p=new URLSearchParams();for(const [k,v] of fd){if(v)p.set(k,v);}
if(!p.get('q'))return;try{history.replaceState(null,'','#'+p);}catch{}
if(location.protocol==='file:'){sum.textContent='Wyszukiwanie działa tylko przez serwer (http://localhost:8112/).';return;}
sum.textContent='Szukam…';out.replaceChildren();
try{const r=await fetch('../../api/szukaj?'+p);const d=await r.json();if(!r.ok){sum.textContent=d.error||'Błąd wyszukiwania.';return;}
sum.innerHTML=`Pasujące akapity: <b>${d.matching_passages}</b> w <b>${d.matching_documents}</b> dokumentach.${d.matching_documents>d.shown_documents?` Pokazano ${d.shown_documents} najlepiej dopasowanych.`:''}`;
out.innerHTML=d.results.map(x=>`<li data-teczka="${esc(JSON.stringify({id:'wynik-'+x.id+'-'+x.hits[0].line,type:'wynik',title:x.country+': '+x.title+' (w. '+x.hits[0].line+')',cite:x.title+' ('+x.country+'), '+(P[x.provider]||x.provider)+', tekst roboczy, wiersz '+x.hits[0].line,url:''}))}"><p class="doc"><a href="${esc(x.country_code.toLowerCase())}.html">${esc(x.country)}</a> · ${esc(x.title)}</p><p class="meta">${esc(L[x.language]||x.language)} · ${esc(P[x.provider]||x.provider)} · ${esc(S[x.status]||x.status)} · <a href="../../${esc(x.text_path)}">TXT</a>${x.original?` · <a href="../../${esc(x.original)}">oryginał</a>`:''}</p><div data-teczka-text>${x.hits.map(h=>`<p class="snip"><span class="ln">w. ${h.line}</span> ${mark(h.snippet,d.marks)}</p>`).join('')}</div></li>`).join('');if(window.Teczka)Teczka.attach(out);if(!d.results.length)out.innerHTML='<li class="empty">Brak wyników. Spróbuj innej formy słowa (bez odmiany), gwiazdki na końcu, np. <code>wod*</code>, albo odpowiednika w innym języku, np. <code>"right to water"</code>. Polskie przekłady obejmują część konstytucji.</li>';}
catch(e){sum.textContent='Serwer wyszukiwania jest niedostępny.';}}
f.addEventListener('submit',e=>{e.preventDefault();run();});if(fill())run();})();</script>"""


def name_pl(code, fallback):
    return HISTORICAL.get(code) or PL.territories.get(code) or fallback


def lang_pl(code):
    return LANG_EXTRA.get(code) or PL.languages.get(code) or code


def year(value):
    try:
        return int(str(value)[:4])
    except (TypeError, ValueError):
        return None


def page(title, body, up="../", description="", css="style.css", current="panstwa"):
    return f'''<!doctype html>
<html lang="pl"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<meta name="description" content="{escape(description)}"><title>{escape(title)}</title><link rel="stylesheet" href="{css}"></head>
<body><a class="skip" href="#tresc">Przejdź do treści</a>
<header>{nav(up, current)}</header>
<main class="wrap" id="tresc">{body}</main>
<footer class="wrap"><span>Konstytucje świata · katalog państw</span><span>Status opisuje wydanie źródłowe, nie ocenę prawną obecnego obowiązywania.</span></footer>
</body></html>'''


def edition_key(rec):
    for item in [rec.get("text") or {}] + list(rec.get("assets") or []):
        path = item.get("path") if isinstance(item, dict) else None
        if path:
            return path.split("/")[2]
    return f'{rec["provider"]}-{rec["provider_id"]}'


def file_links(rec):
    links = []
    for asset in rec.get("assets") or []:
        ext = asset["path"].rsplit(".", 1)[-1].upper()
        links.append(f'<a href="../../{escape(asset["path"])}">{ext}</a>')
    if rec.get("text"):
        links.append(f'<a href="../../{escape(rec["text"]["path"])}">TXT</a>')
    return " ".join(links)


def main() -> int:
    records = [json.loads(line) for line in open(ROOT / "catalog.jsonl", encoding="utf-8")]
    ccp = ccp_data.load()
    atlas = defaultdict(list)
    for z in json.loads((HERE.parent / "zapisy.json").read_text()):
        atlas[z["country_code"]].append(z)
    proposals = json.loads((HERE.parent / "polska" / "propozycje.json").read_text())["proposals"]
    inspired = defaultdict(list)
    atlas_country = {z["id"]: z["country_code"] for zs in atlas.values() for z in zs}
    for p in proposals:
        for a in p["inspirations"]:
            if atlas_country.get(a) and p not in inspired[atlas_country[a]]:
                inspired[atlas_country[a]].append(p)

    by_country = defaultdict(list)
    for rec in records:
        by_country[rec["country_code"]].append(rec)

    index_rows = []
    for code, recs in by_country.items():
        name = name_pl(code, recs[0]["country"])
        got = [r for r in recs if r["download_status"] != "failed"]
        langs = Counter(r["language"] for r in got)
        years = [y for y in (year(r["year_enacted"]) for r in recs) if y]
        editions = defaultdict(list)
        for r in recs:
            editions[edition_key(r)].append(r)

        blocks = []
        for key, items in sorted(editions.items(), key=lambda kv: (-(max([year(r["year_enacted"]) or 0 for r in kv[1]])), kv[0])):
            title = next((r["title"] for r in items if r["language"] == "pl"), None) or next((r["title"] for r in items if r["language"] == "en"), items[0]["title"])
            y = max([year(r["year_enacted"]) or 0 for r in items]) or None
            rows = []
            for r in sorted(items, key=lambda r: (r["language"] != "pl", lang_pl(r["language"]), r["provider"])):
                flags = []
                if r["download_status"] == "failed":
                    flags.append('<span class="flag bad">nie pobrano</span>')
                elif r["download_status"] == "partial":
                    flags.append('<span class="flag">część formatów</span>')
                if r.get("needs_ocr_or_review"):
                    flags.append('<span class="flag">skan bez tekstu</span>')
                rows.append(f'<tr><td>{escape(lang_pl(r["language"]))}</td><td>{escape(PROVIDERS.get(r["provider"], r["provider"]))}</td>'
                            f'<td>{escape(STATUS.get(r["status"], r["status"]))}</td><td class="files">{file_links(r)} {"".join(flags)}'
                            f' <a class="src" href="{escape(r["source_url"])}">źródło ↗</a></td></tr>')
            blocks.append(f'<section class="edition"><h3>{escape(title)}{f" <span>{y}</span>" if y else ""}</h3><div class="table-scroll"><table>'
                          f'<thead><tr><th scope="col">Język</th><th scope="col">Źródło</th><th scope="col">Status</th><th scope="col">Pliki</th></tr></thead>'
                          f'<tbody>{"".join(rows)}</tbody></table></div></section>')

        current = ""
        if code in ccp.by_code:
            d = ccp.by_code[code]
            n = len(ccp.sections.get(code, {}))
            current = (f'<section class="current"><p class="eyebrow">Obowiązująca konstytucja według Constitute</p><h2>{escape(d["title"])}</h2>'
                       f'<p>Uchwalona {escape(str(d["year_enacted"] or "—"))}, wydanie z {escape(str(d["year_revised"] or "—"))}. '
                       f'Koderzy CCP oznaczyli w niej <b>{n}</b> z 331 tematów.</p><p class="actions">'
                       f'<a class="button" href="porownaj.html#c={code}{",PL" if code != "PL" else ",DE"}">Porównaj z {"Polską" if code != "PL" else "Niemcami"}</a>'
                       f'<a class="button ghost" href="../mapa/index.html#t=amend&c={code}">Pokaż na mapie</a></p></section>')
        atlas_html = ""
        if atlas.get(code):
            atlas_html = ('<section><h2>W atlasie zapisów</h2><ul class="atlas">' + "".join(
                f'<li><a href="../ATLAS.html#{escape(z["id"].lower())}">{escape(z["title"])}</a> <span>{escape(z["provision"])} · {escape(z["document_title"])}</span></li>'
                for z in atlas[code]) + "</ul></section>")
        insp_html = ""
        if inspired.get(code):
            insp_html = ('<section><h2>Inspiracja dla propozycji dla Polski</h2><ul class="atlas">' + "".join(
                f'<li><a href="../polska/index.html#{p["id"].lower()}">{escape(p["id"])}: {escape(p["title"])}</a></li>' for p in inspired[code]) + "</ul></section>")
        facts = (f'<dl class="facts"><div><dt>Pozycje w archiwum</dt><dd>{len(recs)}</dd></div><div><dt>Wydania</dt><dd>{len(editions)}</dd></div>'
                 f'<div><dt>Języki</dt><dd>{len(langs)}</dd></div><div><dt>Po polsku</dt><dd>{langs.get("pl", 0)}</dd></div>'
                 f'<div><dt>Lata</dt><dd>{f"{min(years)}–{max(years)}" if years else "—"}</dd></div></dl>')
        body = (f'<p class="crumbs"><a href="index.html">Państwa</a> / {escape(name)}</p><h1>{escape(name)}</h1>'
                f'<p class="sub">{"Dawne państwo · " if code in FORMER else ""}{escape(recs[0]["country"])} · {escape(code)}</p>{facts}{current}{insp_html}{atlas_html}'
                f'<section><h2>Wszystkie wydania i wersje językowe</h2><p class="note">Jedna pozycja to dokument w danym języku z danego źródła. '
                f'Liczba pozycji nie jest liczbą różnych konstytucji. Pliki TXT to robocze odczyty; rozstrzyga oryginał.</p>{"".join(blocks)}</section>')
        (HERE / f"{code.lower()}.html").write_text(page(f"{name}: konstytucje", body, description=f"Konstytucje i akty ustrojowe: {name}."))
        index_rows.append({"code": code, "name": name, "former": code in FORMER, "n": len(recs), "langs": len(langs),
                           "pl": langs.get("pl", 0), "current": code in ccp.by_code, "atlas": len(atlas.get(code, [])),
                           "years": f"{min(years)}–{max(years)}" if years else ""})

    index_rows.sort(key=lambda r: r["name"].lower())
    def row(r):
        badges = ("".join([f'<span class="flag ok">obowiązująca w CCP</span>' if r["current"] else "",
                           f'<span class="flag">{r["pl"]} po polsku</span>' if r["pl"] else "",
                           f'<span class="flag">{r["atlas"]} w atlasie</span>' if r["atlas"] else ""]))
        return (f'<li data-name="{escape(r["name"].lower())} {r["code"].lower()}"><a href="{r["code"].lower()}.html">{escape(r["name"])}</a>'
                f'<span class="meta">{r["n"]} poz. · {r["langs"]} jęz.{" · " + r["years"] if r["years"] else ""}</span>{badges}</li>')
    current_list = "".join(row(r) for r in index_rows if not r["former"])
    former_list = "".join(row(r) for r in index_rows if r["former"])
    body = (f'<h1>Państwa i terytoria</h1><p class="sub">{len(index_rows)} jurysdykcji, {len(records)} pozycji w archiwum. '
            f'<a href="porownaj.html">Porównaj 2–3 konstytucje</a> · <a href="szukaj.html">Szukaj w tekstach</a></p>'
            f'<label class="search">Szukaj państwa<input id="q" type="search" placeholder="np. Polska, Niemcy, PL" autocomplete="off"></label>'
            f'<h2>Państwa i terytoria</h2><ul class="countries" id="list-current">{current_list}</ul>'
            f'<h2>Dawne państwa</h2><ul class="countries" id="list-former">{former_list}</ul>'
            '<script>(()=>{const q=document.getElementById("q");q.addEventListener("input",()=>{const v=q.value.trim().toLowerCase();'
            'document.querySelectorAll(".countries li").forEach(li=>{li.hidden=!!v&&!li.dataset.name.includes(v);});});})();</script>')
    (HERE / "index.html").write_text(page("Państwa: konstytucje świata", body, description="Katalog konstytucji według państw."))

    lang_counts = Counter(r["language"] for r in records if r.get("text"))
    lang_opts = "".join(f'<option value="{l}">{escape(lang_pl(l))} ({n})</option>'
                        for l, n in sorted(lang_counts.items(), key=lambda kv: (-kv[1], kv[0])) if n >= 3)
    country_opts = "".join(f'<option value="{r["code"]}">{escape(r["name"])}</option>' for r in index_rows)
    status_opts = "".join(f'<option value="{k}">{escape(v)}</option>' for k, v in STATUS.items())
    search_body = (SEARCH_PAGE.replace("@@LANGS@@", lang_opts).replace("@@COUNTRIES@@", country_opts)
                   .replace("@@STATUS@@", status_opts).replace("@@PROVIDERS@@", json.dumps(PROVIDERS, ensure_ascii=False))
                   .replace("@@STATUSMAP@@", json.dumps(STATUS, ensure_ascii=False))
                   .replace("@@LANGMAP@@", json.dumps({l: lang_pl(l) for l in lang_counts}, ensure_ascii=False)))
    (HERE / "szukaj.html").write_text(page("Szukaj w tekstach konstytucji", search_body, description="Wyszukiwanie pełnotekstowe w 2141 tekstach konstytucji.").replace("</body>", '<script src="../teczka/teczka.js"></script></body>'))

    compare_data = {"topics": ccp.topic_rows(), "countries": {
        c: {"name": name_pl(c, d["country"]), "title": d["title"], "year": d["year_enacted"],
            "url": f'https://www.constituteproject.org/constitution/{d["id"].split(":")[-1]}', "topics": ccp.sections.get(c, {})}
        for c, d in ccp.by_code.items()}}
    template = (HERE / "porownaj.template.html").read_text()
    payload = json.dumps(compare_data, ensure_ascii=False, separators=(",", ":")).replace("<", "\\u003c")
    (HERE / "porownaj.html").write_text(template.replace("@@NAV@@", nav("../", "panstwa")).replace("@@DATA@@", payload))
    print(json.dumps({"country_pages": len(index_rows), "records": len(records), "compare_countries": len(compare_data["countries"])}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
