#!/usr/bin/env python3
"""Collect public constitutional documents with resumable provenance tracking."""

import argparse
import concurrent.futures
import csv
import fcntl
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import threading
import time
import unicodedata
from urllib.parse import quote, urljoin, urlparse

import requests
from babel import Locale
from bs4 import BeautifulSoup

ROOT = Path(__file__).resolve().parent
HEADERS = {"User-Agent": "ConstitutionResearchArchive/1.0 (public documents; bounded requests)", "Accept": "*/*"}
MAX_BYTES = 50 * 1024 * 1024
PRINT_LOCK = threading.Lock()
HOST_LOCK = threading.Lock()
HOST_NEXT = {}
HOST_BLOCKED = set()
HOST_EMPTY_RESPONSES = {}
LOCAL = threading.local()


def log(message):
    with PRINT_LOCK:
        print(message, flush=True)


def slug(value):
    value = str(value).translate(str.maketrans({"ł": "l", "Ł": "L", "ø": "o", "Ø": "O", "ß": "ss", "đ": "d", "Đ": "D"}))
    value = unicodedata.normalize("NFKD", value).encode("ascii", "ignore").decode()
    return re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-") or "document"


def now():
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


def save_json(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".part")
    tmp.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    tmp.replace(path)


def get(url):
    if not hasattr(LOCAL, "session"):
        LOCAL.session = requests.Session()
        LOCAL.session.headers.update(HEADERS)
    host = urlparse(url).hostname
    if host in HOST_BLOCKED:
        raise ValueError("Source paused for this run after repeated empty HTTP 202 responses")
    for attempt in range(3):
        with HOST_LOCK:
            delay = max(0, HOST_NEXT.get(host, 0) - time.monotonic())
            HOST_NEXT[host] = time.monotonic() + delay + 0.30
        time.sleep(delay)
        try:
            certificate_bundle = ROOT / "metadata" / "tls" / "bundle.pem"
            verification = str(certificate_bundle) if host == "mjp.univ-perp.fr" and certificate_bundle.exists() else True
            with LOCAL.session.get(url, timeout=(10, 35), stream=True, verify=verification) as response:
                if response.status_code in (429, 500, 502, 503, 504) and attempt < 2:
                    time.sleep(min(12, 2 ** (attempt + 1)))
                    continue
                response.raise_for_status()
                if response.status_code != 200:
                    if response.status_code == 202 and host == "wipolex-res.wipo.int":
                        with HOST_LOCK:
                            HOST_EMPTY_RESPONSES[host] = HOST_EMPTY_RESPONSES.get(host, 0) + 1
                            if HOST_EMPTY_RESPONSES[host] >= 5:
                                HOST_BLOCKED.add(host)
                    raise ValueError(f"Non-document HTTP status: {response.status_code}")
                if int(response.headers.get("Content-Length", 0)) > MAX_BYTES:
                    raise ValueError("Response exceeds 50 MiB")
                chunks, size = [], 0
                started = time.monotonic()
                for chunk in response.iter_content(65536):
                    size += len(chunk)
                    if size > MAX_BYTES or time.monotonic() - started > 75:
                        raise ValueError("Response exceeds size/time limit")
                    chunks.append(chunk)
                if not size:
                    raise ValueError("Empty response body")
                return b"".join(chunks), response.headers.get("Content-Type", ""), response.url
        except (requests.Timeout, requests.ConnectionError):
            if attempt == 2:
                raise
            time.sleep(2 ** attempt)
    raise RuntimeError("No successful response")


def cached_page(url, namespace):
    key = hashlib.sha256(url.encode()).hexdigest()[:24]
    path = ROOT / "metadata" / "pages" / namespace / (key + ".html")
    if path.exists() and path.stat().st_size > 100:
        return path.read_bytes()
    body, _, _ = get(url)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(body)
    save_json(path.with_suffix(".json"), {"url": url, "retrieved_at": now()})
    return body


COUNTRIES_PATH = ROOT / "metadata" / "iso3166-1.json"
if not COUNTRIES_PATH.exists():
    COUNTRIES_PATH = Path("/usr/share/iso-codes/json/iso_3166-1.json")
COUNTRIES = json.loads(COUNTRIES_PATH.read_text())["3166-1"]
COUNTRY_NAMES = {item["alpha_2"]: item["name"] for item in COUNTRIES}
COUNTRY_NAMES.update({"XK": "Kosovo", "SU": "Soviet Union", "YU": "Yugoslavia", "CS": "Czechoslovakia", "DD": "East Germany", "OT": "Ottoman Empire", "BAD": "Baden", "BAY": "Bavaria"})
ALIASES = {}
for item in COUNTRIES:
    for field in ("name", "official_name", "common_name", "alpha_2", "alpha_3"):
        if item.get(field):
            ALIASES[slug(item[field])] = item["alpha_2"]
for language in ("en", "pl", "fr", "de", "es", "pt", "it", "ru", "ar", "zh", "ja", "nl", "tr", "uk", "cs", "sv", "fi", "he", "fa", "id", "ro", "el"):
    for code, name in Locale.parse(language).territories.items():
        if code in COUNTRY_NAMES:
            ALIASES[slug(name)] = code
for code, aliases in {
    "BO": ["Bolivia"], "BN": ["Brunei", "Brunei Darussalam"], "CD": ["Democratic Republic of the Congo", "Congo DR", "Congo-Kinshasa", "Congo republique democratique"],
    "CG": ["Congo", "Congo Brazzaville"], "CV": ["Cape Verde"], "CZ": ["Czech Republic"], "FM": ["Micronesia Federated States of", "Micronesia"],
    "GM": ["Gambia", "Gambia The"], "IR": ["Iran", "Iran Islamic Republic of"], "KP": ["North Korea", "Korea Democratic Peoples Republic of"],
    "KR": ["South Korea", "Korea Republic of"], "LA": ["Laos", "Lao Peoples Democratic Republic"], "MD": ["Moldova", "Moldova Republic of"],
    "MK": ["Macedonia", "Macedonia Republic of"], "PS": ["Palestine", "Palestinian Territories"], "RU": ["Russia", "Russian Federation"],
    "SZ": ["Swaziland", "Eswatini"], "SY": ["Syria"], "TL": ["East Timor", "Timor Leste"], "TZ": ["Tanzania"],
    "TW": ["Taiwan", "Taiwan Province of China", "Republic of China"], "US": ["United States", "United States of America", "USA", "Etats Unis", "Etats Unis d Amerique"],
    "VA": ["Vatican", "Vatican City", "Holy See"], "VE": ["Venezuela", "Venezuela Bolivarian Republic of"], "VN": ["Vietnam", "Viet Nam"],
    "GB": ["United Kingdom", "Great Britain", "Royaume Uni", "Grande Bretagne"], "XK": ["Kosovo"], "CI": ["Ivory Coast", "Cote d Ivoire"],
    "BS": ["Bahamas", "Bahamas The"], "SU": ["Soviet Union", "USSR", "URSS"], "YU": ["Yugoslavia", "Yougoslavie"], "CS": ["Czechoslovakia", "Tchecoslovaquie"],
    "DD": ["East Germany", "Republique democratique allemande"], "OT": ["Ottoman Empire", "Empire ottoman"],
    "IR": ["Iran", "Iran Islamic Republic of", "Iran Islamic Rep of"],
    "KP": ["North Korea", "Korea Democratic Peoples Republic of", "Democratic People s Republic of Korea"],
    "KR": ["South Korea", "Korea Republic of", "Republic of Korea"], "FM": ["Micronesia", "Micronesia Fed States of", "Micronesia Federated States of"],
    "GB": ["United Kingdom", "Great Britain", "Royaume Uni", "Grande Bretagne", "United Kingdom of Great Britain and Northern Ireland"],
    "TZ": ["Tanzania", "United Republic of Tanzania"], "MK": ["Macedonia", "North Macedonia", "The former Yugoslav Republic of Macedonia"],
    "BAD": ["Baden"], "BAY": ["Bavaria"]
}.items():
    for alias in aliases:
        ALIASES[slug(alias)] = code


def country_code(name):
    normalized = re.sub(r"-the$", "", slug(name))
    return ALIASES.get(normalized, "")


def record(provider, key, country, title, language, urls, **extra):
    code = country_code(country)
    return {
        "id": provider + ":" + language + ":" + key,
        "provider": provider, "provider_id": key,
        "country_code": code, "country": COUNTRY_NAMES.get(code, country),
        "title": title, "language": language,
        "document_type": "constitution", "status": "unverified",
        "status_note": "Status describes the source edition, not a legal assessment of present validity.",
        "year_enacted": None, "year_revised": None,
        "discovered_at": now(), "urls": urls,
        "source_url": urls[0]["url"], **extra,
    }


def read_manifest():
    path = ROOT / "metadata" / "manifest.json"
    return json.loads(path.read_text()) if path.exists() else []


def merge_manifest(records):
    (ROOT / "metadata").mkdir(parents=True, exist_ok=True)
    with (ROOT / "metadata" / "manifest.lock").open("a") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        existing = {r["id"]: r for r in read_manifest()}
        for item in records:
            if item["id"] in existing:
                item["discovered_at"] = existing[item["id"]]["discovered_at"]
            existing[item["id"]] = item
        save_json(ROOT / "metadata" / "manifest.json", sorted(existing.values(), key=lambda r: r["id"]))
    log(f"Manifest: {len(existing)} document-language-source records")


def discover_constitute():
    records = []
    for language in ("en", "es", "ar"):
        url = "https://www.constituteproject.org/service/constitutions?lang=" + language
        body = cached_page(url, "constitute")
        data = json.loads(body)
        save_json(ROOT / "metadata" / f"constitute-{language}.json", data)
        for item in data:
            if not item.get("public") or not item.get("show", True):
                continue
            key = item["id"]
            base = "https://www.constituteproject.org/constitution/" + quote(key)
            status = "draft" if item.get("is_draft") else ("source_in_force" if item.get("in_force") else "historical_or_replaced")
            records.append(record("constitute", key, item["country_id"].replace("_", " "), item["title"], language,
                [{"url": base + ".pdf?lang=" + language, "format": "pdf"}, {"url": base + "?lang=" + language, "format": "html"}],
                status=status, year_enacted=item.get("year_enacted"), year_revised=item.get("year_revised"),
                update_needed=item.get("update_needed", False), translator=item.get("translator"),
                rights=item.get("copyright"), source_metadata=item))
        log(f"Constitute {language}: {len(data)} catalog entries")
    merge_manifest(records)


def add_seeds():
    path = ROOT / "seeds.json"
    if path.exists():
        merge_manifest(json.loads(path.read_text()))


def refresh_country_mapping():
    items = read_manifest()
    kept = []
    excluded = []
    for item in items:
        if item["provider"] == "constitute" and item["provider_id"] == "Germany_Prussia_1919":
            excluded.append({"id": item["id"], "reason": "Subnational constitution of Prussia, 1919; outside selected scope."})
            continue
        code = item.get("country_code") or country_code(item["country"])
        if code and code != item.get("country_code"):
            old_dir = document_dir(item)
            item.update(country_code=code, country=COUNTRY_NAMES[code])
            new_dir = document_dir(item)
            if old_dir.exists() and old_dir != new_dir:
                new_dir.parent.mkdir(parents=True, exist_ok=True)
                shutil.move(str(old_dir), str(new_dir))
                path = new_dir / "metadata.json"
                if path.exists():
                    data = json.loads(path.read_text())
                    data.update(country_code=code, country=COUNTRY_NAMES[code])
                    old_prefix, new_prefix = str(old_dir.relative_to(ROOT)), str(new_dir.relative_to(ROOT))
                    for asset in data.get("assets", []) + ([data["text"]] if data.get("text") else []):
                        asset["path"] = asset["path"].replace(old_prefix, new_prefix, 1)
                        if asset.get("extracted_from"):
                            asset["extracted_from"] = asset["extracted_from"].replace(old_prefix, new_prefix, 1)
                    save_json(path, data)
        kept.append(item)
    save_json(ROOT / "metadata" / "manifest.json", kept)
    if excluded:
        save_json(ROOT / "reports" / "excluded.json", excluded)
    log(f"Country mapping refreshed: {len(kept)} records; {len(excluded)} excluded")


def document_dir(item):
    country = (item["country_code"] or "UNMAPPED") + "-" + slug(item["country"])
    key = slug(item["provider_id"])[-130:]
    return ROOT / "countries" / country / key / item["language"] / item["provider"]


def html_text(body, provider, selector=None):
    soup = BeautifulSoup(body, "lxml")
    if selector:
        selected = soup.select_one(selector)
        if selected is None:
            raise ValueError("Expected full-text HTML selector not found")
    elif provider == "constitute":
        selected = soup.select_one("#constitution-content") or soup.select_one(".constitution-content")
        if selected is None:
            selected = soup.find(id=re.compile("^constitution"))
        if selected is None:
            # Constitute also embeds the full server-rendered document in article nodes.
            selected = soup.select_one("article") or soup.select_one("main")
    elif provider == "wikisource":
        selected = soup.select_one(".mw-parser-output")
    else:
        selected = soup.select_one("article") or soup.select_one("main")
    selected = selected or soup.body or soup
    for node in selected.select("script, style, nav, footer, header, .mw-editsection, .noprint, .printfooter, .catlinks"):
        node.decompose()
    lines = [re.sub(r"[ \t]+", " ", x).strip() for x in selected.get_text("\n").splitlines()]
    return "\n".join(x for x in lines if x) + "\n"


def validate_body(body, expected):
    if expected == "pdf":
        if not body[:1024].lstrip().startswith(b"%PDF-"):
            raise ValueError("Response is not a PDF")
    elif expected == "html":
        soup = BeautifulSoup(body[:150000], "lxml")
        title = soup.title.get_text(" ", strip=True).lower() if soup.title else ""
        if any(x in title for x in ("access denied", "just a moment", "page not found", "attention required", "404 not found", "403 forbidden")):
            raise ValueError("Error/challenge HTML: " + title)
        if len(body) < 300:
            raise ValueError("HTML response too short")
    elif len(body) < 100:
        raise ValueError("Document too short")


def asset_info(path, **extra):
    body = path.read_bytes()
    return {"path": str(path.relative_to(ROOT)), "bytes": len(body), "sha256": hashlib.sha256(body).hexdigest(), **extra}


def download_record(item, skip_known_errors=False):
    directory = document_dir(item)
    metadata_path = directory / "metadata.json"
    previous = json.loads(metadata_path.read_text()) if metadata_path.exists() else {}
    old_assets = {a["url"]: a for a in previous.get("assets", []) if a.get("url")}
    old_errors = {a["url"]: a for a in previous.get("errors", [])}
    assets, errors = [], []
    for link in item["urls"]:
        url, fmt = link["url"], link["format"]
        if skip_known_errors and url in old_errors and not (fmt == "html" and "not a PDF" in old_errors[url]["error"]):
            errors.append(old_errors[url])
            continue
        old = old_assets.get(url)
        if old:
            path = ROOT / old["path"]
            if path.exists() and asset_info(path)["sha256"] == old["sha256"]:
                assets.append(old)
                continue
        try:
            try:
                cached_path = ROOT / link["cached_path"] if link.get("cached_path") else None
                if cached_path and cached_path.is_file():
                    body, content_type, final_url = cached_path.read_bytes(), "text/html", url
                else:
                    body, content_type, final_url = get(link.get("download_url", url))
            except requests.HTTPError as error:
                if item["provider"] != "wipo" or error.response.status_code != 403:
                    raise
                details, _, _ = get(item["source_url"])
                soup = BeautifulSoup(details, "lxml")
                fresh = next((n["src"] for n in soup.select("iframe[src]") if n["src"].split("?")[0] == url), None)
                if not fresh:
                    raise ValueError("Could not refresh WIPO public PDF link") from error
                body, content_type, final_url = get(fresh)
            validate_body(body, fmt)
            directory.mkdir(parents=True, exist_ok=True)
            filename = link.get("filename", "original." + fmt)
            path = directory / filename
            if path.name != filename:
                raise ValueError("Unsafe filename")
            temp = path.with_suffix(path.suffix + ".part")
            temp.write_bytes(body)
            temp.replace(path)
            info = asset_info(path, url=url, final_url=final_url, retrieved_at=now(), content_type=content_type, format=fmt)
            if fmt == "pdf":
                result = subprocess.run(["pdfinfo", str(path)], capture_output=True, timeout=20)
                if result.returncode:
                    path.unlink()
                    raise ValueError("pdfinfo rejected PDF: " + result.stderr.decode(errors="replace")[:100])
                page_match = re.search(rb"^Pages:\s+(\d+)", result.stdout, re.M)
                info["pages"] = int(page_match.group(1)) if page_match else None
            assets.append(info)
        except Exception as error:
            errors.append({"url": url, "error": f"{type(error).__name__}: {error}"[:500], "at": now()})
    # Prefer PDF text to avoid archiving navigation as constitutional text.
    text_path = directory / "text.txt"
    text = ""
    extraction_source = None
    for asset in sorted(assets, key=lambda x: x["format"] != "pdf"):
        try:
            path = ROOT / asset["path"]
            if asset["format"] == "pdf":
                result = subprocess.run(["pdftotext", "-enc", "UTF-8", "-layout", str(path), "-"], capture_output=True, timeout=25)
                if result.returncode == 0:
                    text = result.stdout.decode("utf-8", errors="replace")
            elif asset["format"] == "html":
                text = html_text(path.read_bytes(), item["provider"], item.get("html_selector"))
            elif asset["format"] == "txt":
                text = path.read_text(encoding="utf-8", errors="replace")
            if len(text.strip()) >= 200:
                extraction_source = asset["path"]
                break
        except Exception:
            continue
    text_info = None
    if extraction_source:
        temporary = text_path.with_suffix(".txt.part")
        temporary.write_text(text, encoding="utf-8")
        temporary.replace(text_path)
        text_info = asset_info(text_path, extracted_from=extraction_source)
    result = {**item, "assets": assets, "text": text_info, "errors": errors, "last_checked_at": now(),
              "download_status": "complete" if assets and not errors else ("partial" if assets else "failed"),
              "needs_ocr_or_review": bool(assets and not text_info)}
    save_json(metadata_path, result)
    return result


def download(workers, provider=None, skip_known_errors=False):
    items = [r for r in read_manifest() if not provider or r["provider"] in provider]
    counts = {"complete": 0, "partial": 0, "failed": 0}
    error_counts = {}
    with concurrent.futures.ThreadPoolExecutor(max_workers=workers) as pool:
        futures = {pool.submit(download_record, r, skip_known_errors): r for r in items}
        for index, future in enumerate(concurrent.futures.as_completed(futures), 1):
            try:
                result = future.result()
                counts[result["download_status"]] += 1
                if result["errors"]:
                    error_counts[result["provider"]] = error_counts.get(result["provider"], 0) + 1
                    if error_counts[result["provider"]] <= 3:
                        log(f"ERROR {result['id']}: {result['errors']}")
                    elif error_counts[result["provider"]] == 4:
                        log(f"Further {result['provider']} errors are recorded in per-document metadata and reports/failures.json")
            except Exception as error:
                counts["failed"] += 1
                log(f"ERROR {futures[future]['id']}: {error}")
            if index % 20 == 0 or index == len(items):
                log(f"Downloaded/checked {index}/{len(items)}: {counts}")
    report(False)


def all_results():
    results = []
    for item in read_manifest():
        path = document_dir(item) / "metadata.json"
        if path.exists():
            results.append(json.loads(path.read_text()))
    return results


def report(verify):
    (ROOT / "metadata").mkdir(parents=True, exist_ok=True)
    with (ROOT / "metadata/report.lock").open("a") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        _report_unlocked(verify)


def _report_unlocked(verify):
    results = all_results()
    successful = [r for r in results if r.get("assets")]
    invalid = []
    hashes = {}
    bytes_total = 0
    for item in results:
        for asset in item.get("assets", []) + ([item["text"]] if item.get("text") else []):
            path = ROOT / asset["path"]
            if not path.exists() or (verify and asset_info(path)["sha256"] != asset["sha256"]):
                invalid.append(asset["path"])
            bytes_total += asset["bytes"]
            hashes.setdefault(asset["sha256"], []).append(asset["path"])
    duplicates = [paths for paths in hashes.values() if len(paths) > 1]
    if verify:
        for paths in duplicates:
            master = ROOT / paths[0]
            if not master.exists():
                continue
            for relative in paths[1:]:
                path = ROOT / relative
                if path.exists() and path.stat().st_ino != master.stat().st_ino and path.read_bytes() == master.read_bytes():
                    temporary = path.with_suffix(path.suffix + ".dedup")
                    os.link(master, temporary)
                    temporary.replace(path)
    catalog = ROOT / "catalog.jsonl"
    catalog.write_text("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in results), encoding="utf-8")
    fields = ["id", "country_code", "country", "title", "language", "provider", "document_type", "status", "year_enacted", "year_revised", "update_needed", "source_url", "download_status", "files", "text_path", "sha256", "retrieved_at"]
    with (ROOT / "catalog.csv").open("w", encoding="utf-8-sig", newline="") as stream:
        writer = csv.DictWriter(stream, fields)
        writer.writeheader()
        for item in results:
            writer.writerow({**{f: item.get(f, "") for f in fields}, "files": " | ".join(a["path"] for a in item.get("assets", [])),
                "text_path": (item.get("text") or {}).get("path", ""), "sha256": " | ".join(a["sha256"] for a in item.get("assets", [])),
                "retrieved_at": " | ".join(a["retrieved_at"] for a in item.get("assets", []))})
    by_country = {}
    for item in successful:
        by_country.setdefault(item["country_code"] or item["country"], []).append(item)
    summary = {"generated_at": now(), "manifest_records": len(read_manifest()), "downloaded_records": len(successful),
        "jurisdictions": len(by_country), "languages": sorted({r["language"] for r in successful}),
        "known_language_count": len({r["language"] for r in successful} - {"und", "mul"}),
        "unidentified_language_records": sum(r["language"] == "und" for r in successful),
        "multilingual_records": sum(r["language"] == "mul" for r in successful),
        "original_files": sum(len(r["assets"]) for r in successful), "text_files": sum(bool(r.get("text")) for r in successful),
        "logical_bytes": bytes_total, "unique_asset_bytes": sum((ROOT / paths[0]).stat().st_size for paths in hashes.values() if (ROOT / paths[0]).exists()),
        "providers": {p: sum(r["provider"] == p for r in successful) for p in sorted({r["provider"] for r in results})},
        "failed_records": sum(not r.get("assets") for r in results), "partial_records": sum(r.get("download_status") == "partial" for r in results),
        "unmapped_records": [r["id"] for r in successful if not r["country_code"]], "invalid_assets": invalid,
        "duplicate_groups": len(duplicates), "verified_hashes": verify}
    save_json(ROOT / "reports" / "summary.json", summary)
    save_json(ROOT / "reports" / "duplicates.json", duplicates)
    save_json(ROOT / "reports" / "failures.json", [{"id": r["id"], "errors": r["errors"]} for r in results if r.get("errors")])
    lines = ["# Indeks konstytucji", "", f"Stan zbioru: {summary['generated_at']}. Pozycja oznacza dokument w danym języku i źródle.", "", "| Państwo lub terytorium | Pozycje | Języki |", "|---|---:|---|"]
    for code, items in sorted(by_country.items(), key=lambda pair: pair[1][0]["country"]):
        directory = document_dir(items[0]).parents[2]
        lines.append(f"| [{items[0]['country']}]({directory.relative_to(ROOT)}/) | {len(items)} | {', '.join(sorted({r['language'] for r in items}))} |")
    lines.extend(["", "# Dokumenty", "", "| Państwo | Tytuł | Język | Status źródłowy | Pliki |", "|---|---|---|---|---|"])
    for item in sorted(successful, key=lambda r: (r["country"], r["title"], r["language"])):
        links = [f"[{a['format']}]({quote(a['path'])})" for a in item["assets"]]
        if item.get("text"):
            links.append(f"[txt]({quote(item['text']['path'])})")
        title = item["title"].replace("|", " ").replace("\n", " ")
        lines.append(f"| {item['country']} | {title} | {item['language']} | {item['status']} | {' '.join(links)} |")
    (ROOT / "INDEX.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    # ISO includes territories; exclude them explicitly to obtain the UN membership baseline.
    non_un = set("AX AS AI AQ AW BL BM BQ BV CC CX CK CW EH FK FO GF GG GI GL GP GS GU HK HM IM IO JE KY MF MO MP MQ MS NC NF NU PF PM PN PR RE SH SJ SX TC TF TK TW UM VG VI WF YT XK VA PS".split())
    baseline = {r["alpha_2"] for r in COUNTRIES} - non_un
    baseline |= {"VA", "PS"}
    missing = sorted(baseline - set(by_country), key=lambda code: COUNTRY_NAMES[code])
    save_json(ROOT / "reports" / "coverage.json", {"baseline": "193 UN members + 2 observer states", "baseline_count": len(baseline),
        "covered": len(baseline & set(by_country)), "missing": [{"code": c, "country": COUNTRY_NAMES[c]} for c in missing],
        "additional_jurisdictions": sorted(set(by_country) - baseline)})
    gap_lines = ["# Pokrycie i braki", "", f"Baza kontrolna: {len(baseline)} państw (193 członków ONZ i 2 państwa obserwatorów).", f"Pobrano co najmniej jeden dokument dla {len(baseline & set(by_country))} państw z tej listy.", "", "Samo pokrycie nie potwierdza aktualności tekstu ani pełnej historii konstytucyjnej.", "", "## Brak pobranego dokumentu", ""]
    gap_lines.extend([f"- {COUNTRY_NAMES[c]} ({c}): do uzupełnienia ze źródeł urzędowych lub archiwalnych." for c in missing] or ["Brak luk geograficznych w bazie kontrolnej."])
    gap_lines.extend(["", "## Ograniczenia", "", "- Status obowiązywania zapisano zgodnie ze źródłem; nie jest to niezależne potwierdzenie prawne.", "- Historia i liczba wersji językowych pozostają niepełne; dostępne publicznie katalogi nie obejmują wszystkich wydań.", "- Skany bez warstwy tekstowej oznaczono do OCR; nie uruchamiano automatycznego OCR.", "- Nie pobierano zasobów wymagających logowania ani płatnego dostępu.", "- Tłumaczenia i redakcje mają własne warunki wykorzystania, zapisane w źródłach i metadanych.", "", f"Błędy pobierania: {summary['failed_records']} pozycji; częściowo pobrane: {summary['partial_records']}. Szczegóły: failures.json.", f"Niezgodne lub brakujące pliki: {len(invalid)}."])
    (ROOT / "reports" / "GAPS.md").write_text("\n".join(gap_lines) + "\n", encoding="utf-8")
    log(json.dumps(summary, ensure_ascii=False))
    if verify and invalid:
        raise SystemExit(1)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=["discover", "download", "report", "verify", "remap"])
    parser.add_argument("--provider", action="append")
    parser.add_argument("--workers", type=int, default=4)
    parser.add_argument("--skip-known-errors", action="store_true")
    args = parser.parse_args()
    if args.command == "discover":
        discover_constitute()
        add_seeds()
        refresh_country_mapping()
    elif args.command == "remap":
        refresh_country_mapping()
    elif args.command == "download":
        download(max(1, min(args.workers, 8)), args.provider, args.skip_known_errors)
    else:
        report(args.command == "verify")


if __name__ == "__main__":
    main()
