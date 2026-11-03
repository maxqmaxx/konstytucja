"""Read-only full-text search over fts.sqlite, used by deploy/serve.py (/api/szukaj)."""
from __future__ import annotations

import re
import sqlite3
import time
from pathlib import Path

DB = Path(__file__).resolve().parent / "fts.sqlite"
MAX_QUERY = 200
MAX_TERMS = 8
TIME_LIMIT = 3.0  # seconds per query
START, END = "\x02", "\x03"


class QueryError(ValueError):
    pass


def fts_query(raw: str) -> str:
    """Turn user input into a safe FTS5 expression: AND of quoted terms/phrases, trailing * = prefix."""
    raw = (raw or "").strip()[:MAX_QUERY]
    parts = re.findall(r'"([^"]+)"|(\S+)', raw)
    terms = []
    for phrase, word in parts:
        if phrase:
            words = re.findall(r"\w+", phrase)
            if words:
                terms.append('"' + " ".join(words) + '"')
        else:
            prefix = word.endswith("*")
            words = re.findall(r"\w+", word)
            if not words:
                continue
            token = '"' + " ".join(words) + '"'
            terms.append(token + ("*" if prefix and len(words) == 1 and len(words[0]) >= 3 else ""))
    if not terms:
        raise QueryError("Wpisz co najmniej jedno słowo.")
    if len(terms) > MAX_TERMS:
        raise QueryError(f"Najwyżej {MAX_TERMS} słów lub fraz.")
    return " ".join(terms)


def connect(path: Path = DB) -> sqlite3.Connection:
    if not path.exists():
        raise FileNotFoundError(path)
    db = sqlite3.connect(f"file:{path}?mode=ro&immutable=1", uri=True, check_same_thread=False)
    db.row_factory = sqlite3.Row
    return db


def search(params: dict, path: Path = DB) -> dict:
    q = fts_query(params.get("q", ""))
    filters, args = [], [q]
    for key, column in (("lang", "language"), ("kraj", "country_code"), ("status", "status")):
        value = (params.get(key) or "").strip()
        if value:
            if not re.fullmatch(r"[A-Za-z_-]{2,40}", value):
                raise QueryError(f"Niepoprawny filtr: {key}")
            filters.append(f"d.{column} = ?")
            args.append(value)
    where = "chunks MATCH ?" + "".join(f" AND {f}" for f in filters)
    db = connect(path)
    deadline = time.monotonic() + TIME_LIMIT
    db.set_progress_handler(lambda: 1 if time.monotonic() > deadline else 0, 20000)
    try:
        rows = db.execute(
            f"""SELECT c.doc, c.line, snippet(chunks, 0, '{START}', '{END}', ' … ', 28) AS snip,
                       d.id, d.country_code, d.country, d.title, d.language, d.provider, d.status, d.year, d.text_path, d.original
                FROM chunks c JOIN docs d ON d.rowid = c.doc WHERE {where} ORDER BY bm25(chunks) LIMIT 400""", args).fetchall()
        total = db.execute(f"SELECT count(*), count(DISTINCT c.doc) FROM chunks c JOIN docs d ON d.rowid = c.doc WHERE {where}", args).fetchone()
    except sqlite3.OperationalError as exc:
        if "interrupted" in str(exc):
            raise QueryError("Zapytanie trwało zbyt długo. Zawęź je filtrem lub dłuższą frazą.") from exc
        raise QueryError("Nie udało się zinterpretować zapytania.") from exc
    finally:
        db.close()
    docs, order = {}, []
    for r in rows:
        if r["doc"] not in docs:
            if len(order) >= 40:
                continue
            docs[r["doc"]] = {k: r[k] for k in ("id", "country_code", "country", "title", "language", "provider", "status", "year", "text_path", "original")}
            docs[r["doc"]]["hits"] = []
            order.append(r["doc"])
        if len(docs[r["doc"]]["hits"]) < 3:
            docs[r["doc"]]["hits"].append({"line": r["line"], "snippet": r["snip"]})
    return {"query": q, "matching_passages": total[0], "matching_documents": total[1],
            "shown_documents": len(order), "results": [docs[d] for d in order], "marks": [START, END]}
