#!/usr/bin/env python3
"""Reconcile source labels, archive exclusions and cached full-text alternatives."""

from collections import defaultdict
import hashlib
import json
import re
import shutil

from bs4 import BeautifulSoup

from collect import ROOT, document_dir, html_text, log, read_manifest, save_json, slug
from sources import attach_wipo_html


LANGUAGES = {
    "oshikwanyama": "kj", "venda": "ve", "gudzarati": "gu", "malgask": "mg", "manipuri": "mni", "tamilsk": "ta",
    "nepalsk": "ne", "bodo": "brx", "palausk": "pau", "kaszmirsk": "ks", "kannada": "kn", "marathi": "mr", "afrikaans": "af",
    "turkmensk": "tk", "assamsk": "as", "soto": "st", "wlosk": "it", "sindhi": "sd", "dari-i-paszto": "mul",
    "khmersk": "km", "kiribati": "gil", "hindi": "hi", "czarnogorsk": "cnr", "marszalsk": "mh", "jezyk-shuar": "jiv",
    "retoromansk": "rm", "malediwsk": "dv", "jezyk-keczua": "qu", "tonga": "to", "romsk": "rom", "konkani": "kok",
    "kurdyjsk": "ku", "ndebele": "nr", "dogri": "doi", "sanskryt": "sa", "slowack": "sk", "odia": "or", "amharsk": "am",
    "bengalsk": "bn", "syngalesk": "si", "cokwe": "cjk", "bislama": "bi", "samoansk": "sm", "kirundi-i-francusk": "mul",
    "tsonga": "ts", "santhali": "sat", "guarani": "gn", "tetum": "tet", "tajsk": "th", "zulu": "zu", "malajalam": "ml",
    "kikongo": "kg", "urdu": "ur", "pedi": "nso", "laotansk": "lo", "swazi": "ss", "maithili": "mai", "pendzabsk": "pa",
    "tswana": "tn", "kazachsk": "kk", "somalijsk": "so", "umbundu": "umb", "telugu": "te", "kosa": "xh", "kimbundu": "kmb", "kirgisk": "ky",
}


def move_metadata(item, old_directory, new_directory):
    if old_directory != new_directory and old_directory.exists():
        new_directory.parent.mkdir(parents=True, exist_ok=True)
        if new_directory.exists():
            raise ValueError(f"Refusing to overwrite directory during metadata migration: {new_directory}")
        shutil.move(str(old_directory), str(new_directory))
    path = new_directory / "metadata.json"
    if not path.exists():
        return
    old = json.loads(path.read_text())
    old_prefix, new_prefix = str(old_directory.relative_to(ROOT)), str(new_directory.relative_to(ROOT))
    for asset in old.get("assets", []) + ([old["text"]] if old.get("text") else []):
        for field in ("path", "extracted_from"):
            if asset.get(field):
                asset[field] = asset[field].replace(old_prefix, new_prefix, 1)
    save_json(path, {**old, **item})


def main():
    save_json(ROOT / "metadata/sejm-language-map.json", LANGUAGES)
    items = read_manifest()
    grouped = defaultdict(list)
    exclusions, kept = [], []
    for item in items:
        if item["provider"] == "wipo":
            grouped[item["source_url"]].append(item)
    enriched = 0
    for url, group in grouped.items():
        path = next((ROOT / "metadata/pages/wipo-details" / (hashlib.sha256((url + suffix).encode()).hexdigest()[:24] + ".html")
                     for suffix in ("", "?view=full")
                     if (ROOT / "metadata/pages/wipo-details" / (hashlib.sha256((url + suffix).encode()).hexdigest()[:24] + ".html")).exists()
                     and (ROOT / "metadata/pages/wipo-details" / (hashlib.sha256((url + suffix).encode()).hexdigest()[:24] + ".html")).stat().st_size > 100), None)
        if path is None:
            continue
        cache_url = url if path.stem == hashlib.sha256(url.encode()).hexdigest()[:24] else url + "?view=full"
        soup = BeautifulSoup(path.read_bytes(), "lxml")
        for item in group:
            attach_wipo_html(item, soup, cache_url)
            enriched += bool(item.get("html_selector"))
    migrated = 0
    for item in items:
        old_directory = document_dir(item)
        if item["provider"] == "sejm-library" and item["language"] == "und":
            note = slug(item.get("language_note", ""))
            item["language"] = next((code for prefix, code in LANGUAGES.items() if note.startswith(prefix)), "und")
        if item["provider"] == "wipo" and item["language"] in ("ie", "cg"):
            item["source_language_code"] = item["language"]
            item["language"] = {"ie": "ga", "cg": "cnr"}[item["language"]]
        item["id"] = item["provider"] + ":" + item["language"] + ":" + item["provider_id"]
        if item["provider"] == "mjp" and not re.search(r"\d", item["provider_id"]):
            body = (ROOT / item["urls"][0]["cached_path"]).read_bytes()
            article_count = len(re.findall(r"\b(?:Article|Art\.)\s+(?:\d|premier|unique|[IVX])", html_text(body, "mjp"), re.I))
            if article_count < 15:
                exclusions.append({"id": item["id"], "reason": "Country overview with chronology and references, not a full legal instrument."})
                if old_directory.exists():
                    destination = ROOT / "excluded" / "country-overviews" / item["provider_id"]
                    destination.parent.mkdir(parents=True, exist_ok=True)
                    if not destination.exists():
                        shutil.move(str(old_directory), str(destination))
                continue
        new_directory = document_dir(item)
        migrated += old_directory != new_directory
        move_metadata(item, old_directory, new_directory)
        kept.append(item)
    save_json(ROOT / "metadata/manifest.json", kept)
    exclusions_path = ROOT / "reports/content-exclusions.json"
    previous_exclusions = json.loads(exclusions_path.read_text()) if exclusions_path.exists() else []
    exclusions_by_id = {item["id"]: item for item in previous_exclusions + exclusions}
    save_json(exclusions_path, list(exclusions_by_id.values()))
    prussia = ROOT / "countries/UNMAPPED-germany-prussia/germany-prussia-1919/en/constitute"
    if prussia.exists():
        destination = ROOT / "excluded/subnational/prussia-1919"
        destination.parent.mkdir(parents=True, exist_ok=True)
        if not destination.exists():
            shutil.move(str(prussia), str(destination))
    for metadata_path in (ROOT / "excluded").rglob("metadata.json"):
        data = json.loads(metadata_path.read_text())
        for asset in data.get("assets", []) + ([data["text"]] if data.get("text") else []):
            asset["path"] = str((metadata_path.parent / asset["path"].split("/")[-1]).relative_to(ROOT))
            if asset.get("extracted_from"):
                asset["extracted_from"] = str((metadata_path.parent / asset["extracted_from"].split("/")[-1]).relative_to(ROOT))
        data["archive_status"] = "excluded_from_catalog"
        save_json(metadata_path, data)
    log(f"Enriched {enriched} WIPO records with existing full HTML; migrated {migrated} language labels; excluded {len(exclusions)} country overviews")


if __name__ == "__main__":
    main()
