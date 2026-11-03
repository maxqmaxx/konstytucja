#!/usr/bin/env python3
"""Build the Polish adaptation view from editorial inputs and verified sources."""

from collections import Counter
import csv
from datetime import datetime, timezone
import hashlib
from html import escape
import json
import os
from pathlib import Path
import re

from editorial import AVOID, PROPOSALS
import world

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
ATLAS = HERE.parent / "zapisy.json"
LABELS = {
    "domain": {"ustroj": "Ustrój i kontrola władzy", "potencjal": "Zdolności i odporność państwa", "prawa": "Prawa i usługi", "udzial": "Udział obywateli"},
    "verdict": {"rekomendowane": "Rekomendowane", "debata": "Do debaty", "zachowac": "Zachować"},
    "change": {"jest": "Już jest w Konstytucji RP", "wzmocnienie": "Wzmocnienie obecnych zasad", "nowe": "Nowa wyraźna gwarancja"},
    "level": {"konstytucja": "Konstytucja + wykonanie ustawowe", "ustawa": "Najpierw ustawa i wykonanie"},
}
PL_URL = "https://eli.gov.pl/eli/DU/1997/483/ogl"
PDF_URL = "https://eli.gov.pl/api/acts/DU/1997/483/text/U/D19970483Lj.pdf"
EU_URL = "https://eur-lex.europa.eu/eli/treaty/teu_2016/oj/eng"


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def local(path):
    return os.path.relpath(ROOT / path, HERE)


def pl_links(articles):
    return ", ".join(f'<a href="sources/konstytucja-rp.html#art-{n}">art. {n}</a>' for n in articles)


def source_links(entry):
    return (f'<a href="../ATLAS.html#{entry["id"].lower()}">{entry["id"]}: {escape(entry["country"])}, {escape(entry["provision"])}</a>'
            f' · <a href="{escape(entry["source_url"], quote=True)}">tekst u wydawcy</a>'
            f' · <a href="{escape(local(entry["source_text_path"]), quote=True)}">tekst w archiwum</a>'
            f'<small>{escape(entry["document_title"])}; {escape(entry["period"])}.</small>')


def polish_source():
    raw = (HERE / "sources/konstytucja-rp-ujednolicony.txt").read_text()
    clean = re.sub(r"(?m)^.*(?:©Kancelaria Sejmu|2015-01-07).*$", "", raw).replace("\f", "")
    parts = re.split(r"(?m)^\s*Art\.\s+(\d+)\.", clean)
    articles = {int(parts[i]): parts[i + 1].strip() for i in range(1, len(parts), 2)}
    if set(articles) != set(range(1, 244)):
        raise ValueError("The official source must contain all 243 articles")
    content = "".join(f'<section id="art-{n}"><h2>Art. {n}</h2><pre>{escape(text)}</pre></section>' for n, text in articles.items())
    (HERE / "sources/konstytucja-rp.html").write_text('''<!doctype html><html lang="pl"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Konstytucja RP: źródło porównania</title><style>body{max-width:850px;margin:35px auto;padding:0 20px;font:17px/1.7 system-ui;color:#172a39}a{color:#006858}section{scroll-margin-top:24px;border-top:1px solid #ddd;margin:35px 0}pre{font:inherit;white-space:pre-wrap;overflow-wrap:anywhere}:target{background:#fff4d7}h1{line-height:1.2}</style><a href="../index.html">← Propozycje dla Polski</a><h1>Konstytucja RP: tekst źródłowy</h1><p>Roboczy odczyt urzędowego tekstu ujednoliconego. Przy rozbieżności rozstrzyga PDF, nie ekstrakcja.</p><p><a href="konstytucja-rp-ujednolicony.pdf">Urzędowy PDF w archiwum</a> · <a href="https://eli.gov.pl/eli/DU/1997/483/ogl">Metryka ELI</a></p><p>PDF oznaczony datą opracowania 2015-01-07. Metrykę sprawdzono 2026-11-01: wskazuje dwie ustawy zmieniające, z 2006 i 2009 r. Data aktualizacji metryki nie jest datą zmiany Konstytucji. Nie jest to analiza orzecznictwa ani praktyki ustrojowej.</p>''' + content + "</html>")
    return articles


def prepare():
    atlas = {e["id"]: e for e in json.loads(ATLAS.read_text())}
    articles = polish_source()
    used = set()
    for item in PROPOSALS:
        for name, mapping in LABELS.items():
            if item[name] not in mapping:
                raise ValueError((item["id"], name))
        if not set(item["polish_articles"]) <= articles.keys():
            raise ValueError("Unknown Polish article")
        item["sources"] = [atlas[key] for key in item["inspirations"]]
        used.update(item["inspirations"])
    for item in AVOID:
        item["inspirations"] = item["sources"].split()
        item["source_entries"] = [atlas[key] for key in item["inspirations"]]
        used.update(item["inspirations"])
    for key in used:
        entry = atlas[key]
        if digest(ROOT / entry["source_text_path"]) != entry["source_sha256"]:
            raise ValueError("Source text changed: " + key)
    return atlas, used


def markdown():
    lines = ["# Co Polska mogłaby wdrożyć w nowej konstytucji", "", "Opracowanie porównawcze, 2026-11-01. Wersja robocza do debaty publicznej.", "",
        "24 propozycje na podstawie atlasu 130 zapisów. Każdy szkic jest autorski: nie stanowi cytatu z obcej konstytucji ani gotowej, uzgodnionej ustawy konstytucyjnej.", "",
        "## Najważniejsze ustalenia", "",
        "- Zachować już istniejące gwarancje, w tym godność, proporcjonalność, konstruktywne wotum nieufności i cywilną kontrolę wojska.",
        "- Priorytetem jest skuteczność ochrony praw, niezależna kontrola i jawność finansów, a nie sama liczba nowych deklaracji.",
        "- Oddzielić moc państwa jako zdolność do działania od niekontrolowanej władzy jego przywódcy.",
        "- Prawo do wody, inicjatywa konstytucyjna obywateli i klauzula rdzenia wymagają osobnych decyzji politycznych oraz testów skutków.",
        "- Część propozycji można wdrożyć ustawą i wykonaniem obecnej Konstytucji; nowy tekst nie jest warunkiem każdej poprawy.", "",
        "## Założenia i granice", "",
        "Przyjmuję demokratyczne, pluralistyczne państwo z ochroną praw, pokojową zmianą władzy i zdolnością obrony. Zachowuję jednolity charakter Polski; wariant relacji prezydenta z rządem pozostawiam do debaty. Oceny są redakcyjne, a korzyści są hipotezami mechanizmów, nie dowiedzionymi skutkami transplantacji prawa.", "",
        f"Stan polskiego tekstu porównano z [metryką ELI]({PL_URL}) i [tekstem ujednoliconym]({PDF_URL}), pobranymi 2026-11-01. Opracowanie PDF jest datowane 2015-01-07; aktualna metryka wskazuje zmiany z 2006 i 2009 r. Nie mylić daty aktualizacji metryki z nowelizacją. [Kopia lokalna](sources/konstytucja-rp-ujednolicony.pdf).", "",
        "Źródła zagraniczne to wskazane wydania archiwalne, nie potwierdzenie ich dzisiejszego obowiązywania. Islandia 2011 i Chile 2022 są projektami. Nie wykonano przeglądu całego orzecznictwa, prawa zwykłego, kosztorysu ani kompletnej kontroli zobowiązań międzynarodowych.", "",
        "## Sześć punktów na początek", ""]
    lines += [f"- [{p['id']}. {p['title']}](#{p['id'].lower()})" for p in PROPOSALS if p["starter"]]
    lines += ["", "## Propozycje", ""]
    for p in PROPOSALS:
        lines += [f'<a id="{p["id"].lower()}"></a>', f"### {p['id']}. {p['title']}", "",
            " · ".join(LABELS[name][p[name]] for name in ("domain", "verdict", "change", "level")), "",
            f"**W Polsce dziś:** {p['poland']}", "",
            "Podstawa: " + ", ".join(f"[art. {n}](sources/konstytucja-rp.html#art-{n})" for n in p["polish_articles"]) + ".", "",
            f"**Szkic autorski:** {p['draft']}", "", f"**Możliwa korzyść:** {p['benefit']}", "",
            f"**Ryzyko:** {p['risk']}", "", f"**Niezbędne zabezpieczenia:** {p['safeguards']}", "",
            f"**Wdrożenie i różnica wobec inspiracji:** {p['implementation']}", "", "**Źródła inspiracji:**", ""]
        for s in p["sources"]:
            lines += [f"- [{s['id']}: {s['country']}, {s['provision']}](../ATLAS.html#{s['id'].lower()}); {s['document_title']}; {s['period']}. [Tekst źródłowy]({s['source_url']}) · [Kopia tekstu]({local(s['source_text_path'])})."]
        lines += [""]
    lines += ["## Osiem wzorców, których nie rekomenduję", ""]
    for item in AVOID:
        links = ", ".join(f"[{key}](../ATLAS.html#{key.lower()})" for key in item["inspirations"])
        lines += [f"### {item['id']}. {item['title']}", "", f"**Waga ryzyka: {item['severity']}.** {item['reason']}", "", f"**Zamiast tego:** {item['alternative']}", "", f"Inspiracje ostrzegawcze: {links}.", ""]
    lines += ["## Mechanizmy, wykonalność i warunki niepowodzenia", "",
        "Ocena jakościowa. Prawdopodobieństwo dotyczy możliwości uruchomienia mechanizmu przy zapewnionym finansowaniu i kontroli; nie jest prognozą liczbową sukcesu państwa.", "",
        "| Mechanizm | Prawdopodobieństwo zadziałania | Potencjalny wpływ | Sterowalność | Co podważy korzyść |", "|---|---|---|---|---|",
        "| Pilna ochrona praw | Umiarkowane | Duży | Umiarkowana | Brak kadr i nadużywanie trybu |",
        "| Niezależna kontrola władzy | Warunkowe | Bardzo duży | Ograniczona samym tekstem | Przejęcie nominacji lub niewykonywanie wyroków |",
        "| Jawny obraz finansów | Umiarkowane do wysokiego | Duży | Duża dla publikacji danych | Niepełne definicje i nierzetelne dane |",
        "| Nauka i zdolności administracji | Warunkowe, długoterminowe | Duży | Umiarkowana | Finansowanie doraźne i polityczne konkursy |",
        "| Udział obywateli | Umiarkowane | Zależny od procedury | Umiarkowana | Nierówność informacji i finansowania |",
        "| Odporność usług i zasobów | Umiarkowane | Duży w kryzysie | Duża dla planów i ćwiczeń | Brak testów i odpowiedzialności za wykonanie |", "",
        "## Kontrola ryzyk projektu i lista prac", "",
        "| Waga | Ustalenie | Zalecenie | Konkretna kolejna praca |", "|---|---|---|---|",
        "| critical | Reguły nominacji mogą służyć przejęciu kontroli | Nie uchwalać samych haseł niezależności | Zasymulować wybór, wakat, bojkot i zmianę większości dla każdego organu |",
        "| critical | Niezgodne przepisy przejściowe mogą zmienić sens limitów i praw | Projektować je razem z tekstem głównym | Opracować mapę kadencji, praw nabytych, środków odwoławczych i dat wejścia w życie |",
        "| major | Niektóre gwarancje już istnieją | Sprawdzić wykonanie przed nowelizacją | Audyt luk ustawowych dla P02, P07, P08, P12, P18, P21-P23 |",
        "| major | Brak oszacowanych kosztów | Nie obiecywać automatycznych świadczeń bez zasobów | Kosztorys środków sądowych, wody i praw społecznych |",
        "| major | Przeniesienie normy nie dowodzi skuteczności | Testować konkretne mechanizmy | Pilotaż ustawowy, terminy ewaluacji i jawne wskaźniki rezultatów |",
        "| major | Niezbadane wszystkie relacje z prawem UE i umowami | Wykonać osobną kontrolę każdego projektu | Macierz zgodności z art. 9, 90 i 91 RP, TUE, EKPC i umowami sektorowymi |", "",
        "## Droga od inspiracji do projektu", "",
        "1. Uzgodnić cele, model władzy wykonawczej i katalog praw; nie zaczynać od wyjątków dla obecnych osób.",
        "2. Zestawić istniejące gwarancje z lukami ich wykonania i wybrać część możliwą do wdrożenia ustawą.",
        "3. Opracować rozłączne warianty spornych rozwiązań wraz z kosztami i scenariuszami nadużycia.",
        "4. Napisać wspólnie przepisy materialne, procedury kontroli, finansowanie oraz regulacje przejściowe.",
        "5. Przeprowadzić kontrolę prawną, konsultacje i symulację kryzysu instytucjonalnego.",
        "6. W ramach obecnego porządku punktem odniesienia dla zmiany jest art. 235. Nie zakładać, że zwykłe referendum z art. 125 samo zastępuje ten tryb; całościowe zastąpienie Konstytucji wymaga osobnej analizy trybu i legitymizacji.", "",
        f"[Konstytucja RP, metryka]({PL_URL}) · [TUE, źródło zobowiązań europejskich]({EU_URL}) · [Interaktywny widok](index.html) · [Dane JSON](propozycje.json) · [CSV](propozycje.csv)", "",
        "## Metoda", "",
        "Selekcja redakcyjna z istniejącego atlasu. Dla każdej propozycji zapisano identyfikatory inspiracji, dokładne wydania, polskie przepisy porównawcze, własny szkic, mechanizm korzyści, ryzyko i zabezpieczenia. Budowa sprawdza sumy tekstów inspiracji oraz obecność wszystkich polskich artykułów. Nie jest to automatyczna analiza całego archiwum ani pełny projekt aktu prawnego. Kategorie i rekomendacje nie są rankingiem państw lub partii.", ""]
    (HERE / "POLSKA.md").write_text("\n".join(lines))


def html_view():
    evidence, topic_labels, review, prevalence = world.load()
    cards = []
    for p in PROPOSALS:
        badges = "".join(f'<span class="badge {p[name]}">{escape(LABELS[name][p[name]])}</span>' for name in ("verdict", "change", "level"))
        sources = "".join(f"<li>{source_links(s)}</li>" for s in p["sources"])
        meta = escape(json.dumps({"id": f"propozycja-{p['id']}", "type": "propozycja", "title": f"{p['id']}: {p['title']}", "anchor": p['id'].lower(),
                                  "cite": f"Konstytucje świata, Dla Polski, propozycja {p['id']} (opracowanie redakcyjne do debaty, 2026-11-01)"}, ensure_ascii=False))
        cards.append(f'''<article class="proposal" id="{p['id'].lower()}" data-id="{p['id']}" data-teczka="{meta}">
<div class="card-top"><span class="eyebrow">{p['id']} / {escape(LABELS['domain'][p['domain']])}</span><label class="choose"><input type="checkbox" data-compare="{p['id']}"> Porównaj</label></div>
<h2><a href="#{p['id'].lower()}">{escape(p['title'])}</a></h2><div class="badges">{badges}</div>
<h3>W Polsce dziś</h3><p>{escape(p['poland'])}</p><p class="references">Konstytucja RP: {pl_links(p['polish_articles'])}.</p>
<div class="draft"><h3>Szkic autorski <span>do dalszego opracowania</span></h3><p data-teczka-text>{escape(p['draft'])}</p></div>
<h3>Co może dać</h3><p>{escape(p['benefit'])}</p><div class="risk"><h3>Główne ryzyko</h3><p>{escape(p['risk'])}</p></div>{world.card_block(p['id'], evidence, topic_labels, review)}{world.path_block(p)}
<details><summary>Zabezpieczenia, wdrożenie i źródła</summary><h3>Niezbędne zabezpieczenia</h3><p>{escape(p['safeguards'])}</p><h3>Wdrożenie i granice inspiracji</h3><p>{escape(p['implementation'])}</p><h3>Źródła zagraniczne</h3><ul class="sources">{sources}</ul></details></article>''')
    negative = "".join(f'''<article class="avoid"><span class="eyebrow">{item['id']} / ryzyko {item['severity']}</span><h3>{escape(item['title'])}</h3><p>{escape(item['reason'])}</p><p><strong>Lepszy kierunek:</strong> {escape(item['alternative'])}</p><details><summary>Źródła ostrzegawcze</summary><ul class="sources">{''.join('<li>' + source_links(s) + '</li>' for s in item['source_entries'])}</ul></details></article>''' for item in AVOID)
    starter = "".join(f'<a href="#{p["id"].lower()}"><span>{p["id"]}</span>{escape(p["title"])}</a>' for p in PROPOSALS if p["starter"])
    page = (HERE / "template.html").read_text()
    embedded = json.dumps({"items": [{k: v for k, v in p.items() if k != "sources"} for p in PROPOSALS], "labels": LABELS}, ensure_ascii=False).replace("<", "\\u003c")
    replacements = {"@@WORLD@@": world.overview(topic_labels, review, prevalence), "@@CARDS@@": "\n".join(cards), "@@AVOID@@": negative, "@@STARTER@@": starter, "@@DATA@@": embedded,
                    "@@COUNT@@": str(len(PROPOSALS)), "@@NEW@@": str(sum(p["change"] == "nowe" for p in PROPOSALS)),
                    "@@STATUTE@@": str(sum(p["level"] == "ustawa" for p in PROPOSALS))}
    for name in ("domain", "verdict", "change", "level"):
        replacements[f"@@{name.upper()}@@"] = "".join(f'<option value="{key}">{escape(value)}</option>' for key, value in LABELS[name].items())
    for token, value in replacements.items():
        page = page.replace(token, value)
    if "@@" in page:
        raise ValueError("Unresolved template marker")
    (HERE / "index.html").write_text(page)


def main():
    atlas, used = prepare()
    markdown()
    html_view()
    output = {"scope": "Autorskie warianty dla Polski na podstawie wyboru z atlasu; nie gotowy projekt konstytucji", "checked_at": "2026-11-01", "labels": LABELS,
              "polish_source": {"url": PL_URL, "pdf_url": PDF_URL, "pdf_sha256": digest(HERE / "sources/konstytucja-rp-ujednolicony.pdf")},
              "proposals": PROPOSALS, "avoid": AVOID}
    (HERE / "propozycje.json").write_text(json.dumps(output, ensure_ascii=False, indent=2) + "\n")
    fields = ["id", "title", "domain", "verdict", "change", "level", "poland", "draft", "benefit", "risk", "safeguards", "implementation", "polish_articles", "inspirations", "source_urls"]
    with (HERE / "propozycje.csv").open("w", encoding="utf-8-sig", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=fields)
        writer.writeheader()
        for p in PROPOSALS:
            row = {key: p[key] for key in fields if key != "source_urls"}
            for name in LABELS:
                row[name] = LABELS[name][p[name]]
            row["polish_articles"] = "; ".join(map(str, p["polish_articles"]))
            row["inspirations"] = "; ".join(p["inspirations"])
            row["source_urls"] = "; ".join(s["source_url"] for s in p["sources"])
            writer.writerow(row)
    result = {"generated_at": datetime.now(timezone.utc).isoformat(), "proposals": len(PROPOSALS), "avoid": len(AVOID),
              "starter": sum(p["starter"] for p in PROPOSALS), "inspirations": len(used),
              "verdicts": dict(Counter(p["verdict"] for p in PROPOSALS)), "levels": dict(Counter(p["level"] for p in PROPOSALS)),
              "changes": dict(Counter(p["change"] for p in PROPOSALS)), "source_hashes_verified": True,
              "complete_legal_review": False, "foreign_current_validity_verified": False,
              "inputs": {name: digest(HERE / name) for name in ("editorial.py", "build.py", "template.html", "style.css", "app.js", "sources/eli-metadata.json", "sources/konstytucja-rp-ujednolicony.pdf")}}
    (HERE / "validation.json").write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n")
    print(json.dumps(result, ensure_ascii=False))


if __name__ == "__main__":
    main()
