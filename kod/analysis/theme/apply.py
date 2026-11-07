#!/usr/bin/env python3
"""Shared theme: dark mode and a theme switch for every page, without rewriting each stylesheet by hand.

1. Every hex colour in CSS values (stylesheets, <style> blocks, style="" attributes) becomes
   var(--c-RRGGBB, #orig): the light look is unchanged even without theme.css.
2. theme.css defines a dark counterpart for each colour: lightness is mirrored in OKLab (paper -> near black,
   ink -> near white, green stays green but lighter), hue kept, chroma slightly reduced. The navigation bar
   and colours on it keep their light values (it is already dark).
3. Every page gets theme.css and theme.js (theme switch in the navigation, remembered per browser).

Idempotent. Usage: python3 analysis/theme/apply.py [root]   (default: analysis/)
"""
from __future__ import annotations

import math
import os
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
HEX = re.compile(r"(?<![\w,-])#([0-9a-fA-F]{6}|[0-9a-fA-F]{3})(?![\w-])")
VALUE = re.compile(r":[^;{}<>]*(?=[;}])|:[^;{}\"<>]*$")
# colours of the dark header / hero / nav: same in both themes
KEEP = {"142d3b", "e4eddf", "a8d1ba", "41525e", "b7c9d2", "dbe5e8", "bc642e"}
JS_FILES = ["mapa/app.js"]  # colour string literals used for map fills and legends
CSS_FILES = ["panstwa/style.css", "rp/rp.css", "polska/style.css", "mapa/style.css", "wizualizacje/style.css"]
SKIP_DIRS = {"vendor", "node_modules", "sources", "__pycache__"}
sys.path.insert(0, str(HERE.parent / "panstwa"))
NAV_ITEMS = None  # loaded lazily from panstwa/build.py (single source of the menu)
CURRENT = {"mapa": "mapa", "rp": "rp", "problemy": "problemy", "tematy": "tematy", "konstruktor": "konstruktor", "statystyki": "statystyki", "wladza": "wladza",
           "panstwa": "panstwa", "polska": "polska", "wizualizacje": "wizualizacje", "ATLAS.html": "atlas"}
SITE = "https://maxqmaxx.github.io/konstytucja/"
SITE_NAME = "Konstytucje świata"
DEFAULT_DESC = "Dane i narzędzia do myślenia o lepszej polskiej konstytucji: 188 konstytucji świata, 331 rozwiązań, Konstytucja RP na tle świata."
ATLAS_DESC = "130 nietypowych zapisów konstytucyjnych z całego świata: oryginalne, ważne i niebezpieczne rozwiązania, z parafrazą, znaczeniem i źródłem."
# section (first path component or file) -> share image in theme/og/
OG = {"mapa": "mapa", "rp": "rp", "problemy": "problemy", "tematy": "tematy", "konstruktor": "konstruktor", "statystyki": "statystyki",
      "wladza": "wladza", "panstwa": "panstwa", "polska": "polska", "ATLAS.html": "atlas", "teczka": "teczka"}
META_RE = re.compile(r"<!--meta-->.*?<!--/meta-->", re.S)
NAV_RE = re.compile(r'<nav class="site-nav"[^>]*>.*?</nav>|<nav aria-label="Widoki kolekcji">.*?</nav>(?=\s*<div class="hero">)', re.S)


def nav_items():
    global NAV_ITEMS
    if NAV_ITEMS is None:
        src = (HERE.parent / "panstwa" / "build.py").read_text(encoding="utf-8")
        block = src[src.index("NAV_ITEMS = ["):]
        block = block[:block.index("]\n") + 1]
        ns = {}
        exec(block, ns)
        NAV_ITEMS = ns["NAV_ITEMS"]
    return NAV_ITEMS


def site_nav(rel: str, up: str) -> str:
    first = rel.split("/")[0]
    current = CURRENT.get(first)
    links = "".join(f'<a href="{up}{href}"{' aria-current="page"' if key == current else ""}>{label}</a>' for href, label, key in nav_items())
    return f'<nav class="site-nav" aria-label="Serwis"><a class="brand" href="{up}ATLAS.html">Konstytucje świata</a><div class="nav-links">{links}</div></nav>'



def head_meta(html: str, rel: str, up: str) -> str:
    """Favicon, Open Graph and Twitter card tags (idempotent: replaced between <!--meta--> markers)."""
    html = META_RE.sub("", html)
    title = re.search(r"<title>(.*?)</title>", html, re.S)
    title = re.sub(r"\s+", " ", title.group(1)).strip().replace('"', "&quot;") if title else SITE_NAME
    desc = re.search(r'<meta name="description" content="([^"]*)"', html)
    extra = ""
    fallback = ATLAS_DESC if rel.endswith("ATLAS.html") else DEFAULT_DESC
    if not desc:
        extra = f'<meta name="description" content="{fallback}">'
    desc = desc.group(1) if desc else fallback
    first = rel.split("/")[0]
    img = "symulator" if rel == "wladza/symulator.html" else OG.get(first, "default")
    url = SITE + ("" if rel == "index.html" else rel)
    tags = (f'<link rel="icon" href="{up}/favicon.svg" type="image/svg+xml"><link rel="apple-touch-icon" href="{up}/apple-touch-icon.png">'
            f'<meta name="theme-color" content="#142d3b">{extra}'
            f'<meta property="og:type" content="website"><meta property="og:site_name" content="{SITE_NAME}"><meta property="og:locale" content="pl_PL">'
            f'<meta property="og:title" content="{title}"><meta property="og:description" content="{desc}"><meta property="og:url" content="{url}">'
            f'<meta property="og:image" content="{SITE}theme/og/{img}.png"><meta property="og:image:width" content="1200"><meta property="og:image:height" content="630">'
            f'<meta name="twitter:card" content="summary_large_image">')
    return html.replace("</head>", f"<!--meta-->{tags}<!--/meta--></head>", 1)


def full(h):
    h = h.lower()
    return "".join(c * 2 for c in h) if len(h) == 3 else h


def var_hex(m):
    h = full(m.group(1))
    return f"var(--c-{h},#{m.group(1)})"


def convert_css(css: str) -> str:
    return VALUE.sub(lambda v: HEX.sub(var_hex, v.group(0)), css)


def convert_html(html: str) -> str:
    html = re.sub(r"(<style[^>]*>)(.*?)(</style>)", lambda m: m.group(1) + convert_css(m.group(2)) + m.group(3), html, flags=re.S)
    return re.sub(r'(style=")([^"]*)(")', lambda m: m.group(1) + convert_css(":" + m.group(2) + ";")[1:-1] + m.group(3), html)


# --- colour maths (sRGB <-> OKLab) ---
def _lin(c):
    return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4


def _gam(c):
    c = max(0.0, min(1.0, c))
    return 12.92 * c if c <= 0.0031308 else 1.055 * c ** (1 / 2.4) - 0.055


def to_oklab(h):
    r, g, b = (_lin(int(h[i:i + 2], 16) / 255) for i in (0, 2, 4))
    l_ = (0.4122214708 * r + 0.5363325363 * g + 0.0514459929 * b) ** (1 / 3)
    m_ = (0.2119034982 * r + 0.6806995451 * g + 0.1073969566 * b) ** (1 / 3)
    s_ = (0.0883024619 * r + 0.2817188376 * g + 0.6299787005 * b) ** (1 / 3)
    return (0.2104542553 * l_ + 0.7936177850 * m_ - 0.0040720468 * s_,
            1.9779984951 * l_ - 2.4285922050 * m_ + 0.4505937099 * s_,
            0.0259040371 * l_ + 0.7827717662 * m_ - 0.8086757660 * s_)


def from_oklab(L, a, b):
    l_ = (L + 0.3963377774 * a + 0.2158037573 * b) ** 3
    m_ = (L - 0.1055613458 * a - 0.0638541728 * b) ** 3
    s_ = (L - 0.0894841775 * a - 1.2914855480 * b) ** 3
    r = 4.0767416621 * l_ - 3.3077115913 * m_ + 0.2309699292 * s_
    g = -1.2684380046 * l_ + 2.6097574011 * m_ - 0.3413193965 * s_
    bb = -0.0041960863 * l_ - 0.7034186147 * m_ + 1.7076147010 * s_
    return "".join(f"{round(_gam(c) * 255):02x}" for c in (r, g, bb))


def dark(h):
    L, a, b = to_oklab(h)
    # mirror lightness into a range that keeps backgrounds dark-but-not-black and text off-white
    L2 = 0.17 + (1 - L) * 0.78 if L > 0.55 else min(0.93, 0.98 - L * 0.62)
    k = 0.75 if L > 0.55 else 1.0  # tone down tints that become backgrounds
    return from_oklab(L2, a * k, b * k)


def collect(root: Path):
    found = set()
    for p in files(root):
        found |= {m.lower() for m in re.findall(r"--c-([0-9a-f]{6})", p.read_text(encoding="utf-8", errors="ignore"))}
    return sorted(found)


def files(root: Path):
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS and not d.startswith(".")]
        for f in filenames:
            if "template" in f:
                continue  # build inputs: placeholders like @@NAV@@ must survive; outputs get themed instead
            if f.startswith("raport."):
                continue  # standalone reports (copied to the share) carry their own light/dark styles
            if (f.endswith((".html", ".css")) and f != "theme.css") or (Path(dirpath) / f).relative_to(root).as_posix() in JS_FILES:
                yield Path(dirpath) / f


def tokens():
    """Design tokens (--ink, --cream…) as defined in the stylesheets, with their light values, for the header reset."""
    out = {}
    for rel in CSS_FILES:
        p = HERE.parent / rel
        if p.exists():
            m = re.search(r":root\{([^}]*)\}", p.read_text(encoding="utf-8"))
            for k, v in re.findall(r"(--[\w-]+):([^;]+)", m.group(1) if m else ""):
                hexm = re.search(r"#([0-9a-fA-F]{3,6})\)?$", v.strip())
                if hexm and k not in out:
                    out[k] = "#" + hexm.group(1)
    return out


def theme_css(colours):
    rules = ";".join(f"--c-{h}:#{h if h in KEEP else dark(h)}" for h in colours)
    light = ";".join(f"--c-{h}:#{h}" for h in colours) + "".join(f";{k}:{v}" for k, v in tokens().items())
    extra = ("color-scheme:dark")
    return ("/* generated by theme/apply.py: dark counterparts of every colour used in the site */\n"
            f":root[data-theme=dark]{{{rules};{extra}}}\n"
            f"@media (prefers-color-scheme:dark){{:root:not([data-theme=light]){{{rules};{extra}}}}}\n"
            f"/* the header is dark in both themes: it keeps its light-theme colours */\nheader,.hero-dark{{{light}}}\n"
            ".site-nav{display:flex;align-items:center;gap:6px 22px;min-height:70px;font-size:13px;flex-wrap:wrap}"
            ".site-nav a{color:#e4eddf;min-height:44px;display:flex;align-items:center;text-decoration:none}.site-nav a:hover{text-decoration:underline}"
            ".site-nav a[aria-current=page]{color:#fff;box-shadow:inset 0 -2px 0 #a8d1ba}.site-nav .brand{font:600 16px Georgia,serif;margin-right:auto;color:#fff}"
            ".site-nav .nav-links{display:flex;flex-direction:row;flex-wrap:wrap;align-items:center;gap:6px 22px;margin:0;width:auto}"
            "@media (max-width:760px){.site-nav{gap:0;padding:4px 0 0;flex-wrap:wrap}.site-nav .brand{flex:1;width:auto}.theme-toggle{order:1}"
            ".site-nav .nav-links{order:2;width:100%;flex-wrap:nowrap;overflow-x:auto;gap:18px;padding-bottom:4px;scrollbar-width:thin;"
            "-webkit-mask-image:linear-gradient(90deg,#000 85%,transparent);mask-image:linear-gradient(90deg,#000 85%,transparent)}"
            ".site-nav .nav-links a{white-space:nowrap;min-height:40px}}\n"
            ".theme-toggle{margin-left:8px;min-height:36px;min-width:36px;padding:4px 10px;border:1px solid #41525e;border-radius:18px;"
            "background:transparent;color:#e4eddf;font:13px system-ui,sans-serif;cursor:pointer}.theme-toggle:hover{border-color:#a8d1ba}"
            ".theme-toggle:focus-visible{outline:3px solid #bc642e;outline-offset:3px}"
            "@media print{.theme-toggle,.report{display:none}}\n"
            ".site-nav .theme-toggle{width:auto;flex:0 0 auto}.theme-toggle.floating{position:fixed;top:10px;right:10px;z-index:55;background:#142d3b;margin:0}"
            ".teczka-add{background:var(--c-ffffff,#fff)!important;color:var(--c-006858,#006858)!important;border-color:var(--c-9fb7ac,#9fb7ac)!important}\n"
            ".report{font:500 12px system-ui,sans-serif;color:var(--muted,#5a666d);margin-left:10px;white-space:nowrap;text-decoration:underline dotted}"
            ".report:hover{color:var(--c-984926,#984926)}\n"
            # readability: no text below 12px; form fields at 16px on phones (iOS zooms into smaller ones)
            "small{font-size:max(12px,.8em)}code{font-size:max(12px,.9em)}.tag,a.tag,span.tag,.chip span,.eyebrow,.bar-row small,.bar-row span,.bar-row b,"
            ".references a,.provenance code,label,select,option{font-size:max(12px,1em)}.tag,a.tag,span.tag{font-size:12px}select,option{font-size:13px}\n"
            "@media (max-width:760px){select,input[type=text],input[type=search],input[type=number],textarea{font-size:16px}}\n"
            # touch: comfortable targets on touch screens only (desktop stays compact)
            "@media (pointer:coarse){a.tag,.tags a{min-height:32px;display:inline-flex;align-items:center}button.link{min-height:40px}"
            "input[type=checkbox],input[type=radio]{width:20px;height:20px}summary{min-height:40px;padding-top:8px;padding-bottom:8px}"
            ".toc a{min-height:40px;display:flex;align-items:center}}\n"
            # mobile menu (theme.js adds the button and .js-menu; without JS the links scroll sideways)
            ".nav-menu-btn{display:none}"
            "@media (max-width:760px){.site-nav.js-menu .nav-menu-btn{display:inline-flex;align-items:center;gap:6px;order:1;min-height:40px;padding:4px 12px;"
            "border:1px solid #41525e;border-radius:18px;background:transparent;color:#e4eddf;font:13px system-ui,sans-serif;cursor:pointer}"
            ".site-nav.js-menu .theme-toggle{order:1}.site-nav.js-menu .nav-links{display:none}"
            ".site-nav.js-menu.open .nav-links{display:grid;grid-template-columns:1fr 1fr;gap:0 16px;overflow:visible;-webkit-mask-image:none;mask-image:none;padding:6px 0 12px}"
            ".site-nav.js-menu.open .nav-links a{min-height:44px;border-bottom:1px solid #24404f}"
            ".nav-menu-btn:focus-visible{outline:3px solid #bc642e;outline-offset:3px}}\n"
            # page tools: table of contents and back-to-top (theme.js)
            ".page-tools{position:fixed;right:16px;bottom:16px;z-index:50;display:flex;gap:8px;align-items:flex-end;opacity:0;pointer-events:none;transition:opacity .2s}"
            ".page-tools.scrolled{opacity:1;pointer-events:auto}"
            ".pt-btn{min-height:44px;min-width:44px;padding:8px 14px;border-radius:22px;border:1px solid var(--c-41525e,#41525e);background:var(--c-142d3b,#142d3b);"
            "color:#fff;font:600 14px system-ui,sans-serif;cursor:pointer;box-shadow:0 4px 14px #0003}.pt-btn:focus-visible{outline:3px solid #bc642e;outline-offset:3px}"
            ".pt-panel{position:absolute;right:0;bottom:56px;width:min(320px,calc(100vw - 32px));max-height:min(70vh,520px);overflow:auto;background:var(--c-ffffff,#fff);"
            "color:var(--c-1d2a35,#1d2a35);border:1px solid var(--c-d9ddd6,#d9ddd6);border-radius:8px;padding:12px 14px;box-shadow:0 8px 28px #0003;font:14px/1.4 system-ui,sans-serif}"
            ".pt-panel ol{margin:6px 0 0;padding-left:20px}.pt-panel li{margin:2px 0}.pt-panel a{display:block;padding:6px 0;color:inherit;text-decoration:none}"
            ".pt-panel a:hover,.pt-panel a.on{color:var(--c-006858,#006858);text-decoration:underline}"
            "h2[id]{scroll-margin-top:16px}\n"
            # print: content only, light, links spelled out
            "@media print{.site-nav,header .site-nav,.theme-toggle,.nav-menu-btn,.page-tools,.report,.teczka-add,.skip,.controls,form[role=search],button,.k-out .actions{display:none!important}"
            ":root,:root[data-theme=dark]{color-scheme:light}body{background:#fff!important;color:#000!important;font-size:11pt}"
            "header,.hero,.hero-dark{background:#fff!important;color:#000!important}header *{color:#000!important}"
            "main,.wrap{max-width:none!important;padding:0!important}a{color:#000!important}"
            "main a[href^='http']::after{content:' (' attr(href) ')';font-size:8pt;color:#444;word-break:break-all}"
            ".box,.chart,.card,.tile,tr,figure,details{break-inside:avoid}h1,h2,h3{break-after:avoid}details{display:block}details>*{display:block}"
            "table{border-collapse:collapse}th,td{border:1px solid #999!important}.tablewrap{max-height:none!important;overflow:visible!important}}\n")


def main(root: Path) -> int:
    for rel in CSS_FILES:
        p = root / rel
        if p.exists():
            p.write_text(convert_css(p.read_text(encoding="utf-8")), encoding="utf-8")
    for rel in JS_FILES:
        p = root / rel
        if p.exists():
            p.write_text(re.sub(r"'#([0-9a-fA-F]{6})'", lambda m: f"'var(--c-{m.group(1).lower()},#{m.group(1)})'", p.read_text(encoding="utf-8")), encoding="utf-8")
    pages = 0
    for p in files(root):
        if p.suffix != ".html":
            continue
        html = p.read_text(encoding="utf-8")
        if "</head>" not in html:
            if "<body" in html:
                html = html.replace("<body", "</head><body", 1)
            elif "</style>" in html:
                html = html.replace("</style>", "</style></head><body>", 1)
            else:
                continue  # implicit head (atlas.py output): make it explicit
        up = os.path.relpath(root / "theme", p.parent).replace(os.sep, "/")
        html = convert_html(html)
        top = up[:-len("theme")]
        html = NAV_RE.sub(lambda m: site_nav(p.relative_to(root).as_posix(), top), html, count=1)
        if 'class="site-nav"' not in html and "masthead" not in html:
            html = re.sub(r"(<header[^>]*>)", lambda m: m.group(1) + site_nav(p.relative_to(root).as_posix(), top), html, count=1)
        html = head_meta(html, p.relative_to(root).as_posix(), up)
        if "theme/theme.css" not in html:
            html = html.replace("</head>", f'<link rel="stylesheet" href="{up}/theme.css"><script src="{up}/theme.js"></script></head>', 1)
        p.write_text(html, encoding="utf-8")
        pages += 1
    (root / "theme").mkdir(exist_ok=True)
    if (root / "theme") != HERE:
        (root / "theme" / "theme.js").write_text((HERE / "theme.js").read_text(encoding="utf-8"), encoding="utf-8")
    colours = collect(root)
    (root / "theme" / "theme.css").write_text(theme_css(colours), encoding="utf-8")
    print(f"theme: {pages} pages, {len(colours)} colours")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(Path(sys.argv[1]).resolve() if len(sys.argv) > 1 else HERE.parent))
