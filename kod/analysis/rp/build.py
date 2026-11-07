#!/usr/bin/env python3
"""Build "Konstytucja RP na tle świata" (rp/) and provision variants per CCP topic (tematy/).

Inputs: official Polish text (../polska/sources), CCP sections and prevalence (../features),
Polish proposals (../polska/propozycje.json), manual gap review. No network.
Run from the project root: python3 analysis/rp/build.py
"""
from __future__ import annotations

import csv
import json
import re
import sys
from collections import Counter, defaultdict
from html import escape
from pathlib import Path

HERE = Path(__file__).resolve().parent
ANALYSIS = HERE.parent
ROOT = ANALYSIS.parent
TOPICS_DIR = ANALYSIS / "tematy"
sys.path.insert(0, str(ANALYSIS / "features"))
sys.path.insert(0, str(ANALYSIS / "panstwa"))
import ccp_data  # noqa: E402
sys.path.insert(0, str(ANALYSIS / "tlumaczenia"))
import store  # noqa: E402
from build import page, name_pl, issue_link  # noqa: E402

EU27 = {"AT", "BE", "BG", "HR", "CY", "CZ", "DK", "EE", "FI", "FR", "DE", "GR", "HU", "IE", "IT",
        "LV", "LT", "LU", "MT", "NL", "PL", "PT", "RO", "SK", "SI", "ES", "SE"}
CHAPTERS = [("P", 0, 0, "Preambuła"), ("I", 1, 29, "Rzeczpospolita"), ("II", 30, 86, "Wolności, prawa i obowiązki człowieka i obywatela"),
            ("III", 87, 94, "Źródła prawa"), ("IV", 95, 125, "Sejm i Senat"), ("V", 126, 145, "Prezydent Rzeczypospolitej Polskiej"),
            ("VI", 146, 162, "Rada Ministrów i administracja rządowa"), ("VII", 163, 172, "Samorząd terytorialny"),
            ("VIII", 173, 201, "Sądy i Trybunały"), ("IX", 202, 215, "Organy kontroli państwowej i ochrony prawa"),
            ("X", 216, 227, "Finanse publiczne"), ("XI", 228, 234, "Stany nadzwyczajne"), ("XII", 235, 235, "Zmiana Konstytucji"),
            ("XIII", 236, 243, "Przepisy przejściowe i końcowe")]
CHAPTER_EN = {"VII": "LOCAL SELF-GOVERNMENT", "XI": "EXTRAORDINARY MEASURES", "XIII": "FINAL AND TRANSITIONAL"}
GAP_CHAPTER = {"unamend": "XII", "cappun": "II", "water": "II", "amparo": "II", "doubjep": "II", "miranda": "II",
               "slave": "II", "resrce": "I", "cc": "IX", "assets": "IV", "hosimm": "V"}
TECZKA = '<script src="../teczka/teczka.js"></script></body>'
VERDICT = {"luka": "brak w Konstytucji RP", "luka_celowa": "brak, rozwiązanie celowe", "inna_technika": "ujęte ogólną klauzulą",
           "czesciowo": "częściowo", "artefakt": "jest, choć CCP nie oznaczył", "nie_dotyczy": "nie dotyczy"}


def rarity(share: float):
    if share >= .75:
        return "standard", "standard światowy"
    if share >= .40:
        return "czeste", "częste"
    if share >= .15:
        return "rzadsze", "rzadsze"
    return "rzadkie", "rzadkie"


def clean_article(raw: str) -> str:
    text = re.sub(r"\s+", " ", raw).strip()
    text = re.sub(r" (\d{1,2})\. (?=\S)", r"\n\1. ", text)
    text = re.sub(r" (\d{1,2})\) (?=\S)", r"\n   \1) ", text)
    return text


def polish_text():
    html = (ANALYSIS / "polska/sources/konstytucja-rp.html").read_text()
    arts = {int(n): clean_article(re.sub(r"<[^>]+>", " ", body).replace("&quot;", '"').replace("&amp;", "&"))
            for n, body in re.findall(r'<section id="art-(\d+)"><h2>Art\. \d+</h2><pre>(.*?)</pre></section>', html, re.S)}
    txt = (ANALYSIS / "polska/sources/konstytucja-rp-ujednolicony.txt").read_text()
    start = txt.find("W trosce o byt")
    end = txt.find("Rozdział I", start)
    preamble = re.sub(r"\s+", " ", txt[start:end]).strip() if start >= 0 else ""
    return arts, preamble


def chapter_of(n: int) -> str:
    return next(c[0] for c in CHAPTERS if c[1] <= n <= c[2])


def article_ref(label: str):
    m = re.match(r"Article (\d+)$", label)
    if m:
        return int(m.group(1))
    if label == "Preamble":
        return 0
    m = re.match(r"Chapter ([IVX]+)\b", label)
    return f"ch-{m.group(1)}" if m else None


def bars(row):
    out = []
    for key, cnt, label, total in (("share", "count", "świat", 188), ("share_2000plus", "count_2000plus", "od 2000 r.", 49), ("share_eu27", "count_eu27", "UE-27", 27)):
        s = float(row[key])
        out.append(f'<div class="bar-row"><span>{label}</span><span class="bar"><i style="width:{s * 100:.1f}%"></i></span><b>{s:.0%}</b><small>{row[cnt]}/{total}</small></div>')
    return "".join(out)


def chip(key, ccp):
    row = ccp.prevalence[key]
    cls, word = rarity(float(row["share"]))
    return (f'<a class="chip {cls}" href="../tematy/{key}.html" title="{escape(ccp.topics[key])}">{escape(ccp.labels[key])}'
            f'<span>{word} · {float(row["share"]):.0%} świata · UE {row["count_eu27"]}/27</span></a>')


def main() -> int:
    ccp = ccp_data.load()
    arts, preamble = polish_text()
    if len(arts) != 243:
        raise SystemExit(f"expected 243 articles, got {len(arts)}")
    proposals = json.loads((ANALYSIS / "polska/propozycje.json").read_text())["proposals"]
    review = {r["topic"]: r for r in csv.DictReader(open(ANALYSIS / "features/poland_gap_review.csv", encoding="utf-8"))}
    evidence = json.loads((ANALYSIS / "features/proposals_evidence.json").read_text())["proposals"]
    topic_props = defaultdict(list)
    for pid, items in evidence.items():
        for it in items:
            topic_props[it["topic"]].append(pid)
    prop_by_id = {p["id"]: p for p in proposals}
    art_props = defaultdict(list)
    for p in proposals:
        for a in p["polish_articles"]:
            art_props[a].append(p)

    # All tagged sections (up to 3 per country and topic), in-force editions only.
    variants = defaultdict(lambda: defaultdict(list))
    pl_refs = defaultdict(list)  # topic -> [article number | 'ch-X']
    art_topics = defaultdict(list)  # article number | 'ch-X' -> [topic]
    poland_doc = ccp.by_code["PL"]["id"]
    with open(ANALYSIS / "features/ccp_sections.csv", encoding="utf-8") as fh:
        for row in csv.DictReader(fh):
            doc = ccp.docs.get(row["doc_id"])
            if not doc:
                continue
            bucket = variants[row["topic"]][doc["country_code"]]
            if len(bucket) < 3:
                bucket.append((row["article"], row["section_id"].split("/")[-1], row["text"], (row["doc_id"], row["section_id"])))
            if row["doc_id"] == poland_doc:
                ref = article_ref(row["article"])
                if ref is not None and ref not in pl_refs[row["topic"]]:
                    pl_refs[row["topic"]].append(ref)
                    art_topics[ref].append(row["topic"])

    # ---------- rp/index.html ----------
    toc, blocks = [], []
    total_tagged = 0
    for code, lo, hi, title in CHAPTERS:
        anchor = "preambula" if code == "P" else f"rozdzial-{code.lower()}"
        toc.append(f'<a href="#{anchor}">{"Preambuła" if code == "P" else f"Rozdz. {code}"}<span>{escape(title) if code != "P" else ""}</span></a>')
        gaps = [t for t, ch in GAP_CHAPTER.items() if ch == code and t in review]
        gap_html = ""
        if gaps:
            gap_html = '<div class="missing"><h3>Czego tu nie ma, a jest w innych konstytucjach</h3><ul>' + "".join(
                f'<li><a href="../tematy/{t}.html">{escape(ccp.labels[t])}</a>: {float(ccp.prevalence[t]["share"]):.0%} świata, UE {ccp.prevalence[t]["count_eu27"]}/27. '
                f'<span>{escape(VERDICT[review[t]["verdict"]])}. {escape(review[t]["note"])}</span></li>' for t in gaps) + "</ul></div>"
        chapter_chips = "".join(chip(t, ccp) for t in art_topics.get(f"ch-{code}", []))
        items = []
        numbers = [0] if code == "P" else range(lo, hi + 1)
        for n in numbers:
            body = preamble if n == 0 else arts[n]
            topics = art_topics.get(n, [])
            total_tagged += bool(topics)
            props = art_props.get(n, [])
            chips = "".join(chip(t, ccp) for t in sorted(topics, key=lambda t: float(ccp.prevalence[t]["share"])))
            rare = any(float(ccp.prevalence[t]["share"]) < .15 for t in topics)
            props_html = ("<p class=\"props\">Propozycje zmian: " + ", ".join(
                f'<a href="../polska/index.html#{p["id"].lower()}">{p["id"]} {escape(p["title"])}</a>' for p in props) + "</p>") if props else ""
            expert = ""
            if topics:
                expert = ('<details class="expert"><summary>Dla ekspertów: kody CCP</summary><ul>' + "".join(
                    f'<li><code>{t}</code> {escape(ccp.topics[t])}: {ccp.prevalence[t]["count"]}/188, od 2000 r. {ccp.prevalence[t]["count_2000plus"]}/49</li>' for t in topics)
                    + '</ul><p><a href="https://www.constituteproject.org/constitution/Poland_2009">Wydanie angielskie w Constitute</a></p></details>')
            label = "Preambuła" if n == 0 else f"Art. {n}"
            anchor_id = "preambula-tekst" if n == 0 else f"art-{n}"
            meta = {"id": f"rp-{anchor_id}", "type": "rp", "title": f"Konstytucja RP, {'preambuła' if n == 0 else f'art. {n}'}", "anchor": anchor_id,
                    "cite": f"Konstytucja Rzeczypospolitej Polskiej z dnia 2 kwietnia 1997 r., {'preambuła' if n == 0 else f'art. {n}'} (Dz.U. 1997 nr 78 poz. 483 ze zm.)",
                    "url": "https://eli.gov.pl/eli/DU/1997/483/ogl"}
            items.append(f'<article class="art" id="{anchor_id}" data-ch="{code}" data-rare="{int(rare)}" data-props="{int(bool(props))}" data-tagged="{int(bool(topics))}" data-teczka="{escape(json.dumps(meta, ensure_ascii=False))}">'
                         f'<h3><a href="#{anchor_id}">{label}</a>{issue_link(f"Konstytucja RP na tle świata, {label} (rp/index.html#{anchor_id})", "tematy: " + ", ".join(topics))}</h3><div class="text" data-teczka-text>{escape(body)}</div>'
                         f'{f"<div class=chips>{chips}</div>" if chips else ""}{props_html}{expert}</article>')
        heading = "Preambuła" if code == "P" else f"Rozdział {code}. {title}"
        blocks.append(f'<section class="chapter" id="{anchor}"><h2>{escape(heading)}</h2>{gap_html}'
                      f'{f"<div class=chips>{chapter_chips}</div>" if chapter_chips else ""}{"".join(items)}</section>')

    legend = ('<div class="rarity-legend"><span class="chip standard">standard światowy<span>co najmniej 75% konstytucji</span></span>'
              '<span class="chip czeste">częste<span>40–75%</span></span><span class="chip rzadsze">rzadsze<span>15–40%</span></span>'
              '<span class="chip rzadkie">rzadkie<span>poniżej 15%</span></span></div>')
    body = f'''<p class="crumbs">Konstytucja RP na tle świata</p><h1>Konstytucja RP na tle świata</h1>
<p class="sub">Urzędowy tekst Konstytucji z 2 kwietnia 1997 r. Pod artykułami: jakie rozwiązania w nim widzą koderzy Comparative Constitutions Project i jak często występują w 188 obowiązujących konstytucjach. Kliknij rozwiązanie, aby zobaczyć, jak zapisały je inne państwa.</p>
{legend}
<section class="controls rp-controls" aria-label="Filtry"><label class="wide">Szukaj w tekście<input id="q" type="search" placeholder="np. kadencja, referendum, sumienie" autocomplete="off"></label>
<label>Pokaż<select id="show"><option value="">wszystkie artykuły</option><option value="tagged">z rozwiązaniami CCP</option><option value="rare">z rzadkimi rozwiązaniami</option><option value="props">z propozycjami zmian</option></select></label></section>
<p class="summary" id="summary" aria-live="polite"></p>
<div class="rp-layout"><nav class="toc" aria-label="Rozdziały">{"".join(toc)}</nav><div>{"".join(blocks)}</div></div>
<p class="note">Tekst: urzędowy tekst ujednolicony (ELI, Dz.U. 1997 nr 78 poz. 483 ze zm.), odczyt roboczy z PDF; przy rozbieżności rozstrzyga PDF. Kodowanie CCP dotyczy angielskiego wydania Constitute (rev. 2009). Częstość nie mówi, czy rozwiązanie działa. Brak oznaczenia nie dowodzi braku regulacji: zob. <a href="../features/README.md">metodę</a>.</p>
<script>(()=>{{const q=document.getElementById('q'),s=document.getElementById('show'),out=document.getElementById('summary');
const arts=[...document.querySelectorAll('.art')];const norm=v=>v.toLowerCase().normalize('NFD').replace(/[\\u0300-\\u036f]/g,'').replace(/ł/g,'l');
const texts=arts.map(a=>norm(a.textContent));
function run(){{const v=norm(q.value.trim()),m=s.value;let n=0;arts.forEach((a,i)=>{{const ok=(!v||texts[i].includes(v))&&(!m||a.dataset[m]==='1');a.hidden=!ok;n+=ok;}});
document.querySelectorAll('.chapter').forEach(c=>{{c.hidden=!c.querySelector('.art:not([hidden])');}});out.textContent=(v||m)?`Pasujące artykuły: ${{n}}.`:'';
try{{const p=new URLSearchParams();if(q.value.trim())p.set('q',q.value.trim());if(m)p.set('pokaz',m);history.replaceState(null,'',p.toString()?'#'+p:location.pathname);}}catch{{}}}}
try{{const p=new URLSearchParams(location.hash.slice(1));if(p.get('q'))q.value=p.get('q');if(p.get('pokaz'))s.value=p.get('pokaz');}}catch{{}}
q.addEventListener('input',run);s.addEventListener('change',run);if(q.value||s.value)run();}})();</script>'''
    HERE.joinpath("index.html").write_text(page("Konstytucja RP na tle świata", body, description="Konstytucja RP artykuł po artykule na tle 188 konstytucji świata.",
                                                css="../panstwa/style.css", current="rp").replace("</head>", '<link rel="stylesheet" href="../rp/rp.css"></head>').replace("</body>", TECZKA))

    # ---------- tematy/<topic>.html and index ----------
    TOPICS_DIR.mkdir(exist_ok=True)
    texts = {k: t for per_topic in variants.values() for secs in per_topic.values() for _, _, t, k in secs}
    trans = store.load(texts)
    sila_labels, prob_labels = store.VOCAB["sila"], store.VOCAB["problemy"]
    topic_problems = defaultdict(lambda: defaultdict(int))  # topic -> problem -> sections tagged
    topic_tagged = defaultdict(int)
    problem_sections = defaultdict(set)  # problem -> unique (doc_id, section_id)
    for key_ in variants:
        for code_, secs_ in variants[key_].items():
            for _, _, _, k in secs_:
                r = trans.get(k)
                if r and r.get("streszczenie"):
                    topic_tagged[key_] += 1
                    for pr in r.get("problemy", []):
                        topic_problems[key_][pr] += 1
                        problem_sections[pr].add(k)

    FACETS = {k: v for k, v in json.loads((ANALYSIS / "warianty/facets.json").read_text()).items() if not k.startswith("_")}
    sys.path.insert(0, str(ANALYSIS / "warianty"))
    import load as warianty_load  # noqa: E402
    facet_recs = warianty_load.load()

    def facet_label(topic, field, value):
        f = FACETS[topic]["fields"][field]
        if f["type"] == "int":
            return "—" if value is None else str(value)
        if f["type"] == "bool3":
            return {"tak": "tak", "nie": "nie", "nie_wynika": "nie wynika z tekstu"}.get(value, str(value))
        if f["type"] == "multi":
            return ", ".join(f["values"].get(v, v) for v in value) if value else "—"
        return f["values"].get(value, str(value))

    def facets_section(topic):
        recs = {c: r for (tp, c), r in facet_recs.items() if tp == topic}
        if topic not in FACETS or not recs:
            return ""
        pl = recs.get("PL")
        blocks = []
        for field, f in FACETS[topic]["fields"].items():
            counts, unknown = Counter(), 0
            for c, r in recs.items():
                v = r["values"].get(field)
                if v in (None, "nie_wynika", []):
                    unknown += 1
                    continue
                for x in (v if isinstance(v, list) else [v]):
                    counts[x] += 1
            known = len(recs) - unknown
            if not counts:
                continue
            if f["type"] == "int":
                nums = sorted(int(k) for k, n in counts.items() for _ in range(n))
                med = nums[len(nums) // 2]
                top = ", ".join(f"{k} ({n})" for k, n in counts.most_common(5))
                body = f'<p>Mediana: <b>{med}</b> · najczęściej: {top} · zakres {nums[0]}–{nums[-1]}</p>'
            else:
                rows = []
                for k, n in counts.most_common():
                    mark = ' <span class="pl-mark">● Polska</span>' if pl and (pl["values"].get(field) == k or (isinstance(pl["values"].get(field), list) and k in pl["values"][field])) else ""
                    rows.append(f'<div class="bar-row"><span>{escape(facet_label(topic, field, [k] if f["type"] == "multi" else k))}</span><span class="bar"><i style="width:{n / max(1, known) * 100:.1f}%"></i></span><b>{n}</b><small>{n / max(1, known):.0%}{mark}</small></div>')
                body = "".join(rows)
            plv = f' <span class="pl-val">Polska: {escape(facet_label(topic, field, pl["values"].get(field)))}</span>' if pl else ""
            blocks.append(f'<div class="facet"><h3>{escape(f["label"])}{plv}</h3>{body}<p class="note">Ustalono w {known} z {len(recs)} konstytucji; w pozostałych tekst tego nie określa (często odsyła do ustawy).</p></div>')
        if pl and pl.get("korekty"):
            blocks.append('<div class="facet"><h3>Korekty ręczne (Polska)</h3>' + "".join(
                f'<p class="note"><b>{escape(FACETS[topic]["fields"][k["field"]]["label"])}</b>: {escape(facet_label(topic, k["field"], k["value"]))}. {escape(k["basis"])}.</p>' for k in pl["korekty"]) + '</div>')
        kw = sorted((c for c, r in recs.items() if r.get("source") == "slowa" and c != "PL"), key=lambda c: name_pl(c, c))
        kw_html = ""
        if kw:
            items = []
            for c in kw:
                r = recs[c]
                vals = " · ".join(f'{escape(FACETS[topic]["fields"][fn]["label"])}: <b>{escape(facet_label(topic, fn, fv))}</b>' for fn, fv in r["values"].items() if fv not in (None, "nie_wynika", []))
                arts_l = ", ".join(a.split(".")[0].replace("Article", "art.").replace("Section", "sekcja") for a in r.get("articles", []) if re.match(r"(Article|Section|Art)", a)) or "pełny tekst"
                url = f'https://www.constituteproject.org/constitution/{r["doc_id"].split(":")[-1]}'
                items.append(f'<li><a href="../panstwa/{c.lower()}.html">{escape(name_pl(c, c))}</a> (<a href="{url}">{escape(arts_l)}</a>): {vals or "tekst tego nie określa"}<span class="quote" title="Cytat ze źródła"> „{escape(r["cytat"][:200])}”</span>{issue_link(f"Wariant {topic}, {name_pl(c, c)}, {arts_l} (tematy/{topic}.html)", "warianty: " + ("; ".join(f"{fn}={fv}" for fn, fv in r["values"].items() if fv not in (None, "nie_wynika", [])) or "nie ustalono"))}</li>')
            kw_html = (f'<details class="kw-found"><summary>Ustalono także w {len(kw)} konstytucjach bez oznaczenia CCP</summary><p class="note">Artykuły znalezione po słowach kluczowych; '
                       f'odczytane tak samo i z tym samym sprawdzeniem cytatu. Nie ma ich na liście przepisów niżej.</p><ul class="facet-badges">{"".join(items)}</ul></details>')
        n_kw = sum(1 for r in recs.values() if r.get("source") == "slowa")
        wide = FACETS[topic].get("ccp_tags")
        source_note = (f'z artykułów oznaczonych tematami CCP: {escape(", ".join(ccp.labels[t].lower() for t in wide))}, z maksymalnie pięciu artykułów znalezionych w każdej konstytucji po słowach kluczowych '
                       f'(z długich artykułów tylko pasujące akapity) i z artykułów, do których odsyłają' if wide else
                       f'z pełnych artykułów oznaczonych tym tematem i artykułów, do których odsyłają{f", a w {n_kw} konstytucjach bez oznaczenia CCP z artykułów znalezionych po słowach kluczowych" if n_kw else ""}')
        return (f'<section class="facets"><h2>Jak to rozwiązano: warianty</h2><p class="note">Wartości odczytane automatycznie (Claude Opus 5.5) z zamkniętej listy, {source_note}. Każda wartość ma dosłowny cytat sprawdzony w źródle. '
                f'Konstytucja może przewidywać kilka rodzajów (np. stanów nadzwyczajnych); zapisano najczęściej opisywany. To nawigacja, nie ocena prawna.</p><div class="facet-grid">{"".join(blocks)}</div>{kw_html}</section>')

    def variant_html(url, a, sec, text, k):
        where = f'<p class="where"><a href="{url}#s{escape(sec)}">{escape(a.replace("Article", "art.").replace("Section", "sekcja"))}</a></p>'
        if not text:
            return f'<div class="variant-text">{where}<p><em>Tekst przy nagłówku; zobacz źródło.</em></p></div>'
        r = trans.get(k)
        if not r:
            return f'<div class="variant-text">{where}<p lang="en">{escape(text)}</p></div>'
        tags = ""
        if r.get("sila"):
            tags += f'<span class="tag sila">{escape(sila_labels.get(r["sila"], r["sila"]))}</span>'
        tags += "".join(f'<a class="tag prob" href="../problemy/{p}.html">{escape(prob_labels[p])}</a>' for p in r.get("problemy", []) if p in prob_labels)
        summary = f'<p class="sum">{escape(r["streszczenie"])}</p>' if r.get("streszczenie") else ""
        if not r["usable"]:
            return (f'<div class="variant-text">{where}{summary}<p lang="en">{escape(text)}</p>'
                    f'<p class="mt-note">Przekład maszynowy nie przeszedł kontroli; pokazano oryginał.</p>{f"<p class=tags>{tags}</p>" if tags else ""}</div>')
        return (f'<div class="variant-text">{where}{summary}<p lang="pl" class="mt">{escape(r["translation"])}</p>'
                f'<details class="orig"><summary>Oryginał (EN)</summary><p lang="en">{escape(text)}</p></details>{f"<p class=tags>{tags}</p>" if tags else ""}</div>')

    rows_index = []
    for key in ccp.topic_keys:
        prev = ccp.prevalence[key]
        cls, word = rarity(float(prev["share"]))
        have = variants.get(key, {})
        refs = pl_refs.get(key, [])
        if refs:
            parts = []
            for ref in refs:
                if ref == 0:
                    parts.append(f'<div class="pl-art"><h3><a href="../rp/index.html#preambula-tekst">Preambuła</a></h3><div class="text">{escape(preamble)}</div></div>')
                elif isinstance(ref, int):
                    parts.append(f'<div class="pl-art"><h3><a href="../rp/index.html#art-{ref}">Art. {ref}</a></h3><div class="text">{escape(arts[ref])}</div></div>')
                else:
                    ch = ref.split("-")[1]
                    title = next(c[3] for c in CHAPTERS if c[0] == ch)
                    parts.append(f'<div class="pl-art"><h3><a href="../rp/index.html#rozdzial-{ch.lower()}">Rozdział {ch}. {escape(title)}</a></h3></div>')
            pl_html = f'<section class="poland yes"><h2>W Konstytucji RP</h2>{"".join(parts)}</section>'
        elif key in review:
            r = review[key]
            pl_html = (f'<section class="poland no"><h2>W Konstytucji RP</h2><p><b>{escape(VERDICT[r["verdict"]])}</b>'
                       f'{f" ({escape(r["polish_basis"])})" if r["polish_basis"] else ""}. {escape(r["note"])}</p></section>')
        else:
            pl_html = ('<section class="poland unknown"><h2>W Konstytucji RP</h2><p>Koderzy CCP nie oznaczyli tego tematu. '
                       'Nie sprawdzono ręcznie, czy Konstytucja RP reguluje go innymi słowami.</p></section>')
        props = [prop_by_id[p] for p in topic_props.get(key, [])]
        props_html = ('<p class="props">Związane propozycje dla Polski: ' + ", ".join(
            f'<a href="../polska/index.html#{p["id"].lower()}">{p["id"]} {escape(p["title"])}</a>' for p in props) + "</p>") if props else ""
        cards = []
        for code in sorted((c for c in have if c != "PL"), key=lambda c: name_pl(c, c)):
            d = ccp.by_code[code]
            y = str(d["year_enacted"] or "")
            recent = (y[:4].isdigit() and int(y[:4]) >= 2000)
            url = f'https://www.constituteproject.org/constitution/{d["id"].split(":")[-1]}'
            secs = "".join(variant_html(url, a, sec, txt, k) for a, sec, txt, k in have[code])
            recs = [trans.get(k) for _, _, _, k in have[code]]
            silas = " ".join(sorted({r["sila"] for r in recs if r and r.get("sila")}))
            probs = " ".join(sorted({p for r in recs if r for p in r.get("problemy", [])}))
            mt = any(r and r["usable"] for r in recs)
            arts_label = ", ".join(a.replace("Article", "art.").replace("Section", "sekcja") for a, _, _, _ in have[code])
            meta = {"id": f"wariant-{key}-{code}", "type": "wariant", "title": f"{name_pl(code, code)}: {ccp.labels[key]}",
                    "cite": f"Konstytucja: {d['title']} ({name_pl(code, code)}), {arts_label}, tekst angielski w Constitute Project, temat CCP „{ccp.topics[key]}”{"; przekład maszynowy (Claude Opus 5.5), nieurzędowy" if mt else ""}",
                    "url": f"{url}#s{have[code][0][1]}"}
            fr = facet_recs.get((key, code))
            main_field = next(iter(FACETS[key]["fields"])) if key in FACETS else None
            main_val = ""
            facet_badges = ""
            if fr:
                mv = fr["values"].get(main_field)
                main_val = " ".join(mv) if isinstance(mv, list) else str(mv)
                facet_badges = '<p class="facet-badges">' + " · ".join(
                    f'{escape(FACETS[key]["fields"][fn]["label"])}: <b>{escape(facet_label(key, fn, fv))}</b>' for fn, fv in fr["values"].items()
                    if fv not in (None, "nie_wynika", [])) + f'<span class="quote" title="Cytat ze źródła">„{escape(fr["cytat"][:240])}”</span></p>'
            secs = facet_badges + secs
            report_current = "warianty: " + "; ".join(f"{fn}={fv}" for fn, fv in fr["values"].items() if fv not in (None, "nie_wynika", [])) if fr else ""
            cards.append(f'<li class="variant" data-eu="{int(code in EU27)}" data-recent="{int(recent)}" data-pl="{int(code == "PL")}" data-sila="{silas}" data-prob="{probs}" data-w="{escape(main_val)}" data-teczka="{escape(json.dumps(meta, ensure_ascii=False))}">'
                         f'<h3><a href="../panstwa/{code.lower()}.html">{escape(name_pl(code, code))}</a> <span>{escape(d["title"])}{" · UE" if code in EU27 else ""}</span>{issue_link(f"Temat {key} ({ccp.labels[key]}), {name_pl(code, code)}, {arts_label} (tematy/{key}.html)", report_current)}</h3><div data-teczka-text>{secs}</div></li>')
        missing = sorted((name_pl(c, c) for c in ccp.by_code if c not in have), key=str.lower)
        body = f'''<p class="crumbs"><a href="index.html">Tematy</a> / {escape(ccp.labels[key])}</p><h1>{escape(ccp.labels[key])}</h1>
<p class="sub"><span class="chip {cls}">{word}</span> {prev["count"]} ze 188 obowiązujących konstytucji. Nazwa w CCP: <i lang="en">{escape(ccp.topics[key])}</i> (<code>{key}</code>).</p>
<div class="topic-head"><div class="bars">{bars(prev)}</div>{pl_html}</div>{props_html}{facets_section(key)}
<h2>Jak to zapisano w innych konstytucjach</h2>
<p class="note">Fragmenty oznaczone przez CCP w angielskich wydaniach Constitute (do trzech na państwo, do 1500 znaków). <b>Polskie przekłady i streszczenia są maszynowe (Claude Opus 5.5) i nieurzędowe</b>; oryginał jest pod każdym przekładem, a link prowadzi do pełnego przepisu. Siła normy i problemy to automatyczne oznaczenia do nawigacji, nie ocena prawna.</p>
<section class="controls variant-controls" aria-label="Filtry"><label class="wide">Szukaj w przepisach<input id="q" type="search" placeholder="np. referendum, two-thirds" autocomplete="off"></label>
<label>Państwa<select id="grp"><option value="">wszystkie</option><option value="eu">tylko UE</option><option value="recent">uchwalone od 2000 r.</option></select></label>
<label>Siła normy<select id="sila"><option value="">każda</option>{"".join(f'<option value="{k}">{escape(v)}</option>' for k, v in sila_labels.items())}</select></label>
{f'<label>{escape(FACETS[key]["fields"][next(iter(FACETS[key]["fields"]))]["label"])}<select id="wvar"><option value="">każdy</option>' + "".join(f'<option value="{vk}">{escape(vl)}</option>' for vk, vl in FACETS[key]["fields"][next(iter(FACETS[key]["fields"]))].get("values", {}).items() if vk != "nie_wynika") + '</select></label>' if key in FACETS and FACETS[key]["fields"][next(iter(FACETS[key]["fields"]))].get("values") else ''}
<label>Problem<select id="prob"><option value="">każdy</option>{"".join(f'<option value="{k}">{escape(v)}</option>' for k, v in prob_labels.items())}</select></label></section>
<p class="summary" id="summary" aria-live="polite"></p><p class="note">Konstytucja RP jest wyżej i nie jest liczona w tej liście.</p><ol class="variants">{"".join(cards)}</ol>
<details class="table-box"><summary>Konstytucje bez tego tematu w kodowaniu CCP ({len(missing)})</summary><p class="note">{escape(", ".join(missing))}</p></details>
<script>(()=>{{const $=id=>document.getElementById(id),q=$('q'),g=$('grp'),si=$('sila'),pr=$('prob'),s=$('summary');const items=[...document.querySelectorAll('.variant')];const t=items.map(i=>i.textContent.toLowerCase());
const wv=$('wvar');const F={{q:q,grupa:g,sila:si,problem:pr,wariant:wv}};
try{{const h=new URLSearchParams(location.hash.slice(1));for(const[k,el]of Object.entries(F))if(el&&h.get(k))el.value=h.get(k);}}catch{{}}
const inList=(v,l)=>!v||(' '+l+' ').includes(' '+v+' ');if(wv)wv.addEventListener('change',()=>run());
const save=()=>{{try{{const p=new URLSearchParams();for(const[k,el]of Object.entries(F))if(el&&el.value.trim())p.set(k,el.value.trim());history.replaceState(null,'',p.toString()?'#'+p:location.pathname+location.search);}}catch{{}}}};
function run(){{save();const v=q.value.trim().toLowerCase();let n=0;items.forEach((i,k)=>{{const ok=(!v||t[k].includes(v))&&(!g.value||i.dataset[g.value]==='1')&&inList(si.value,i.dataset.sila)&&inList(pr.value,i.dataset.prob)&&(!wv||inList(wv.value,i.dataset.w||''));i.hidden=!ok;n+=ok;}});s.textContent=`Pokazano ${{n}} z ${{items.length}} konstytucji.`;}}
q.addEventListener('input',run);[g,si,pr].forEach(e=>e.addEventListener('change',run));run();}})();</script>'''
        (TOPICS_DIR / f"{key}.html").write_text(page(f"{ccp.labels[key]}: warianty przepisów", body, description=f"{ccp.labels[key]} w konstytucjach świata.",
                                                     css="../panstwa/style.css", current="tematy").replace("</head>", '<link rel="stylesheet" href="../rp/rp.css"></head>').replace("</body>", TECZKA))
        rows_index.append((key, ccp.labels[key], ccp.topics[key], int(prev["count"]), int(prev["count_eu27"]), bool(refs), cls, word))

    trs = "".join(f'<tr data-pl="{int(pl)}" data-name="{escape(l.lower())} {escape(en.lower())} {k}"><th scope="row"><a href="{k}.html">{escape(l)}</a><span lang="en">{escape(en)}</span></th>'
                  f'<td data-v="{n}">{n / 188:.0%}</td><td data-v="{eu}">{eu}/27</td><td><span class="chip {c}">{w}</span></td><td>{"tak" if pl else escape(VERDICT[review[k]["verdict"]]) if k in review else "—"}</td></tr>'
                  for k, l, en, n, eu, pl, c, w in rows_index)
    body = f'''<p class="crumbs">Tematy</p><h1>Tematy konstytucyjne</h1>
<p class="sub">331 rozwiązań w kodowaniu Comparative Constitutions Project. Każdy temat prowadzi do zestawienia, jak zapisały go obowiązujące konstytucje, z polskim przepisem na górze.</p>
<section class="controls rp-controls" aria-label="Filtry"><label class="wide">Szukaj tematu<input id="q" type="search" placeholder="np. sąd, kadencja, woda" autocomplete="off"></label>
<label>Pokaż<select id="pl"><option value="">wszystkie</option><option value="0">nieoznaczone w Konstytucji RP</option><option value="1">oznaczone w Konstytucji RP</option></select></label>
<label>Sortuj<select id="sort"><option value="name">alfabetycznie</option><option value="desc">najczęstsze</option><option value="asc">najrzadsze</option></select></label></section>
<p class="summary" id="summary" aria-live="polite"></p>
<div class="table-scroll"><table class="topics"><thead><tr><th scope="col">Rozwiązanie</th><th scope="col">Świat</th><th scope="col">UE</th><th scope="col">Jak często</th><th scope="col">Konstytucja RP</th></tr></thead><tbody id="rows">{trs}</tbody></table></div>
<p class="note">„Konstytucja RP: —” oznacza brak tagu CCP, nie zawsze brak przepisu. Sprawdzone luki: <a href="../polska/index.html#na-tle-swiata">Polska na tle świata</a>.</p>
<script>(()=>{{const q=document.getElementById('q'),pl=document.getElementById('pl'),so=document.getElementById('sort'),tb=document.getElementById('rows'),s=document.getElementById('summary');const rows=[...tb.rows];
function run(){{const v=q.value.trim().toLowerCase();let n=0;rows.forEach(r=>{{const ok=(!v||r.dataset.name.includes(v))&&(!pl.value||r.dataset.pl===pl.value);r.hidden=!ok;n+=ok;}});
const sorted=[...rows];if(so.value!=='name')sorted.sort((a,b)=>(so.value==='desc'?-1:1)*(a.cells[1].dataset.v-b.cells[1].dataset.v));sorted.forEach(r=>tb.appendChild(r));s.textContent=`Pokazano ${{n}} z ${{rows.length}} tematów.`;}}
[q,pl,so].forEach(e=>e.addEventListener(e===q?'input':'change',run));run();}})();</script>'''
    (TOPICS_DIR / "index.html").write_text(page("Tematy konstytucyjne", body, description="331 tematów konstytucyjnych z wariantami przepisów.",
                                               css="../panstwa/style.css", current="tematy").replace("</head>", '<link rel="stylesheet" href="../rp/rp.css"></head>'))
    # ---------- problemy/<code>.html and index ----------
    PROBLEMS_DIR = ANALYSIS / "problemy"
    PROBLEMS_DIR.mkdir(exist_ok=True)
    prob_index = []
    for pcode, plabel in prob_labels.items():
        ranked = []
        for tk, counts in topic_problems.items():
            if topic_tagged[tk] >= 3 and counts.get(pcode):
                ranked.append((counts[pcode] / topic_tagged[tk], counts[pcode], tk))
        ranked.sort(reverse=True)
        core = [tk for share, n, tk in ranked if share >= 0.5]
        sections_n = len(problem_sections[pcode])
        rows = "".join(
            f'<tr><th scope="row"><a href="../tematy/{tk}.html#problem={pcode}">{escape(ccp.labels[tk])}</a><span lang="en">{escape(ccp.topics[tk])}</span></th>'
            f'<td>{share:.0%}</td><td>{n}</td><td>{float(ccp.prevalence[tk]["share"]):.0%}</td><td>{"tak" if pl_refs.get(tk) else "—"}</td></tr>'
            for share, n, tk in ranked[:40])
        pl_arts = sorted({r for tk in core for r in pl_refs.get(tk, []) if isinstance(r, int) and r > 0})
        arts_html = (", ".join(f'<a href="../rp/index.html#art-{a}">art. {a}</a>' for a in pl_arts)) or "brak przypisanych artykułów"
        props = sorted({pid for tk in core for pid in topic_props.get(tk, [])})
        props_html = ", ".join(f'<a href="../polska/index.html#{pid.lower()}">{pid} {escape(prop_by_id[pid]["title"])}</a>' for pid in props) or "brak"
        body = f'''<p class="crumbs"><a href="index.html">Problemy</a> / {escape(plabel)}</p><h1>{escape(plabel)}</h1>
<p class="sub">Przepisy konstytucji świata, które dotyczą tego problemu, według automatycznych oznaczeń przy przekładzie ({sections_n} fragmentów). Wybierz temat, aby zobaczyć warianty przefiltrowane do tego problemu.</p>
<section class="poland yes"><h2>W Konstytucji RP</h2><p>Artykuły z tematami najsilniej związanymi z problemem: {arts_html}.</p><p class="props">Propozycje dla Polski: {props_html}</p></section>
<h2>Tematy związane z problemem</h2>
<div class="table-scroll"><table class="topics"><thead><tr><th scope="col">Temat</th><th scope="col">Udział fragmentów tematu</th><th scope="col">Fragmenty</th><th scope="col">Świat</th><th scope="col">Konstytucja RP</th></tr></thead><tbody>{rows or '<tr><td colspan="5">Brak danych.</td></tr>'}</tbody></table></div>
<p class="note">Oznaczenia problemów nadał model językowy przy tłumaczeniu, z zamkniętej listy, do trzech na fragment. Służą nawigacji; nie są oceną prawną. „Udział fragmentów tematu”: jaka część oznaczonych fragmentów danego tematu dotyczy tego problemu.</p>'''
        (PROBLEMS_DIR / f"{pcode}.html").write_text(page(f"{plabel}: konstytucje świata", body, description=plabel,
                                                     css="../panstwa/style.css", current="problemy").replace("</head>", '<link rel="stylesheet" href="../rp/rp.css"></head>'))
        prob_index.append((pcode, plabel, sections_n, len(core)))
    cards = "".join(f'<li><a href="{c}.html">{escape(l)}</a><span class="meta">{n} fragmentów · {k} głównych tematów</span></li>' for c, l, n, k in prob_index)
    body = f'''<p class="crumbs">Problemy</p><h1>Problemy polskiej debaty</h1>
<p class="sub">Zacznij od pytania, nie od kodu. Każdy problem prowadzi do tematów konstytucyjnych, artykułów Konstytucji RP, propozycji i przepisów innych państw.</p>
<ul class="countries">{cards}</ul>
<p class="note">Oznaczenia nadane automatycznie przy przekładzie (Claude Opus 5.5) z zamkniętej listy 23 problemów.</p>'''
    (PROBLEMS_DIR / "index.html").write_text(page("Problemy polskiej debaty", body, description="Wejście problemowe do konstytucji świata.",
                                                 css="../panstwa/style.css", current="problemy").replace("</head>", '<link rel="stylesheet" href="../rp/rp.css"></head>'))

    print(json.dumps({"articles": len(arts), "articles_with_topics": total_tagged, "topic_pages": len(rows_index),
                      "poland_topics": sum(1 for r in rows_index if r[5])}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
