#!/usr/bin/env python3
"""Discover additional public constitutional collections."""

import argparse
import concurrent.futures
import hashlib
import json
from pathlib import Path
import re
from urllib.parse import urljoin, urlparse

from bs4 import BeautifulSoup

from collect import COUNTRIES, COUNTRY_NAMES, ROOT, cached_page, country_code, get, html_text, log, merge_manifest, now, record, save_json, slug


def discover_sejm(workers):
    index = "https://biblioteka.sejm.gov.pl/konstytucje_swiata/"
    soup = BeautifulSoup(cached_page(index, "sejm"), "lxml")
    profiles = {}
    aliases = {"korea-polnocna": "KP", "korea-poludniowa": "KR", "wielka-brytania": "GB", "watykan": "VA", "wybrzeze-kosci-sloniowej": "CI", "timor-wschodni": "TL", "kongo": "CG", "demokratyczna-republika-konga": "CD", "wyspy-zielonego-przyladka": "CV", "kosowo": "XK"}
    for anchor in soup.select("a[href]"):
        url = urljoin(index, anchor["href"]).split("?")[0].split("#")[0]
        if not re.search(r"/konstytucje-swiata-[^/]+/?$", urlparse(url).path):
            continue
        name = anchor.get_text(" ", strip=True)
        stem = urlparse(url).path.strip("/").replace("konstytucje-swiata-", "")
        code = aliases.get(stem) or country_code(name) or country_code(stem)
        if code:
            profiles[url] = code
    languages = {"polsk": "pl", "angielsk": "en", "francusk": "fr", "niemieck": "de", "hiszpansk": "es", "portugalsk": "pt", "rosyjsk": "ru", "arabsk": "ar", "persk": "fa", "ukrainsk": "uk", "wlosk": "it", "chinsk": "zh", "japonsk": "ja", "koreansk": "ko", "niderlandzk": "nl", "holendersk": "nl", "szwedzk": "sv", "norwesk": "no", "finsk": "fi", "dunsk": "da", "islandzk": "is", "irlandzk": "ga", "greck": "el", "czesk": "cs", "slowack": "sk", "slowensk": "sl", "chorwack": "hr", "serbsk": "sr", "bosniack": "bs", "bulgarsk": "bg", "rumunsk": "ro", "wegiersk": "hu", "litewsk": "lt", "lotewsk": "lv", "estonsk": "et", "tureck": "tr", "hebrajsk": "he", "malta": "mt", "gruzinsk": "ka", "ormiansk": "hy", "albansk": "sq", "macedonsk": "mk", "bialorusk": "be", "indonezyjsk": "id", "malajsk": "ms", "suahili": "sw", "wietnamsk": "vi"}
    extra_languages = ROOT / "metadata/sejm-language-map.json"
    if extra_languages.exists():
        languages.update(json.loads(extra_languages.read_text()))
    records, failures, seen = {}, [], set()
    with concurrent.futures.ThreadPoolExecutor(max_workers=workers) as pool:
        futures = {pool.submit(cached_page, url, "sejm"): (url, code) for url, code in profiles.items()}
        for index_number, future in enumerate(concurrent.futures.as_completed(futures), 1):
            url, code = futures[future]
            try:
                page = BeautifulSoup(future.result(), "lxml")
                for row in page.select("tr"):
                    row_text = slug(row.get_text(" ", strip=True))
                    language = next((language for prefix, language in languages.items() if row_text.startswith(prefix)), "und")
                    for anchor in row.select("a[href]"):
                        target = urljoin(url, anchor["href"])
                        if anchor.get_text(" ", strip=True).upper() != "PDF" and not urlparse(target).path.lower().endswith(".pdf"):
                            continue
                        if target in seen:
                            continue
                        seen.add(target)
                        heading = row.find_previous(["h2", "h3"])
                        title = heading.get_text(" ", strip=True) if heading else "Konstytucja"
                        key = hashlib.sha256(target.encode()).hexdigest()[:20]
                        years = re.findall(r"\b(?:1[5-9]\d{2}|20\d{2})\b", title)
                        records[target] = record("sejm-library", key, COUNTRY_NAMES.get(code, code), title, language,
                            [{"url": target, "format": "pdf"}], country_code=code, source_url=url,
                            year_enacted=years[0] if years else None, status="source_edition_unverified",
                            language_note=row.get_text(" ", strip=True)[:200], rights="Sejm Library bibliography and linked legal texts/translations; see each original publisher.")
            except Exception as error:
                failures.append({"url": url, "error": str(error)[:300]})
            if index_number % 40 == 0 or index_number == len(profiles):
                log(f"Sejm Library {index_number}/{len(profiles)} profiles; {len(records)} public PDF links")
    merge_manifest(records.values())
    save_json(ROOT / "reports" / "sejm-discovery-failures.json", failures)
    save_json(ROOT / "metadata" / "sejm-discovery.json", {"at": now(), "profiles": len(profiles), "records": len(records), "failures": len(failures)})


def discover_mjp(workers):
    index = "https://mjp.univ-perp.fr/constit/constitintro.htm"
    soup = BeautifulSoup(cached_page(index, "mjp"), "lxml")
    special = {"and": "AD", "aut": "AT", "dan": "DK", "fin": "FI", "lux": "LU", "mon": "MC", "pb": "NL", "uk": "GB", "kos": "XK", "som": "XS", "ddr": "DD", "tch": "CS", "rau": "UAR", "veco1819": "GCO", "de-prusse1850": "PRU", "cn1932mand": "MAN", "crete": "CRE", "dantzig": "DAN", "memel": "MEM", "samos": "SAM", "ma1923": "TAN", "trieste1947": "TRI", "go": "CU"}
    names = {"XS": "Somaliland", "UAR": "United Arab Republic", "GCO": "Gran Colombia", "PRU": "Prussia", "MAN": "Manchukuo", "CRE": "Cretan State", "DAN": "Free City of Danzig", "MEM": "Memel Territory", "SAM": "Principality of Samos", "TAN": "Tangier International Zone", "TRI": "Free Territory of Trieste"}
    names.update(COUNTRY_NAMES)
    roots, prefixes = {}, {}
    for anchor in soup.select("a[href]"):
        url = urljoin(index, anchor["href"]).split("#")[0]
        path = urlparse(url).path
        if urlparse(url).hostname != "mjp.univ-perp.fr" or not path.startswith("/constit/") or not path.endswith(".htm"):
            continue
        stem = Path(path).stem.lower()
        if stem in ("constitintro", "cat"):
            continue
        code = special.get(stem) or (stem.upper() if stem.upper() in COUNTRY_NAMES else country_code(anchor.get_text(" ", strip=True)))
        if not code:
            continue
        roots[url] = code
        prefixes[stem] = code
    roots["https://mjp.univ-perp.fr/france/france.htm"] = "FR"
    roots["https://mjp.univ-perp.fr/france/france5.htm"] = "FR"
    prefixes.update({"su": "SU", "yu": "YU"})

    def classify(url):
        parsed = urlparse(url)
        if parsed.hostname != "mjp.univ-perp.fr" or parsed.query or not parsed.path.endswith((".htm", ".html")):
            return None
        stem = Path(parsed.path).stem.lower()
        if url in roots:
            return roots[url]
        if parsed.path.startswith("/constit/"):
            for prefix in sorted(prefixes, key=len, reverse=True):
                if stem.startswith(prefix) and re.match(r"^[0-9-]", stem[len(prefix):]):
                    # National constitutions and former sovereign states only.
                    if prefix == "de" and stem.startswith("de-") and not re.match(r"de-prusse(?:17|18[0-6])", stem):
                        return None
                    return prefixes[prefix]
        if parsed.path.startswith("/france/") and re.match(r"(?:co|ddh)\d{4}", stem):
            return "FR"
        if parsed.path == "/traites/1929latran.htm":
            return "VA"
        return None

    visited, pending, records, failures = set(), dict(roots), {}, []
    round_number = 0
    while pending:
        round_number += 1
        batch = dict(pending)
        pending = {}
        with concurrent.futures.ThreadPoolExecutor(max_workers=workers) as pool:
            futures = {pool.submit(cached_page, url, "mjp"): (url, code) for url, code in batch.items()}
            for future in concurrent.futures.as_completed(futures):
                url, code = futures[future]
                visited.add(url)
                try:
                    body = future.result()
                    page = BeautifulSoup(body, "lxml")
                    for anchor in page.select("a[href]"):
                        target = urljoin(url, anchor["href"]).split("#")[0]
                        target_code = classify(target)
                        if target_code and target not in visited and target not in batch:
                            pending[target] = target_code
                    text = html_text(body, "mjp")
                    legal_articles = len(re.findall(r"\b(?:Article|Art\.)\s+(?:\d|premier|unique|[IVX])", text, re.I))
                    # Country landing pages contain timelines and links, not full constitutions.
                    if legal_articles < 2 or len(text) < 1000 or (url in roots and not re.search(r"\d", Path(urlparse(url).path).stem) and legal_articles < 15):
                        continue
                    title = page.title.get_text(" ", strip=True) if page.title else Path(urlparse(url).path).stem
                    stem = Path(urlparse(url).path).stem
                    key = hashlib.sha256(url.encode()).hexdigest()[:24]
                    cached_path = f"metadata/pages/mjp/{key}.html"
                    years = re.findall(r"\b(?:1[5-9]\d{2}|20\d{2})\b", title)
                    item = record("mjp", ("france-" if "/france/" in url else "") + stem, names.get(code, code), title, "fr",
                        [{"url": url, "format": "html", "cached_path": cached_path}], country_code=code,
                        year_enacted=years[0] if years else None,
                        status="draft" if re.search(r"\bprojet\b", title, re.I) else "source_edition_unverified",
                        document_type="constitutional_text", rights="Digithèque MJP, Jean-Pierre Maury / University of Perpignan; see notices in original HTML.")
                    records[item["id"]] = item
                except Exception as error:
                    failures.append({"url": url, "error": str(error)[:300]})
        merge_manifest(records.values())
        save_json(ROOT / "reports" / "mjp-discovery-failures.json", failures)
        log(f"MJP traversal {round_number}: {len(visited)} pages; {len(records)} legal texts; {len(pending)} new pages")
    save_json(ROOT / "metadata" / "mjp-discovery.json", {"at": now(), "pages": len(visited), "records": len(records), "failures": len(failures)})


def constitution_title(title):
    return bool(re.match(r"^(?:the\s+)?(?:constitution\b|constitutional (?:law|act)\b|basic (?:law|laws)\b|fundamental (?:law|laws|statute)\b|instrument of government\b|statute of the kingdom\b|charter of (?:rights|the kingdom)\b|bill of rights\b|human rights act\b)", title.strip(), re.I))


def wipo_profile(code):
    url = "https://www.wipo.int/wipolex/en/members/profile/" + code
    body = cached_page(url, "wipo-profiles")
    soup = BeautifulSoup(body, "lxml")
    found = []
    for anchor in soup.select('a[href*="/legislation/details/"]'):
        title = anchor.get_text(" ", strip=True)
        if constitution_title(title):
            found.append((urljoin(url, anchor["href"]), code, title))
    return found


def wipo_details(entry):
    url, code, title = entry
    cache_url = url
    try:
        body = cached_page(url, "wipo-details")
    except ValueError:
        cache_url = url + "?view=full"
        body = cached_page(cache_url, "wipo-details")
    soup = BeautifulSoup(body, "lxml")
    key = urlparse(url).path.rsplit("/", 1)[-1]
    text = soup.get_text(" ", strip=True)
    # Source labels describe this edition; historical editions are never called current.
    version = re.search(r"Year of Version\s+(\d{4})", text)
    year = version.group(1) if version else None
    records, related, seen = [], [], set()
    for node in soup.select("iframe[src], a.seo-only-link[href]"):
        pdf_url = node.get("src") or node.get("href")
        parsed = urlparse(pdf_url)
        stable_url = pdf_url.split("?")[0]
        if parsed.hostname != "wipolex-res.wipo.int" or not parsed.path.lower().endswith(".pdf") or stable_url in seen:
            continue
        match = re.search(r"/laws/([^/]+)/([^/]+)/", parsed.path)
        if not match:
            continue
        # Restrict full texts to the selected law's main text, not linked amending laws.
        if node.find_parent(id=re.compile("related", re.I)):
            continue
        seen.add(stable_url)
        language = match.group(1)
        filename = Path(parsed.path).stem
        source_title = node.get("title") or node.get_text(" ", strip=True) or title
        normalized_language = {"ie": "ga", "cg": "cnr"}.get(language, language)
        item = record("wipo", key + "-" + filename, COUNTRY_NAMES.get(code, code), source_title, normalized_language,
            [{"url": stable_url, "download_url": pdf_url, "format": "pdf"}],
            country_code=code, source_url=url, year_revised=year, status="source_edition_unverified",
            edition_title=title, wipo_law_id=key, rights="WIPO Lex and underlying legal text/translation terms apply; see source page.")
        if normalized_language != language:
            item["source_language_code"] = language
        attach_wipo_html(item, soup, cache_url)
        records.append(item)
    for anchor in soup.select('a[href*="/legislation/details/"]'):
        related_title = anchor.get_text(" ", strip=True)
        if constitution_title(related_title):
            target = urljoin(url, anchor["href"])
            if target != url:
                related.append((target, code, related_title))
    return records, related


def attach_wipo_html(item, soup, cache_url):
    stable_url = next(u["url"] for u in item["urls"] if u["format"] == "pdf")
    frame = next((n for n in soup.select("iframe[src]") if n["src"].split("?")[0] == stable_url), None)
    if frame is None:
        return
    wrapper = frame.find_parent(class_="fileDetails")
    if wrapper is None:
        return
    sibling = wrapper.find_next_sibling(class_="fileDetails")
    if sibling is None or sibling.select_one(".htmlView") is None:
        return
    widget = sibling.select_one("wu-machine-translation-widget")
    if widget and widget.get("google-widget-pagelanguage") != item.get("source_language_code", item["language"]):
        return
    if len(sibling.select_one(".htmlView").get_text(strip=True)) < 500:
        return
    cache_key = hashlib.sha256(cache_url.encode()).hexdigest()[:24]
    item["html_selector"] = f'[id="{sibling["id"]}"] .htmlView'
    item["urls"] = [u for u in item["urls"] if u["format"] != "html"] + [{
        "url": item["source_url"] + "#" + sibling["id"], "format": "html", "filename": "source-page.html",
        "cached_path": f"metadata/pages/wipo-details/{cache_key}.html"}]


def discover_wipo(workers):
    failures, pending = [], {}
    # Include territories when WIPO exposes a jurisdiction profile.
    codes = [r["alpha_2"] for r in COUNTRIES]
    with concurrent.futures.ThreadPoolExecutor(max_workers=workers) as pool:
        futures = {pool.submit(wipo_profile, code): code for code in codes}
        for index, future in enumerate(concurrent.futures.as_completed(futures), 1):
            try:
                for entry in future.result():
                    pending[entry[0]] = entry
            except Exception as error:
                failures.append({"stage": "profile", "code": futures[future], "error": str(error)[:300]})
            if index % 40 == 0 or index == len(codes):
                log(f"WIPO profiles {index}/{len(codes)}; constitutional editions: {len(pending)}")
    pending.setdefault("https://www.wipo.int/wipolex/en/legislation/details/22646", ("https://www.wipo.int/wipolex/en/legislation/details/22646", "AZ", "Constitution of the Republic of Azerbaijan"))
    seen, records, round_number = set(), {}, 0
    while pending:
        round_number += 1
        batch = list(pending.values())
        pending = {}
        with concurrent.futures.ThreadPoolExecutor(max_workers=workers) as pool:
            futures = {pool.submit(wipo_details, entry): entry for entry in batch}
            for future in concurrent.futures.as_completed(futures):
                entry = futures[future]
                seen.add(entry[0])
                try:
                    new_records, related = future.result()
                    for item in new_records:
                        records[item["id"]] = item
                    for target in related:
                        if target[0] not in seen and target[0] not in {r[0] for r in batch}:
                            pending[target[0]] = target
                except Exception as error:
                    failures.append({"stage": "details", "url": entry[0], "error": str(error)[:300]})
        merge_manifest(records.values())
        save_json(ROOT / "reports" / "wipo-discovery-failures.json", failures)
        log(f"WIPO version traversal {round_number}: {len(seen)} editions visited; {len(records)} language records; {len(pending)} new editions")
    save_json(ROOT / "metadata" / "wipo-discovery.json", {"at": now(), "profile_count": len(codes), "edition_count": len(seen), "records": len(records), "failures": len(failures)})


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", choices=["wipo", "mjp", "sejm"])
    parser.add_argument("--workers", type=int, default=4)
    args = parser.parse_args()
    if args.source == "wipo":
        discover_wipo(max(1, min(args.workers, 6)))
    elif args.source == "mjp":
        discover_mjp(max(1, min(args.workers, 6)))
    elif args.source == "sejm":
        discover_sejm(max(1, min(args.workers, 6)))


if __name__ == "__main__":
    main()
