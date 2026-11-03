"""Read-only access to machine translations for page builders (no API dependency).

load(texts) -> {(doc_id, section_id): record} keeping only records whose source hash matches the
current text. Rich records (summary, normative strength, problem tags) win over plain ones.
A record with a failed numbers check is returned with 'usable': False so pages show the original.
"""
from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
FILES = [HERE / "translations.jsonl", HERE / "translations-rich.jsonl"]  # later files win
VOCAB = json.loads((HERE / "slowniki.json").read_text())
sys.path.insert(0, str(HERE))
from translate import check  # noqa: E402  (no API import at module level)


def _sha(text: str) -> str:
    return hashlib.sha256(text.encode()).hexdigest()


def load(texts: dict) -> dict:
    """texts: {(doc_id, section_id): current source text}."""
    out = {}
    for path in FILES:
        if not path.exists():
            continue
        with path.open(encoding="utf-8") as fh:
            for line in fh:
                r = json.loads(line)
                key = (r["doc_id"], r["section_id"])
                src = texts.get(key)
                if not r.get("translation") or src is None or _sha(src) != r["source_sha256"]:
                    continue
                prev = out.get(key)
                if prev and prev.get("streszczenie") and not r.get("streszczenie"):
                    continue
                current = check(src, r["translation"])  # re-evaluate with the current checks
                r["problems"] = current + [p for p in r.get("problems", []) if p.startswith("streszczenie")]
                r["usable"] = not any(p.startswith(("liczby", "pozostałości")) for p in current)
                out[key] = r
    return out
