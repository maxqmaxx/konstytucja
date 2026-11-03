#!/usr/bin/env python3
"""Resolve bibliography download labels that actually point to document landing pages."""

import concurrent.futures
import hashlib
import re
from urllib.parse import urljoin, urlparse

from bs4 import BeautifulSoup

from collect import ROOT, all_results, cached_page, html_text, log, merge_manifest, read_manifest, save_json


def resolve(item):
    url = item["urls"][0]["url"]
    body = cached_page(url, "landings")
    if body[:1024].lstrip().startswith(b"%PDF-"):
        return item, [{"url": url, "format": "pdf"}]
    soup = BeautifulSoup(body, "lxml")
    candidates = []
    for node in soup.select("a[href], iframe[src], embed[src], object[data]"):
        target = urljoin(url, node.get("href") or node.get("src") or node.get("data"))
        parsed = urlparse(target)
        if parsed.scheme not in ("https", "http"):
            continue
        if parsed.path.lower().endswith(".pdf") or "abrir_pdf.php" in parsed.path:
            candidates.append(target)
    candidates = list(dict.fromkeys(candidates))
    if len(candidates) > 3:
        filtered = [u for u in candidates if re.search(r"constit|ustav|konst|fundamen|charte", u, re.I)]
        candidates = filtered or candidates[:1]
    if candidates:
        return item, [{"url": u, "format": "pdf", "filename": f"resolved-{index}.pdf"} for index, u in enumerate(candidates[:3], 1)]
    text = html_text(body, "sejm-library")
    if len(text) > 10000 and len(re.findall(r"\b(?:Article|Art\.|Section)\s+(?:\d|premier|unique|[IVX])", text, re.I)) >= 10:
        key = hashlib.sha256(url.encode()).hexdigest()[:24]
        return item, [{"url": url, "format": "html", "cached_path": f"metadata/pages/landings/{key}.html"}]
    return item, []


def main():
    results = {r["id"]: r for r in all_results()}
    targets = [r for r in read_manifest() if r["provider"] == "sejm-library" and r["id"] in results
               and not results[r["id"]]["assets"] and any("not a PDF" in e["error"] for e in results[r["id"]].get("errors", []))
               and r["country_code"] not in ("PL", "UG")]
    updated, outcomes = [], []
    with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:
        futures = {pool.submit(resolve, item): item for item in targets}
        for future in concurrent.futures.as_completed(futures):
            original = futures[future]
            try:
                item, urls = future.result()
                if urls:
                    item["bibliography_original_links"] = item["urls"]
                    item["urls"] = urls
                    updated.append(item)
                outcomes.append({"id": item["id"], "resolved_urls": len(urls)})
            except Exception as error:
                outcomes.append({"id": original["id"], "error": str(error)[:300]})
    merge_manifest(updated)
    save_json(ROOT / "reports/landing-resolution.json", outcomes)
    log(f"Landing page review: {len(targets)} reviewed; {len(updated)} resolved")


if __name__ == "__main__":
    main()
