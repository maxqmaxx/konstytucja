#!/usr/bin/env python3
"""Build a reproducible screening register and an editorial atlas of constitutional clauses."""

import argparse
from collections import Counter
import csv
import hashlib
import html
import json
from pathlib import Path
import re
import unicodedata
from bs4 import BeautifulSoup
from babel import Locale
from datetime import datetime, timezone

ROOT = Path(__file__).resolve().parents[1]
OUT = Path(__file__).resolve().parent

CATEGORIES = {
    "ciekawe": "Najciekawsze",
    "oryginalne": "Najoryginalniejsze",
    "kontrowersyjne": "Najbardziej kontrowersyjne",
    "wazne": "Kluczowe dla danego ustroju",
    "niebezpieczne": "Największe ryzyka ustrojowe",
    "dziwne": "Najbardziej zaskakujące",
    "panstwo": "Potencjał państwa i społeczeństwa",
    "wladca": "Koncentracja władzy przywódcy",
    "trudne": "Najtrudniejsze do interpretacji",
}

TOPICS = {
    "sovereignty": ("Suwerenność i źródło władzy", r"\b(?:sovereign\w*|souverain\w*|suweren\w*|soberan\w*|sovran\w*|souveran\w*)\b"),
    "rights": ("Prawa i równość", r"\b(?:fundamental rights|human rights|equal protection|droits fondamentaux|droits de l.homme|prawa czlowieka|rowni wobec|derechos fundamentales|diritti fondamentali|grundrechte|menschenwurde)\b"),
    "emergency": ("Stan nadzwyczajny i zawieszanie praw", r"\b(?:state of emergency|martial law|suspend\w*|etat d.urgence|etat de siege|pleins pouvoirs|stan wojenny|stan wyjatkowy|estado de excepcion|estado de sitio|ausnahmezustand|notstand)\b"),
    "accountability": ("Kontrola władzy i odpowiedzialność", r"\b(?:judicial review|constitutional court|impeach\w*|vote of no confidence|cour constitutionnelle|responsabilite|trybunal konstytucyjny|wotum nieufnosci|tribunal constitucional|verfassungsgericht|sfiducia)\b"),
    "power": ("Koncentracja władzy i blokowanie zmian", r"\b(?:supreme leader|absolute power|inviolab\w*|shall not be challenged|notwithstanding|unamend\w*|command\w*.in.chief|pouvoir absolu|ne peut etre revise|nie podlega|nie moze byc zmien|irrevocab\w*|unabander\w*)\b"),
    "capacity": ("Finanse, wiedza i zdolność działania", r"\b(?:public debt|budget\w*|tax\w*|scientific|research|innovation|dette publique|impot\w*|recherche scientifique|dlug publiczny|badania naukowe|deuda publica|forschung|ricerca scientifica)\b"),
    "unusual": ("Szczególne rozwiązania i tożsamość", r"\b(?:rights of nature|dignity of living|gross national happiness|forest cover|minarets?|nuclear|sece\w*|secess\w*|hereditar\w*|eternal|insurrection|bon fils|polonais|droits de la nature|szczesc\w*|genetisch\w*)\b"),
}
SCREEN_LANGUAGES = {"en", "fr", "pl", "es", "de", "it", "pt"}


def normalized(text):
    text = text.translate(str.maketrans({"ł": "l", "Ł": "L", "ß": "ss", "ø": "o"}))
    return "".join(c for c in unicodedata.normalize("NFD", text).lower() if not unicodedata.combining(c))


def catalog():
    return [json.loads(line) for line in (ROOT / "catalog.jsonl").read_text(encoding="utf-8").splitlines()]


def write_json(path, data):
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def headings(lines):
    pattern = re.compile(r"^\s*(?:(?:article|art[.]?|artykul|artikel|articulo|artigo|section|§)\s*(?:[0-9]+[a-zA-Z]*(?:[.][0-9]+)?|[IVXLC]+|premier|unique)\b|(?:[0-9]{1,3}[a-zA-Z]?[.]\s+[A-ZÀ-Ž]))", re.I)
    out = []
    for index, line in enumerate(lines):
        if ". . ." in line or re.search(r"\.{4,}", line):
            continue
        if len(line.strip()) < 180 and pattern.match(normalized(line)):
            out.append((index + 1, line.strip()))
    return out


def locate_heading(found, line):
    previous = [(n, title) for n, title in found if n <= line]
    return previous[-1] if previous else (1, "Numer przepisu do ustalenia")


def screen():
    records = catalog()
    rows, candidates, hashes = [], [], {}
    patterns = {key: re.compile(pattern, re.I) for key, (_, pattern) in TOPICS.items()}
    for item in records:
        text_info = item.get("text")
        row = {"id": item["id"], "country_code": item["country_code"], "country": item["country"], "title": item["title"], "language": item["language"],
               "status": item["status"], "source_url": item["source_url"], "has_source_file": bool(item.get("assets")), "has_text": bool(text_info),
               "screening": "brak pobranego pliku" if not item.get("assets") else "brak tekstu, skan lub problem ekstrakcji", "text_path": "", "sha256": "", "headings_detected": 0, "topics": "", "duplicate_of": ""}
        if text_info:
            path = ROOT / text_info["path"]
            text = path.read_text(encoding="utf-8")
            sha = hashlib.sha256(path.read_bytes()).hexdigest()
            if sha != text_info["sha256"]:
                raise ValueError("Input text hash differs from archive catalog: " + str(path))
            lines = text.splitlines()
            found_headings = headings(lines)
            row.update(text_path=text_info["path"], sha256=sha, headings_detected=len(found_headings), duplicate_of=hashes.get(sha, ""))
            hashes.setdefault(sha, item["id"])
            if item["language"] in SCREEN_LANGUAGES:
                detected = Counter()
                choices = {}
                # Evaluate complete text, including historical editions; skip PDF table-of-contents lines.
                for index, line in enumerate(lines):
                    if ". . ." in line or "PDF generated" in line or "constituteproject.org" in line:
                        continue
                    norm = normalized(line)
                    for key, pattern in patterns.items():
                        if pattern.search(norm):
                            detected[key] += 1
                            ref_line, ref = locate_heading(found_headings, index + 1)
                            # A locator is a reading aid, not a validated constitutional citation.
                            choices.setdefault(key, (ref_line, ref, index + 1))
                for key, (ref_line, ref, matched_line) in choices.items():
                    candidates.append({"document_id": item["id"], "topic": key, "topic_pl": TOPICS[key][0], "candidate_heading": ref,
                        "heading_line": ref_line, "match_line": matched_line, "text_path": text_info["path"], "source_url": item["source_url"],
                        "review_status": "automatyczny trop, bez weryfikacji znaczenia i numeracji"})
                row.update(screening="wyszukiwanie tematyczne, bez pełnej oceny eksperckiej", topics="; ".join(TOPICS[key][0] for key in TOPICS if detected[key]))
            else:
                row["screening"] = "kontrola integralności i struktury; brak wyszukiwania semantycznego w tym języku"
        rows.append(row)
    with (OUT / "pokrycie.csv").open("w", encoding="utf-8-sig", newline="") as stream:
        writer = csv.DictWriter(stream, list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    with (OUT / "tropy.csv").open("w", encoding="utf-8-sig", newline="") as stream:
        writer = csv.DictWriter(stream, list(candidates[0]))
        writer.writeheader()
        writer.writerows(candidates)
    write_json(OUT / "screening-summary.json", {
        "catalog_sha256": hashlib.sha256((ROOT / "catalog.jsonl").read_bytes()).hexdigest(),
        "catalog_records": len(records), "downloaded_records": sum(r["has_source_file"] for r in rows), "text_records": sum(r["has_text"] for r in rows),
        "unique_text_hashes": len(hashes), "keyword_languages": sorted(SCREEN_LANGUAGES),
        "keyword_screened_records": sum(r["has_text"] and r["language"] in SCREEN_LANGUAGES for r in rows),
        "structure_only_records": sum(r["has_text"] and r["language"] not in SCREEN_LANGUAGES for r in rows),
        "candidates": len(candidates), "unreviewed_candidates": True,
    })
    print(json.dumps(json.loads((OUT / "screening-summary.json").read_text()), ensure_ascii=False), flush=True)


def probe(document_id, pattern, context):
    items = [x for x in catalog() if (x["id"] == document_id or (x["country_code"] == document_id and x["language"] in ("en", "fr", "pl"))) and x.get("text")]
    regex = re.compile(pattern, re.I | re.M)
    for item in items:
        lines = (ROOT / item["text"]["path"]).read_text().splitlines()
        matches = [i for i, line in enumerate(lines) if regex.search(line)]
        if matches:
            print("\nDOC", item["id"], "|", item["title"], "|", item["source_url"])
            found = headings(lines)
            for i in matches[:8]:
                print("HEADING", locate_heading(found, i + 1))
                for n in range(max(0, i - context), min(len(lines), i + context + 1)):
                    print(f"{n+1}: {lines[n]}")


def selections():
    with (OUT / "selections.tsv").open(encoding="utf-8") as stream:
        return list(csv.DictReader(stream, delimiter="\t"))


def normalize_selected():
    records = {r["id"]: r for r in catalog()}
    directory = OUT / "normalized"
    directory.mkdir(exist_ok=True)
    result = {}
    for document_id in dict.fromkeys(s["document_id"] for s in selections()):
        item = records[document_id]
        if item["provider"] != "constitute":
            continue
        asset = next((a for a in item.get("assets", []) if a["format"] == "html"), None)
        if not asset:
            continue
        soup = BeautifulSoup((ROOT / asset["path"]).read_bytes(), "lxml")
        copy = soup.select_one(".constitution-content__copy")
        if copy is None:
            raise ValueError("Constitute full text container missing: " + document_id)
        for node in copy.select("script,style,.section-topic"):
            node.decompose()
        lines, hs, seen_headings = [], [], set()
        for node in copy.strings:
            value = node.strip()
            if not value:
                continue
            heading = node.find_parent(["h1", "h2", "h3", "h4", "h5", "h6"])
            if heading is not None:
                if id(heading) in seen_headings:
                    continue
                seen_headings.add(id(heading))
                value = heading.get_text(" ", strip=True)
            lines.append(value)
            if heading is not None:
                parent = heading.find_parent(id=True)
                hs.append({"line": len(lines), "heading": value, "anchor": parent.get("id") if parent else None})
        path = directory / (document_id.replace(":", "-") + ".txt")
        text = "\n".join(lines) + "\n"
        path.write_text(text, encoding="utf-8")
        result[document_id] = {"path": str(path.relative_to(ROOT)), "sha256": hashlib.sha256(text.encode()).hexdigest(),
            "source_html_path": asset["path"], "source_html_sha256": asset["sha256"], "source_url": asset["url"], "headings": hs,
            "transformation": "Server-rendered constitutional text only; removed topic annotations; one paragraph per line. Archive originals unchanged."}
    write_json(OUT / "normalized-sources.json", result)
    print("Normalized", len(result), "selected source editions from original HTML", flush=True)


def evidence(seed, records):
    item = records[seed["document_id"]]
    normalized_sources = json.loads((OUT / "normalized-sources.json").read_text()) if (OUT / "normalized-sources.json").exists() else {}
    selected_source = normalized_sources.get(item["id"], item["text"])
    lines = (ROOT / selected_source["path"]).read_text(encoding="utf-8").splitlines()
    searchable_lines = [" " * len(line) if ". . ." in line or re.search(r"\.{4,}", line) else line for line in lines]
    full = "\n".join(searchable_lines)
    number_match = re.search(r"(?:art[.]|sekcja|poprawka)\s+([0-9]+[a-zA-Z]*|[IVX]+|U)\b", seed["provision"], re.I)
    starts = []
    if number_match:
        number = number_match.group(1)
        article_pattern = re.compile(r"^\s*(?:(?:Article|Art[.]?|Amendment)\s+" + re.escape(number) + r"\b|" + re.escape(number) + r"(?:[.]\s*|\s*$))", re.I)
        if number == "1":
            article_pattern = re.compile(r"^\s*(?:(?:Article|Art[.]?)\s+(?:1|premier|premi.er)\b|1[.]\s+[A-Z])", re.I)
        starts = [i for i, line in enumerate(searchable_lines) if article_pattern.search(line)]
    needle = re.compile(seed["pattern"].replace(" ", r"\s+"), re.I)
    sections = []
    for start in starts:
        end = next((i for i in range(start + 1, len(lines)) if re.match(r"^\s*(?:Article|Art[.]?)\s+(?:\d|[IVX]+\b)", lines[i], re.I)), min(start + 150, len(lines)))
        block = "\n".join(searchable_lines[start:end])
        if needle.search(block):
            sections.append((start, end, block))
    if sections:
        start, end, block = sections[0]
        match = needle.search(block)
        offset = len("\n".join(lines[:start])) + (1 if start else 0)
        reference_matched = True
    else:
        match = needle.search(full)
        start, end, block, offset = 0, len(lines), full, 0
        reference_matched = False
    if match is None:
        return {"found": False, "reference_matched": False, "id": item["id"], "title": seed["title"], "provision": seed["provision"]}
    absolute = offset + match.start()
    line_number = full.count("\n", 0, absolute) + 1
    found = headings(lines)
    previous_headings = [(n, h) for n, h in found if n <= line_number][-4:]
    source_url = selected_source.get("source_url", item["source_url"])
    if item["id"] in normalized_sources:
        anchor_candidates = [h for h in selected_source["headings"] if h["line"] <= line_number and h.get("anchor")]
        if anchor_candidates:
            source_url += "#" + anchor_candidates[-1]["anchor"]
    left = max(0, match.start() - 400)
    right = min(len(block), match.end() + 1800)
    return {"found": True, "reference_matched": reference_matched, "id": item["id"], "title": seed["title"], "provision": seed["provision"],
        "line": line_number, "headings": previous_headings, "context": re.sub(r"\s+", " ", block[left:right]).strip(), "text_path": selected_source["path"],
        "source_url": source_url, "sha256": selected_source["sha256"], "start_line": start + 1,
        "original_source_html": selected_source.get("source_html_path"), "original_source_html_sha256": selected_source.get("source_html_sha256")}


def review(start, count):
    records = {r["id"]: r for r in catalog()}
    seeds = selections()
    for index in range(start - 1, min(len(seeds), start - 1 + count)):
        data = evidence(seeds[index], records)
        print(json.dumps({"number": index + 1, **data}, ensure_ascii=False))


HISTORICAL_DOCUMENTS = {
    "mjp:fr:ht1805", "constitute:en:Japan_1889", "constitute:en:Bolivia_1826",
    "mjp:fr:france-co1793", "mjp:fr:france-co1795", "mjp:fr:france-co1804", "mjp:fr:france-co1848",
    "mjp:fr:de1919", "mjp:fr:de1933", "mjp:fr:su1936", "constitute:en:Russia_1918", "constitute:en:Poland_1791",
    "mjp:fr:ht1964", "mjp:fr:ht1971",
}


def selected_entries():
    records = {r["id"]: r for r in catalog()}
    with (OUT / "editorial.tsv").open(encoding="utf-8") as stream:
        notes = {int(row["number"]): row for row in csv.DictReader(stream, delimiter="\t")}
    entries = []
    for number, seed in enumerate(selections(), 1):
        if number not in notes:
            raise ValueError(f"Missing editorial assessment for selection {number}")
        item = records[seed["document_id"]]
        proof = evidence(seed, records)
        if not proof["found"]:
            raise ValueError(f"Source locator not found for selection {number}: {seed['title']}")
        source_text = ROOT / proof["text_path"]
        if hashlib.sha256(source_text.read_bytes()).hexdigest() != proof["sha256"]:
            raise ValueError("Source hash mismatch for " + str(source_text))
        tags = seed["categories"].split(",")
        if not set(tags) <= CATEGORIES.keys():
            raise ValueError("Unrecognized editorial category")
        status = "projekt" if item["status"] == "draft" else ("historyczny" if item["id"] in HISTORICAL_DOCUMENTS else "wydanie z archiwum")
        if number == 101:
            status = "historyczny fragment później zmienionego tekstu"
        country_pl = Locale.parse("pl").territories.get(item["country_code"], item["country"])
        entries.append({"id": f"A{number:03}", "number": number, "country_code": item["country_code"], "country": country_pl,
            "document_id": item["id"], "document_title": item["title"], "source_language": item["language"], "period": status,
            "source_status": item["status"], "title": seed["title"], "provision": seed["provision"], "categories": tags,
            "meaning": notes[number]["meaning"], "why": notes[number]["why"], "caveat": notes[number]["caveat"],
            "source_url": proof["source_url"], "source_text_path": proof["text_path"], "source_line": proof["line"],
            "source_sha256": proof["sha256"], "original_source_html": proof.get("original_source_html"),
            "original_source_html_sha256": proof.get("original_source_html_sha256"),
            "archive_assets": [{"path": a["path"], "format": a["format"], "sha256": a["sha256"]} for a in item.get("assets", [])],
            "article_locator_automatched": proof["reference_matched"], "review_scope": "Parafraza i analiza konkretnego przepisu w wersji archiwalnej; nie audyt całego orzecznictwa ani aktualnego obowiązywania."})
    if len(notes) != len(entries):
        raise ValueError("Editorial rows and selections differ in count")
    return entries


def local_link(path, line=None):
    return str(ROOT / path) + (":" + str(line) if line else "")


def md_report(entries, screening):
    normalized_count = len(json.loads((OUT / "normalized-sources.json").read_text()))
    countries = len({e["country_code"] for e in entries})
    editions = len({e["document_id"] for e in entries})
    categories = Counter(tag for e in entries for tag in e["categories"])
    lines = ["# Atlas osobliwych i kluczowych zapisów konstytucyjnych", "", f"{len(entries)} opisów z {editions} wersji dokumentów i {countries} państw lub dawnych państw. Opracowanie po polsku, na podstawie lokalnego archiwum.", "",
        "## Najważniejsze ustalenia", "",
        "- Sprawność państwa i siła jego przywódcy to różne rzeczy. Rozdzielono je na dwie kategorie; sam przepis nie jest dowodem wzrostu potęgi.",
        "- Najdalej idące ryzyka to brak skutecznej kontroli, obejście konstytucji, samoutrwalanie urzędu i wykluczenie części ludzi ze wspólnoty politycznej.",
        "- Nietypowość bywa konstruktywna: inicjatywa obywatelska, szybka ochrona sądowa, ochrona zasobów i mechanizm wyboru następcy rządu mogą zwiększać zdolność wspólnego działania.",
        "- Wyjątki i przepisy przejściowe potrafią odwrócić sens pierwszego wrażenia. Szczególnie czytelne przykłady to Palau, Rwanda, Rosja i monarchia Liechtensteinu.", "",
        "## Jak czytać wynik", "",
        "Każda pozycja podaje konkretny przepis, polską parafrazę, ocenę znaczenia, istotne zastrzeżenie oraz odsyłacze do internetowego źródła i jego lokalnej kopii. Numery A001 itd. są identyfikatorami, nie punktami ani obiektywnym rankingiem. Kategorie mogą się nakładać.", "",
        "Przez niebezpieczne rozumiem ryzyka dla praw, rozliczalności władzy lub odporności ustroju. Przez dziwne rozumiem zaskakujące na tle typowych rozwiązań konstytucyjnych; nie jest to ocena wartości kultury. Kluczowe dla ustroju oznacza wagę wybranego przepisu w danym modelu, nie dowiedziony wybór jednego najważniejszego artykułu w każdym dokumencie.", "",
        "Wszystkie opisy odnoszą się do wskazanego wydania z archiwum. Nie potwierdzono aktualnego obowiązywania każdego przepisu. Historyczny oznacza tekst lub fragment historyczny, a projekt nie jest przedstawiany jako uchwalone prawo. Nie przenoszę na dzisiejsze państwa zakazów z dawnych konstytucji.", "",
        "## Pokrycie całej kolekcji", "",
        f"- Katalog: {screening['catalog_records']} pozycji, w tym {screening['downloaded_records']} z pobranymi plikami.",
        f"- Sprawdzono integralność i strukturę {screening['text_records']} tekstów, odpowiadających {screening['unique_text_hashes']} różnym sumom tekstu. Różna suma nie oznacza odrębnej konstytucji.",
        f"- Wyszukiwanie słów i wzorców tematycznych objęło {screening['keyword_screened_records']} pozycji w siedmiu językach: angielskim, francuskim, polskim, hiszpańskim, niemieckim, włoskim i portugalskim.",
        f"- Dla {screening['structure_only_records']} tekstów w pozostałych językach wykonano kontrolę techniczną i strukturalną, bez porównywalnego przeglądu znaczenia. Brak trafienia nie oznacza braku ciekawego zapisu.",
        f"- Szczegółowo opisany wybór to {len(entries)} przepisów z {editions} wersji dokumentów. Nie jest to pełna recenzja każdego z {screening['downloaded_records']} pobranych rekordów ani wszystkich 101 języków.",
        f"- Wyszukiwanie utworzyło {screening['candidates']} tropów do dalszej lektury. Nie są one automatycznie uznane za ważne ani prawidłowo ponumerowane przepisy.", "",
        "[Pełny rejestr pokrycia](pokrycie.csv) · [Automatyczne tropy do lektury](tropy.csv) · [Wybrane zapisy CSV](zapisy.csv) · [Dane i źródła JSON](zapisy.json) · [Wersja interaktywna](ATLAS.html)", "",
        "## Dziewięć kategorii", "", "| Kategoria | Pozycje |", "|---|---:|"]
    for key, label in CATEGORIES.items():
        lines.append(f"| [{label}](#kategoria-{key}) | {categories[key]} |")
    lines.extend(["", "## Spis wybranych zapisów", "", "| ID | Państwo lub porządek | Przepis | Temat |", "|---|---|---|---|"])
    for e in entries:
        lines.append(f"| [{e['id']}](#{e['id'].lower()}) | {e['country']} | {e['provision']} | {e['title']} |")
    lines.extend(["", "## Analizy zapisów", ""])
    for e in entries:
        lines.extend([f"<a id=\"{e['id'].lower()}\"></a>", f"### {e['id']}. {e['title']}", "",
            f"**{e['country']} · {e['provision']} · {e['period']}**", "",
            f"Dokument: {e['document_title']}. Język źródła: `{e['source_language']}`. Kategorie: {', '.join(CATEGORIES[c] for c in e['categories'])}.", "",
            f"**Sens zapisu (parafraza):** {e['meaning']}", "", f"**Znaczenie i ocena:** {e['why']}", "", f"**Kontekst lub ograniczenie:** {e['caveat']}", "",
            f"**Źródła:** [wydawca, wskazany przepis]({e['source_url']}) · [tekst lokalny, wiersz {e['source_line']}]({local_link(e['source_text_path'],e['source_line'])})"])
        links = [f"[{a['format'].upper()} w archiwum]({local_link(a['path'])})" for a in e["archive_assets"]]
        lines.extend([" · ".join(links), "", f"Identyfikator archiwum: `{e['document_id']}`. SHA-256 odczytanego tekstu: `{e['source_sha256']}`.", ""])
    lines.extend(["## Zestawienia według kategorii", ""])
    for key, label in CATEGORIES.items():
        lines.extend([f"<a id=\"kategoria-{key}\"></a>", f"### {label}", ""])
        lines.extend(f"- [{e['id']}. {e['title']}](#{e['id'].lower()}) ({e['country']}, {e['provision']})." for e in entries if key in e["categories"])
        lines.append("")
    lines.extend(["## Co może budować potencjał państwa", "",
        "To hipotezy o mechanizmach, nie ustalona empirycznie lista przyczyn bogactwa czy przewagi militarnej. Każdy mechanizm wymaga instytucji wykonawczych, zasobów i legitymizacji.", "",
        "| Mechanizm | Przykłady | Co może podważyć oczekiwaną korzyść |", "|---|---|---|",
        "| Ciągłość podejmowania decyzji | Niemcy, konstruktywne wotum nieufności; Polska 1791, ograniczenie weta | Stabilny, ale nieskuteczny rząd; brak rzeczywistej reprezentacji |",
        "| Wiarygodność finansowa | Polska, limit długu; Singapur, ochrona wcześniejszych rezerw | Ukrywanie zobowiązań, obchodzenie definicji długu lub zbyt sztywna reakcja na kryzys |",
        "| Wiedza i innowacje | USA, czasowa ochrona wynalazców; Korea Południowa, nauka i zasoby ludzkie | Monopole hamujące konkurencję, brak finansowania i swobody badań |",
        "| Korekta błędów i rozliczalność | Kolumbia, tutela; RPA, instytucje kontroli i dostęp do informacji | Brak niezależności organów, przewlekłość, selektywna egzekucja |",
        "| Zachowanie zasobów i kosztów międzypokoleniowych | Bhutan, lasy; Brazylia, przyszłe pokolenia; Islandia, projekt własności zasobów | Symboliczne deklaracje, brak kontroli wykonania albo kosztowne nieelastyczne zakazy |",
        "| Legitymizacja i pokojowe rozwiązywanie sporów | Szwajcaria, narzędzia obywatelskie; Kostaryka, cywilna kontrola bezpieczeństwa | Paraliż decyzyjny, marginalizacja mniejszości lub niedopasowanie do zagrożeń zewnętrznych |", "",
        "## Kontrola jakości i granice wnioskowania", "",
        "| Problem | Waga dla tej analizy | Zastosowane działanie lub wymagane uzupełnienie |", "|---|---|---|",
        f"| Błędny odczyt PDF albo numer przepisu | critical | Dla {normalized_count} wybranych wersji Constitute wykorzystano także oryginalny HTML, usunięto etykiety tematów i zachowano źródłowe sumy kontrolne. Zidentyfikowano m.in. błędny odczyt PDF Hondurasu. |",
        "| Pominięcie wyjątku albo przepisu przejściowego | critical | Wskazano wyjątki m.in. dla Palau, Mikronezji, Brunei, Rwandy i Rosji; poprawiono numery przepisów Brunei. |",
        "| Uznanie dawnej normy lub projektu za dzisiejsze prawo | major | Każdy wpis podaje wydanie i status. Przed wykorzystaniem prawnym potrzebne jest sprawdzenie aktualnego tekstu urzędowego i orzecznictwa. |",
        "| Ograniczenie przeglądu semantycznego do części języków | major | Osobny rejestr ujawnia pokrycie. Następnym rozszerzeniem powinien być przegląd pozostałych języków i tekstów bez warstwy tekstowej. |",
        "| Mylenie wpływu przepisu z rzeczywistą potęgą | major | Rozdzielono potencjał państwa od siły władcy; mechanizmy opisano jako hipotezy, bez pozornie dokładnych ocen liczbowych. |", "",
        "## Metoda i odtwarzalność", "",
        "Podstawą jest niezmieniona kolekcja lokalna i jej katalog. Program sprawdza sumy tekstów, rozpoznaje nagłówki oraz wyszukuje wielojęzyczne wzorce. Tropów automatycznych nie traktuje się jako ustaleń prawnych. Wybrane wpisy mają osobne parafrazy i komentarze sprawdzone na konkretnych fragmentach źródeł. Kopie robocze z HTML są w normalized/, a normalized-sources.json łączy je z oryginałami. W tekstach historycznych i konsolidacjach MJP trzeba uwzględniać także przypisy oraz oznaczenia zmian i wykreśleń w oryginalnym HTML. Nie tłumaczono automatycznie całych konstytucji, nie dopisywano nieznanego orzecznictwa i nie przeprowadzano niezależnego audytu prawa obowiązującego na dziś.", "",
        "Odtworzenie: `python3 analysis/atlas.py normalize`, `python3 analysis/atlas.py screen`, następnie `python3 analysis/atlas.py build`. Rejestry, dane redakcyjne i raport są zapisane oddzielnie. Sumy kontrolne i walidacja wyników: validation.json.", ""])
    (OUT / "ATLAS.md").write_text("\n".join(lines), encoding="utf-8")


def html_report(entries, screening):
    esc = html.escape
    country_names = {e["country_code"]: e["country"] for e in entries}
    cards = []
    for e in entries:
        tags = "".join(f'<span class="tag">{esc(CATEGORIES[c])}</span>' for c in e["categories"])
        local = str(Path(e["source_text_path"]).relative_to("analysis")) if e["source_text_path"].startswith("analysis/") else "../" + e["source_text_path"]
        assets = " · ".join(f'<a href="../{esc(a["path"],quote=True)}">{esc(a["format"].upper())}</a>' for a in e["archive_assets"])
        cards.append(f'''<article class="card" id="{e['id'].lower()}" data-country="{esc(e['country_code'])}" data-period="{esc(e['period'])}" data-categories="{','.join(e['categories'])}" data-number="{e['number']}">
<div class="eyebrow">{e['id']} · {esc(e['country'])} · {esc(e['period'])}</div><h2>{esc(e['title'])}</h2>
<p class="reference">{esc(e['provision'])} | {esc(e['document_title'])}</p><div class="tags">{tags}</div>
<h3>Sens zapisu <small>parafraza</small></h3><p>{esc(e['meaning'])}</p><h3>Znaczenie i ocena</h3><p>{esc(e['why'])}</p>
<div class="context"><h3>Kontekst lub ograniczenie</h3><p>{esc(e['caveat'])}</p></div>
<div class="sources"><a href="{esc(e['source_url'],quote=True)}" target="_blank" rel="noopener noreferrer">Źródło internetowe ↗</a> · <a href="{esc(local,quote=True)}">Tekst lokalny, w. {e['source_line']}</a> · {assets}</div>
<details class="provenance"><summary>Wersja i pochodzenie</summary><p>Język źródła: {esc(e['source_language'])}. Status źródłowy: {esc(e['source_status'])}. Aktualne obowiązywanie nie zostało potwierdzone.</p><code>{esc(e['document_id'])}</code><p>SHA-256 odczytanego tekstu:</p><code>{e['source_sha256']}</code></details></article>''')
    category_options = "".join(f'<option value="{key}">{esc(label)}</option>' for key, label in CATEGORIES.items())
    country_options = "".join(f'<option value="{code}">{esc(name)}</option>' for code, name in sorted(country_names.items(), key=lambda pair:pair[1]))
    template = '''<!doctype html>
<html lang="pl"><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1"><title>Atlas zapisów konstytucyjnych</title>
<style>
:root{--ink:#172a39;--paper:#f5f2e9;--line:#d8ddd9;--accent:#006858;--muted:#53636a}*{box-sizing:border-box}body{margin:0;background:var(--paper);color:var(--ink);font:16px/1.65 system-ui,sans-serif}a{color:var(--accent);text-underline-offset:3px}a:focus-visible,button:focus-visible,input:focus-visible,select:focus-visible,summary:focus-visible{outline:3px solid #c25d22;outline-offset:3px}header{background:#142d3b;color:#fff;padding:64px max(24px,calc((100vw - 1180px)/2)) 42px}header p{max-width:820px;color:#dce5e5}.kicker{text-transform:uppercase;letter-spacing:.17em;color:#9fd0ba;font-size:12px;font-weight:750}h1{font:600 clamp(2rem,4.5vw,3.6rem)/1.1 Georgia,serif;max-width:900px;margin:16px 0 24px}.stats{display:flex;gap:36px;flex-wrap:wrap;margin:28px 0}.stats b{display:block;font-size:28px}.stats span{font-size:13px;color:#c6d9d9}.wrap{max-width:1230px;margin:auto;padding:28px 24px 64px}.scope{background:#fff;border-left:4px solid #bd772f;padding:16px 22px;margin:0 0 24px}.scope p{margin:5px 0}.downloads{display:flex;flex-wrap:wrap;gap:18px;margin:18px 0}details.method{border:1px solid var(--line);padding:12px 18px;background:#fff;margin-bottom:20px}summary{cursor:pointer;font-weight:650}.filters{display:grid;grid-template-columns:2fr 1.5fr 1fr 1fr auto;gap:12px;padding:18px;background:#e5ebe5;border:1px solid #ccd8cf;border-radius:8px}label{font-size:12px;font-weight:750;display:block}input,select,button{font:inherit;padding:10px 12px;border:1px solid #aebcb5;border-radius:4px;background:#fff;width:100%;color:var(--ink)}button{align-self:end;background:var(--accent);color:#fff;cursor:pointer}.results{display:flex;justify-content:space-between;gap:20px;align-items:center;margin:22px 0}.results span{font-size:14px}.grid{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:22px}.card{background:#fff;border:1px solid var(--line);border-top:4px solid var(--accent);padding:28px;scroll-margin-top:20px}.card h2{font:650 26px/1.25 Georgia,serif;margin:12px 0}.eyebrow{font-size:11px;font-weight:800;letter-spacing:.07em;text-transform:uppercase;color:var(--accent)}.reference{font-size:13px;color:var(--muted)}.tags{display:flex;gap:6px;flex-wrap:wrap;margin:15px 0}.tag{font-size:10px;border:1px solid #c8d8cf;padding:3px 7px;border-radius:3px;color:#26513e;background:#f1f6f0}.card h3{font-size:12px;text-transform:uppercase;letter-spacing:.05em;margin:22px 0 7px}.card h3 small{font-weight:400;color:var(--muted)}.card p{margin:5px 0 14px}.context{background:#f7f3e8;padding:1px 14px 8px;border-left:2px solid #c28c4b;margin:18px 0}.sources{font-size:12px;padding-top:13px;border-top:1px solid var(--line);overflow-wrap:anywhere}.provenance{font-size:12px;color:var(--muted);margin-top:16px}.provenance code{font-size:10px;overflow-wrap:anywhere}footer{font-size:13px;color:var(--muted);padding:35px 0}.empty{padding:40px;text-align:center;background:#fff;border:1px solid var(--line)}[hidden]{display:none!important}@media(max-width:950px){.filters{grid-template-columns:1fr 1fr}.filters label:first-child{grid-column:1/-1}}@media(max-width:700px){.grid{grid-template-columns:1fr}.card{padding:21px}.stats{gap:20px}.filters{grid-template-columns:1fr}.filters label:first-child{grid-column:auto}header{padding-top:38px}}@media print{body{background:#fff;font-size:10pt}header{background:#fff;color:#000;padding:0 0 20px}header p,.stats span{color:#333}.filters,.results button,.downloads{display:none}.wrap{padding:0}.grid{display:block}.card{break-inside:avoid;border:1px solid #aaa;margin:16px 0;padding:15px}.card h2{font-size:18pt}.scope{border-color:#333}.provenance{display:none}.card[hidden]{display:none!important}a{color:#222}}
</style>
<header><div class="kicker">Archiwum konstytucji świata · atlas porównawczy</div><h1>Jak konstytucje budują, ograniczają i oddają władzę</h1><p>Oryginalne normy, ważne mechanizmy i trudne wyjątki. Każdy opis łączy przepis, parafrazę, ocenę oraz źródła. Numery są identyfikatorami, a nie obiektywną punktacją.</p><div class="stats"><div><b>@@COUNT@@</b><span>opisanych zapisów</span></div><div><b>@@EDITIONS@@</b><span>wersji dokumentów</span></div><div><b>@@COUNTRIES@@</b><span>państw i dawnych państw</span></div><div><b>9</b><span>kategorii oceny</span></div></div></header>
<main class="wrap"><nav class="downloads" aria-label="Widoki kolekcji"><a href="rp/index.html" style="font-weight:750">Konstytucja RP na tle świata →</a><a href="tematy/index.html" style="font-weight:750">331 tematów z wariantami przepisów →</a><a href="mapa/index.html" style="font-weight:750">Mapa: 331 rozwiązań w 188 konstytucjach →</a><a href="panstwa/index.html" style="font-weight:750">Państwa, porównanie i wyszukiwarka pełnotekstowa →</a><a href="wizualizacje/index.html" style="font-weight:750">Pracownia wizualna: osiem analiz →</a><a href="polska/index.html" style="font-weight:750">Dla Polski: 24 propozycje do nowej konstytucji →</a></nav><div class="scope"><p><strong>Potencjał państwa i siła przywódcy są oceniane osobno.</strong> Opisujemy mechanizmy i możliwe skutki, nie dowiedziony wpływ na bogactwo czy siłę militarną.</p><p>Analiza dotyczy wskazanych wydań z archiwum. Projekty i teksty historyczne są oznaczone. Nie potwierdzono aktualnego obowiązywania wszystkich przepisów.</p></div>
<div class="downloads"><a href="ATLAS.md">Raport Markdown</a><a href="zapisy.csv">Wybrane zapisy CSV</a><a href="zapisy.json">Dane i źródła JSON</a><a href="pokrycie.csv">Pokrycie całego archiwum</a><a href="tropy.csv">Automatyczne tropy</a></div>
<details class="method"><summary>Co obejmuje analiza, a czego nie obejmuje</summary><p>Katalog zawiera @@CATALOG@@ pozycji; pobrano pliki dla @@DOWNLOADED@@. Sprawdzono integralność i strukturę @@TEXTS@@ tekstów. Wyszukiwanie słów i wzorców w siedmiu językach objęło @@SCREENED@@ pozycji; pozostałe @@STRUCTURE@@ tekstów otrzymało kontrolę techniczną i strukturalną. Nie jest to pełna analiza znaczenia we wszystkich 101 językach.</p><p>Wybrano @@COUNT@@ zapisów z @@EDITIONS@@ wersji dokumentów i przygotowano osobne parafrazy oraz komentarze sprawdzone na źródłach. Nie ustalono jednego najważniejszego artykułu w każdym dokumencie. Tropy automatyczne są materiałem do dalszej lektury, a nie zatwierdzonymi ustaleniami.</p><p>Dla @@NORMALIZED@@ wybranych wersji Constitute wykorzystano także zapisany HTML, aby uniknąć błędów odczytu PDF. Oryginałów archiwum nie zmieniono. Pełna metoda, mechanizmy budowy potencjału oraz ograniczenia są w raporcie Markdown.</p></details>
<div class="filters"><label>Szukaj<input id="query" type="search" placeholder="np. przyroda, kadencja, Polska, art. 16"></label><label>Kategoria<select id="category"><option value="">Wszystkie kategorie</option>@@CATEGORY_OPTIONS@@</select></label><label>Państwo<select id="country"><option value="">Wszystkie państwa</option>@@COUNTRY_OPTIONS@@</select></label><label>Rodzaj tekstu<select id="period"><option value="">Wszystkie</option><option value="archive">Wydania z archiwum</option><option value="history">Historyczne</option><option value="draft">Projekty</option></select></label><button id="reset" type="button">Wyczyść</button></div>
<div class="results"><span id="count" aria-live="polite">Wszystkie pozycje</span><button id="print" type="button" style="width:auto">Drukuj / zapisz PDF</button></div><div id="empty" class="empty" hidden>Brak pasujących pozycji. Zmień filtry lub wyszukiwanie.</div><section class="grid" id="cards" aria-label="Wybrane zapisy konstytucyjne">@@CARDS@@</section><footer>Opracowanie na podstawie lokalnego archiwum. Klasyfikacja jest oceną redakcyjną; teksty i ich status należy odróżniać od skuteczności instytucji w praktyce.</footer></main>
<script>
const cards=[...document.querySelectorAll('.card')];
const norm=s=>s.toLocaleLowerCase('pl').replaceAll('ł','l').normalize('NFD').replace(/\\p{M}/gu,'');
const input=document.getElementById('query'),cat=document.getElementById('category'),country=document.getElementById('country'),period=document.getElementById('period');
for(const card of cards)card.searchText=norm(card.textContent);
function filter(){const q=norm(input.value.trim()),words=q.split(/\\s+/).filter(Boolean);let shown=0;for(const card of cards){const p=card.dataset.period;const type=p==='projekt'?'draft':p.startsWith('historyczny')?'history':'archive';const ok=words.every(w=>card.searchText.includes(w))&&(!cat.value||card.dataset.categories.split(',').includes(cat.value))&&(!country.value||country.value===card.dataset.country)&&(!period.value||period.value===type);card.hidden=!ok;if(ok)shown++;}document.getElementById('count').textContent=`Pokazano ${shown} z ${cards.length} opisanych zapisów`;document.getElementById('empty').hidden=shown>0;}
input.addEventListener('input',filter);for(const select of [cat,country,period])select.addEventListener('change',filter);document.getElementById('reset').addEventListener('click',()=>{input.value='';cat.value='';country.value='';period.value='';filter();});document.getElementById('print').addEventListener('click',()=>window.print());filter();
</script></html>'''
    replacements = {"@@COUNT@@": str(len(entries)), "@@EDITIONS@@": str(len({e["document_id"] for e in entries})), "@@COUNTRIES@@":str(len(country_names)),
        "@@CATALOG@@":str(screening["catalog_records"]),"@@DOWNLOADED@@":str(screening["downloaded_records"]),"@@TEXTS@@":str(screening["text_records"]),
        "@@SCREENED@@":str(screening["keyword_screened_records"]),"@@STRUCTURE@@":str(screening["structure_only_records"]),
        "@@NORMALIZED@@":str(len(json.loads((OUT / "normalized-sources.json").read_text()))),
        "@@CATEGORY_OPTIONS@@":category_options,"@@COUNTRY_OPTIONS@@":country_options,"@@CARDS@@":"\n".join(cards)}
    for key, value in replacements.items():
        template = template.replace(key, value)
    (OUT / "ATLAS.html").write_text(template, encoding="utf-8")


def build():
    entries = selected_entries()
    screening = json.loads((OUT / "screening-summary.json").read_text())
    current_hash = hashlib.sha256((ROOT / "catalog.jsonl").read_bytes()).hexdigest()
    if screening["catalog_sha256"] != current_hash:
        raise ValueError("Archive catalog changed since corpus screening")
    write_json(OUT / "zapisy.json", entries)
    fields = ["id","country","country_code","document_title","source_language","period","provision","title","categories","meaning","why","caveat","source_url","source_text_path","source_line","source_sha256","document_id"]
    with (OUT / "zapisy.csv").open("w", encoding="utf-8-sig", newline="") as stream:
        writer = csv.DictWriter(stream, fields)
        writer.writeheader()
        writer.writerows({key:("; ".join(e[key]) if key=="categories" else e[key]) for key in fields} for e in entries)
    md_report(entries, screening)
    html_report(entries, screening)
    with (OUT / "pokrycie.csv").open(encoding="utf-8-sig") as stream:
        coverage_rows = list(csv.DictReader(stream))
    for row in coverage_rows:
        selected = [entry for entry in entries if entry["document_id"] == row["id"]]
        row["selected_clause_ids"] = "; ".join(entry["id"] for entry in selected)
        row["editorial_scope"] = "opis wybranych przepisów; bez pełnej recenzji dokumentu" if selected else "brak szczegółowej oceny redakcyjnej"
    with (OUT / "pokrycie.csv").open("w", encoding="utf-8-sig", newline="") as stream:
        writer = csv.DictWriter(stream, list(coverage_rows[0]))
        writer.writeheader()
        writer.writerows(coverage_rows)
    result = {"generated_at":datetime.now(timezone.utc).isoformat(),"curated_clauses":len(entries),"source_editions":len({e["document_id"] for e in entries}),
        "jurisdictions":len({e["country_code"] for e in entries}),"categories":dict(Counter(tag for e in entries for tag in e["categories"])),
        "archive_catalog_sha256":current_hash,"all_source_locators_found":True,"all_selected_source_hashes_verified":True,
        "source_versions_current_validity_verified":False,"full_semantic_review_of_all_documents":False}
    write_json(OUT / "validation.json", result)
    print(json.dumps(result,ensure_ascii=False),flush=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=["screen", "probe", "review", "normalize", "build"])
    parser.add_argument("--document")
    parser.add_argument("--pattern")
    parser.add_argument("--context", type=int, default=8)
    parser.add_argument("--start", type=int, default=1)
    parser.add_argument("--count", type=int, default=20)
    args = parser.parse_args()
    if args.command == "screen":
        screen()
    elif args.command == "normalize":
        normalize_selected()
    elif args.command == "build":
        build()
    elif args.command == "probe":
        probe(args.document, args.pattern, args.context)
    else:
        review(args.start, args.count)


if __name__ == "__main__":
    main()
