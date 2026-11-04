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
CURRENT = {"mapa": "mapa", "rp": "rp", "problemy": "problemy", "tematy": "tematy", "konstruktor": "konstruktor", "statystyki": "statystyki",
           "panstwa": "panstwa", "polska": "polska", "wizualizacje": "wizualizacje", "ATLAS.html": "atlas"}
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
            ".report:hover{color:var(--c-984926,#984926)}\n")


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
