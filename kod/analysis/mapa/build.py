#!/usr/bin/env python3
"""Build the world map of constitutional topics (static, offline).

Inputs: Natural Earth 1:50m via world-atlas@2.0.2 (vendor/, ISC licence, public-domain data),
CCP topic tables from ../features, atlas entries from ../zapisy.json.
Output: index.html with inline SVG paths (Equal Earth projection) and embedded data.
Run from the project root: python3 analysis/mapa/build.py
"""
from __future__ import annotations

import hashlib
import json
import re
import math
from collections import defaultdict
from html import escape
from pathlib import Path

from babel import Locale

import sys
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "features"))
import ccp_data  # noqa: E402

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
FEATURES = HERE.parent / "features"
WIDTH = 1000.0
MIN_STEP = 0.6  # px; drop vertices closer than this to the previous kept one
EXTRA_POINTS = {"TV": (179.2, -8.5)}  # Tuvalu is absent from Natural Earth 1:50m
NAME_TO_ISO = {"Kosovo": "XK"}
FEATURED = ["unamend", "cappun", "water", "hosterml", "amparo", "env", "judcrts2", "ombuds", "referen",
            "initiat", "offrel", "god", "equalgr7", "infoacc", "balbudgt", "cc", "milserv", "arms"]
EU27 = {"AT", "BE", "BG", "HR", "CY", "CZ", "DK", "EE", "FI", "FR", "DE", "GR", "HU", "IE", "IT",
        "LV", "LT", "LU", "MT", "NL", "PL", "PT", "RO", "SK", "SI", "ES", "SE"}


def equal_earth(lon, lat):
    a1, a2, a3, a4 = 1.340264, -0.081106, 0.000893, 0.003796
    m = math.sqrt(3) / 2
    lam, phi = math.radians(lon), math.radians(lat)
    th = math.asin(m * math.sin(phi))
    t2, t6 = th * th, th ** 6
    x = 2 * math.sqrt(3) * lam * math.cos(th) / (3 * (9 * a4 * t6 * t2 + 7 * a3 * t6 + 3 * a2 * t2 + a1))
    y = th * (a4 * t6 * t2 + a3 * t6 + a2 * t2 + a1)
    return x, y


XMAX = equal_earth(180, 0)[0]
SCALE = WIDTH / (2 * XMAX)
TOP = equal_earth(0, 84)[1]
YCUT = equal_earth(0, -58)[1]  # crop Antarctic latitudes
HEIGHT = round((TOP - YCUT) * SCALE)


def project(lon, lat):
    x, y = equal_earth(lon, lat)
    return (x + XMAX) * SCALE, (TOP - y) * SCALE


def decode_arcs(topo):
    sx, sy = topo["transform"]["scale"]
    tx, ty = topo["transform"]["translate"]
    arcs = []
    for arc in topo["arcs"]:
        x = y = 0
        pts = []
        for dx, dy in arc:
            x += dx
            y += dy
            pts.append((x * sx + tx, y * sy + ty))  # lon/lat; projected per ring
        arcs.append(pts)
    return arcs


def ring_path(ring, arcs):
    lonlat = []
    for index in ring:
        arc = arcs[index] if index >= 0 else arcs[~index][::-1]
        lonlat.extend(arc if not lonlat else arc[1:])
    # world-atlas rings may cross the antimeridian: unwrap longitudes, then clamp to the map edge.
    unwrapped, prev = [], None
    for lon, lat in lonlat:
        if prev is not None:
            while lon - prev > 180:
                lon -= 360
            while lon - prev < -180:
                lon += 360
        unwrapped.append((lon, lat))
        prev = lon
    pts = [project(max(-180.0, min(180.0, lon)), lat) for lon, lat in unwrapped]
    out, last = [], None
    for x, y in pts:
        p = (round(x, 1), round(y, 1))
        if last is None or (p[0] - last[0]) ** 2 + (p[1] - last[1]) ** 2 >= MIN_STEP ** 2:
            out.append(p)
            last = p
    if len(out) < 3:  # tiny islands: keep every distinct rounded vertex
        out = []
        for x, y in pts:
            p = (round(x, 1), round(y, 1))
            if not out or p != out[-1]:
                out.append(p)
    if len(out) < 3:
        return "", 0.0
    area = 0.5 * abs(sum(out[i][0] * out[i - 1][1] - out[i - 1][0] * out[i][1] for i in range(len(out))))
    d = "M" + "L".join(f"{x:g} {y:g}" for x, y in out) + "Z"
    return d, area


def geometry_path(geom, arcs):
    polys = geom["arcs"] if geom["type"] == "MultiPolygon" else [geom["arcs"]] if geom["type"] == "Polygon" else []
    parts, total, best = [], 0.0, (0.0, None)
    for poly in polys:
        for k, ring in enumerate(poly):
            d, area = ring_path(ring, arcs)
            if d:
                parts.append(d)
                if k == 0:
                    total += area
                    if area > best[0]:
                        xs = [float(v.split(" ")[0]) for v in d[1:-1].split("L")]
                        ys = [float(v.split(" ")[1]) for v in d[1:-1].split("L")]
                        best = (area, (sum(xs) / len(xs), sum(ys) / len(ys)))
    return "".join(parts), total, best[1]


def relative_path(d: str) -> str:
    """Absolute "M x yL x y…Z" -> "M x yl dx dy dx dy…z": same shape, about 40% shorter."""
    out = []
    for sub in re.findall(r"M[^M]*", d):
        closed = sub.rstrip().endswith("Z")
        pts = [tuple(map(float, p.split())) for p in re.split(r"[ML]", sub.replace("Z", "")) if p.strip()]
        if not pts:
            continue
        x0, y0 = pts[0]
        steps, px, py = [], round(x0, 1), round(y0, 1)
        for x, y in pts[1:]:
            x, y = round(x, 1), round(y, 1)
            dx, dy = round(x - px, 1), round(y - py, 1)
            if dx or dy:
                steps.append(f"{dx:g} {dy:g}")
            px, py = x, y
        out.append(f"M{round(x0, 1):g} {round(y0, 1):g}" + ("l" + " ".join(steps) if steps else "") + ("z" if closed else ""))
    return "".join(out).replace(" -", "-")


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> int:
    topo_path = HERE / "vendor/countries-50m.json"
    topo = json.loads(topo_path.read_text())
    iso = {r["numeric"]: r["alpha_2"] for r in json.loads((ROOT / "metadata/iso3166-1.json").read_text())["3166-1"]}
    names_pl = Locale("pl").territories
    ccp = ccp_data.load()
    labels, docs, by_code, topic_keys, tindex, sections = ccp.labels, ccp.docs, ccp.by_code, ccp.topic_keys, ccp.tindex, ccp.sections

    catalog = {}
    with open(ROOT / "catalog.jsonl", encoding="utf-8") as fh:
        for line in fh:
            rec = json.loads(line)
            if rec["id"] in docs:
                catalog[rec["id"]] = rec
    atlas = defaultdict(list)
    for z in json.loads((HERE.parent / "zapisy.json").read_text()):
        atlas[z["country_code"]].append([z["id"].lower(), z["title"]])

    arcs = decode_arcs(topo)
    shapes, seen = [], set()
    for geom in topo["objects"]["countries"]["geometries"]:
        code = iso.get(str(geom.get("id"))) or NAME_TO_ISO.get(geom["properties"]["name"])
        if code == "AQ":
            continue
        d, area, centre = geometry_path(geom, arcs)
        if not d:
            continue
        seen.add(code)
        shapes.append({"code": code or "", "name": names_pl.get(code, geom["properties"]["name"]) if code else geom["properties"]["name"],
                       "d": d, "small": area < 6, "c": [round(centre[0], 1), round(centre[1], 1)] if centre else None})
    for code, (lon, lat) in EXTRA_POINTS.items():
        x, y = project(lon, lat)
        shapes.append({"code": code, "name": names_pl.get(code, code), "d": "", "small": True, "c": [round(x, 1), round(y, 1)]})

    countries = {}
    for code, doc in by_code.items():
        rec = catalog[doc["id"]]
        html_url = next((u["url"] for u in rec.get("urls") or [] if u.get("format") == "html"), rec["source_url"])
        countries[code] = {
            "name": names_pl.get(code, doc["country"]), "title": doc["title"],
            "year": doc["year_enacted"], "revised": doc["year_revised"],
            "stale": bool(rec.get("update_needed")) if "update_needed" in rec else None,
            "url": html_url.split("?")[0], "local": doc["html"],
            "eu": code in EU27, "atlas": atlas.get(code, []),
        }
        # article labels repeat across topics: store each once (app.js expands them on load)
        arts, idx, topics = [], {}, {}
        for t, (label, sec) in sections.get(code, {}).items():
            if label not in idx:
                idx[label] = len(arts)
                arts.append(label)
            topics[t] = [idx[label], sec]
        countries[code]["arts"], countries[code]["topics"] = arts, topics
    missing = sorted(set(by_code) - seen - set(EXTRA_POINTS))
    if missing:
        raise SystemExit(f"sample countries without geometry: {missing}")

    data = {
        "topics": ccp.topic_rows(),
        "featured": [tindex[k] for k in FEATURED], "countries": countries,
        "sample": len(docs), "width": WIDTH, "height": HEIGHT,
    }
    paths = []
    for s in sorted(shapes, key=lambda s: s["small"]):
        label = escape(s["name"])
        if s["d"]:
            paths.append(f'<path class="land{" in" if s["code"] in countries else ""}" data-code="{s["code"]}" d="{relative_path(s["d"])}"><title>{label}</title></path>')
    dots = "".join(
        f'<circle class="dot in" data-code="{s["code"]}" cx="{s["c"][0]}" cy="{s["c"][1]}" r="3.2"><title>{escape(s["name"])}</title></circle>'
        for s in shapes if s["small"] and s["code"] in countries and s["c"])
    page = (HERE / "template.html").read_text()
    payload = json.dumps(data, ensure_ascii=False, separators=(",", ":")).replace("<", "\\u003c")
    options = "".join(f'<option value="{tindex[k]}">{escape(labels[k])}</option>' for k in FEATURED)
    all_options = "".join(f'<option value="{i}">{escape(labels[k])}</option>' for i, k in enumerate(topic_keys))
    for key, value in {"@@PATHS@@": "".join(paths), "@@DOTS@@": dots, "@@DATA@@": payload,
                       "@@VIEWBOX@@": f"0 0 {WIDTH:g} {HEIGHT}", "@@FEATURED@@": options, "@@ALL@@": all_options,
                       "@@SAMPLE@@": str(len(docs))}.items():
        if page.count(key) < 1 or (key != "@@SAMPLE@@" and page.count(key) != 1):
            raise SystemExit(f"template placeholder {key} count invalid")
        page = page.replace(key, value)
    (HERE / "index.html").write_text(page)
    manifest = {"inputs": {str(p.relative_to(ROOT)): sha(p) for p in [topo_path, FEATURES / "prevalence.csv", FEATURES / "ccp_sections.csv", FEATURES / "topic_labels_pl.json", HERE.parent / "zapisy.json"]},
                "shapes": len(shapes), "sample_countries": len(countries), "small_markers": dots.count("<circle"),
                "index_bytes": (HERE / "index.html").stat().st_size}
    (HERE / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=1) + "\n")
    print(json.dumps(manifest))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
