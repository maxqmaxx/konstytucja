#!/usr/bin/env python3
"""Build the full-text index (SQLite FTS5) over all extracted constitution texts.

One row per paragraph chunk with its starting line number. Diacritics are folded
(unicode61 remove_diacritics 2); there is no stemming, use a trailing * for prefixes.
Output: analysis/szukaj/fts.sqlite (rebuildable, not versioned). No network.
Run from the project root: nice taskset -c 0,1 python3 analysis/szukaj/index.py
"""
from __future__ import annotations

import json
import os
import sqlite3
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(HERE.parent / "panstwa"))
from build import name_pl  # noqa: E402

MAX_CHUNK = 1200
MIN_CHUNK = 120


def chunks(text: str):
    """Yield (start_line, chunk) from blank-line paragraphs, splitting long ones by line."""
    buf, start = [], None
    size = 0
    for number, line in enumerate(text.splitlines(), 1):
        stripped = line.strip()
        if not stripped:
            if size >= MIN_CHUNK:
                yield start, " ".join(buf)
                buf, start, size = [], None, 0
            continue
        if start is None:
            start = number
        buf.append(stripped)
        size += len(stripped) + 1
        if size >= MAX_CHUNK:
            yield start, " ".join(buf)
            buf, start, size = [], None, 0
    if buf:
        yield start, " ".join(buf)


def main() -> int:
    target = HERE / "fts.sqlite"
    tmp = HERE / "fts.sqlite.part"
    if tmp.exists():
        tmp.unlink()
    db = sqlite3.connect(tmp)
    db.executescript("""
        PRAGMA journal_mode=OFF; PRAGMA synchronous=OFF;
        CREATE TABLE docs(id TEXT, country_code TEXT, country TEXT, title TEXT, language TEXT, provider TEXT,
                          status TEXT, year TEXT, text_path TEXT, original TEXT);
        CREATE VIRTUAL TABLE chunks USING fts5(body, doc UNINDEXED, line UNINDEXED,
                          tokenize = 'unicode61 remove_diacritics 2');
    """)
    started = time.time()
    n_docs = n_chunks = 0
    with open(ROOT / "catalog.jsonl", encoding="utf-8") as fh:
        for raw in fh:
            rec = json.loads(raw)
            text = rec.get("text")
            if not text or not (ROOT / text["path"]).exists():
                continue
            original = next((a["path"] for a in rec.get("assets") or [] if a["path"].endswith(".pdf")),
                            next((a["path"] for a in rec.get("assets") or []), ""))
            cur = db.execute("INSERT INTO docs VALUES (?,?,?,?,?,?,?,?,?,?)", (
                rec["id"], rec["country_code"], name_pl(rec["country_code"], rec["country"]), rec["title"],
                rec["language"], rec["provider"], rec["status"], str(rec.get("year_enacted") or ""), text["path"], original))
            doc = cur.lastrowid
            body = (ROOT / text["path"]).read_text(encoding="utf-8", errors="replace")
            rows = [(c, doc, line) for line, c in chunks(body)]
            db.executemany("INSERT INTO chunks(body, doc, line) VALUES (?,?,?)", rows)
            n_docs += 1
            n_chunks += len(rows)
    db.execute("INSERT INTO chunks(chunks) VALUES('optimize')")
    db.commit()
    db.execute("VACUUM")
    db.close()
    os.replace(tmp, target)
    info = {"documents": n_docs, "chunks": n_chunks, "bytes": target.stat().st_size, "seconds": round(time.time() - started)}
    (HERE / "index-info.json").write_text(json.dumps(info, indent=1) + "\n")
    print(json.dumps(info))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
