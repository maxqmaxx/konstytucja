#!/usr/bin/env python3
"""Add targeted primary-source constitutional instruments."""

import re

from collect import ROOT, merge_manifest, read_manifest, record, save_json


def main():
    seeds = []
    uk = [
        ("magna-carta-1297", "Magna Carta 1297", "aep/Edw1cc1929/25/9"),
        ("petition-of-right-1627", "Petition of Right 1627", "aep/Cha1/3/1"),
        ("bill-of-rights-1688", "Bill of Rights 1688", "aep/WillandMarSess2/1/2"),
        ("act-of-settlement-1700", "Act of Settlement 1700", "aep/Will3/12-13/2"),
        ("union-with-scotland-1706", "Union with Scotland Act 1706", "aep/Ann/6/11"),
        ("parliament-act-1911", "Parliament Act 1911", "ukpga/Geo5/1-2/13"),
        ("parliament-act-1949", "Parliament Act 1949", "ukpga/Geo6/12-13-14/103"),
        ("human-rights-act-1998", "Human Rights Act 1998", "ukpga/1998/42"),
        ("constitutional-reform-act-2005", "Constitutional Reform Act 2005", "ukpga/2005/4"),
    ]
    for key, title, path in uk:
        base = "https://www.legislation.gov.uk/" + path
        seeds.append(record("uk-legislation", key, "United Kingdom", title, "en",
            [{"url": base + "/data.pdf", "format": "pdf"}, {"url": base + "/data.htm", "format": "html"}],
            source_url=base, document_type="constitutional_instrument", status="official_edition_unverified"))
    for language, url in [("en", "https://laws-lois.justice.gc.ca/eng/Const/FullText.html"), ("fr", "https://laws-lois.justice.gc.ca/fra/Const/TexteComplet.html")]:
        seeds.append(record("canada-justice", "constitutional-acts-1867-1982", "Canada", "Constitution Acts, 1867 to 1982", language,
            [{"url": url, "format": "html"}], document_type="constitutional_instruments", status="official_edition_unverified"))
    seeds.append(record("nz-legislation", "constitution-act-1986-2025", "New Zealand", "Constitution Act 1986, version as at 13 November 2025", "en",
        [{"url": "https://www.legislation.govt.nz/act/public/1986/114/en/2025-11-13.pdf", "format": "pdf"}],
        document_type="constitutional_instrument", year_enacted="1986", year_revised="2025", status="official_edition_unverified"))
    seeds.append(record("nz-legislation", "bill-of-rights-act-1990", "New Zealand", "New Zealand Bill of Rights Act 1990", "en",
        [{"url": "https://www.legislation.govt.nz/act/public/1990/0109/latest/whole.html", "format": "html"}],
        document_type="constitutional_instrument", year_enacted="1990", status="official_edition_unverified"))
    # Replace fragile legacy ISAP downloads with the official ELI API endpoints.
    seen = set()
    for item in read_manifest():
        for link in item["urls"]:
            if "isap.sejm.gov.pl" not in link["url"]:
                continue
            match = re.search(r"WDU(\d{4})\d{3}(\d{4,5})", link["url"], re.I)
            if not match:
                continue
            year, position = match.group(1), str(int(match.group(2)))
            key = f"DU-{year}-{position}"
            if key in seen:
                continue
            seen.add(key)
            base = f"https://api.sejm.gov.pl/eli/acts/DU/{year}/{position}"
            seeds.append(record("eli-sejm", key, "Poland", item["title"], "pl",
                [{"url": base + "/text.pdf", "format": "pdf"}], source_url=f"https://eli.gov.pl/eli/DU/{year}/{position}/ogl",
                year_enacted=year, status="official_publication_unverified"))
    save_json(ROOT / "seeds.json", seeds)
    merge_manifest(seeds)


if __name__ == "__main__":
    main()
