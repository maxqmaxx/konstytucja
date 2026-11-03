#!/usr/bin/env python3
"""Machine-translate CCP-tagged constitutional provisions (EN -> PL), with code-side checks.

Usage (from the project root, inside .venv):
  .venv/bin/python analysis/tlumaczenia/translate.py pilot --n 50      # synchronous sample
  .venv/bin/python analysis/tlumaczenia/translate.py report            # checks + samples for review

Output: translations.jsonl, one record per (doc_id, section_id, source_sha256), with model,
time and check results. A changed source text invalidates its old translation (new hash).
Translations are unofficial and must be labelled as machine translations wherever shown.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
import random
import re
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
ANALYSIS = HERE.parent
sys.path.insert(0, str(ANALYSIS / "features"))
import ccp_data  # noqa: E402

OUT = HERE / "translations.jsonl"
MODEL = "claude-opus-5-5"
SYSTEM = (
    "Tłumaczysz przepisy konstytucji z angielskiego na polski dla polskich prawników i obywateli.\n"
    "Zasady:\n"
    "1. Tłumacz wiernie i w całości. Niczego nie dodawaj, nie streszczaj i nie komentuj.\n"
    "2. Używaj polskiej terminologii konstytucyjnej (np. 'ustawa' dla 'law/act of parliament' gdy chodzi o akt parlamentu, "
    "'Rzecznik Praw Obywatelskich' tylko gdy tekst dotyczy Polski; obce instytucje opisowo lub w oryginalnej nazwie).\n"
    "3. Zachowaj numerację, odesłania do artykułów, liczby, daty i nazwy własne.\n"
    "4. Jeśli tekst jest urwany, przetłumacz to, co jest, i nie dopowiadaj reszty.\n"
    "5. Zwróć wyłącznie przekład, bez cudzysłowów i wstępów."
)


def sha(text: str) -> str:
    return hashlib.sha256(text.encode()).hexdigest()


def numbers(text: str):
    """Numbers with thousand separators removed ("1,000" / "1 000" / "1.000" -> "1000")."""
    text = re.sub(r"(?<=\d)[,\u00a0 .](?=\d{3}\b)", "", text)
    return sorted(re.findall(r"\d+", text))


def check(src: str, dst: str) -> list[str]:
    problems = []
    from collections import Counter
    missing = Counter(numbers(src)) - Counter(numbers(dst))  # extra digits in PL are fine (ordinal words -> digits)
    if missing:
        problems.append("liczby różnią się od oryginału: brak " + ", ".join(sorted(missing)))
    ratio = len(dst) / max(1, len(src))
    if len(src) >= 80 and not 0.6 <= ratio <= 1.8:
        problems.append(f"nietypowy stosunek długości {ratio:.2f}")
    if re.search(r"\b(the|shall|and|of)\b", dst) and len(re.findall(r"\b(the|shall)\b", dst)) >= 3:
        problems.append("pozostałości angielskiego")
    return problems


def sections():
    ccp = ccp_data.load()
    seen, items = set(), []
    with open(ANALYSIS / "features/ccp_sections.csv", encoding="utf-8") as fh:
        for row in csv.DictReader(fh):
            doc = ccp.docs.get(row["doc_id"])
            if not doc or doc["country_code"] == "PL" or not row["text"].strip():
                continue
            key = (row["doc_id"], row["section_id"])
            if key in seen:
                continue
            seen.add(key)
            items.append({"doc_id": row["doc_id"], "section_id": row["section_id"], "country_code": doc["country_code"],
                          "topic": row["topic"], "text": row["text"]})
    return items


def done():
    if not OUT.exists():
        return set()
    return {(r["doc_id"], r["section_id"], r["source_sha256"]) for r in map(json.loads, OUT.open(encoding="utf-8"))}


def client():
    import anthropic
    key = os.environ.get("ANTHROPIC_API_KEY") or Path.home() / ".anthropic_key".read_text().strip()
    return anthropic.Anthropic(api_key=key, max_retries=4)


def translate_one(api, text: str):
    response = api.beta.messages.create(
        model=MODEL, max_tokens=8000, system=SYSTEM,
        output_config={"effort": "low"},
        betas=["server-side-fallback-2026-07-01"], fallbacks="default",
        messages=[{"role": "user", "content": text}],
    )
    if response.stop_reason == "refusal":
        return None, response
    out = "".join(b.text for b in response.content if b.type == "text").strip()
    return out, response


def pilot(n: int, seed: int):
    items = sections()
    rnd = random.Random(seed)
    priority = {"unamend", "hosterml", "em", "water", "amparo", "referen", "jc", "cappun", "env", "infoacc"}
    picked = rnd.sample([i for i in items if i["topic"] in priority], min(n // 2, 1000))
    rest = [i for i in items if i not in picked]
    picked += rnd.sample(rest, n - len(picked))
    have = done()
    api = client()
    usage = {"input": 0, "output": 0}
    with OUT.open("a", encoding="utf-8") as fh:
        for i, item in enumerate(picked, 1):
            key = (item["doc_id"], item["section_id"], sha(item["text"]))
            if key in have:
                continue
            started = time.time()
            text, resp = translate_one(api, item["text"])
            usage["input"] += resp.usage.input_tokens
            usage["output"] += resp.usage.output_tokens
            rec = {"doc_id": item["doc_id"], "section_id": item["section_id"], "source_sha256": key[2],
                   "topic": item["topic"], "country_code": item["country_code"], "model": resp.model,
                   "created_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
                   "translation": text, "refused": text is None,
                   "problems": check(item["text"], text) if text else ["odmowa"],
                   "request_id": getattr(resp, "_request_id", None), "seconds": round(time.time() - started, 1)}
            fh.write(json.dumps(rec, ensure_ascii=False) + "\n")
            fh.flush()
            print(f"{i}/{len(picked)} {item['country_code']} {item['topic']} problems={rec['problems']}", flush=True)
    cost = usage["input"] / 1e6 * 4 + usage["output"] / 1e6 * 20
    print(json.dumps({"translated": len(picked), "usage": usage, "cost_usd_est": round(cost, 3)}))


SCHEMA = {"type": "object", "properties": {"items": {"type": "array", "items": {"type": "object",
          "properties": {"id": {"type": "integer"}, "pl": {"type": "string"}}, "required": ["id", "pl"], "additionalProperties": False}}},
          "required": ["items"], "additionalProperties": False}
GROUP_NOTE = ("\n6. Dostajesz listę fragmentów w JSON jako [{\"id\": n, \"text\": ...}]. Każdy fragment tłumacz osobno; "
              "zwróć dokładnie te same id, każdy fragment raz.")


def translate_group(api, batch):
    payload = json.dumps([{"id": k, "text": it["text"]} for k, it in enumerate(batch)], ensure_ascii=False)
    response = api.beta.messages.create(
        model=MODEL, max_tokens=16000, system=SYSTEM + GROUP_NOTE,
        output_config={"effort": "low", "format": {"type": "json_schema", "schema": SCHEMA}},
        betas=["server-side-fallback-2026-07-01"], fallbacks="default",
        messages=[{"role": "user", "content": payload}],
    )
    if response.stop_reason in ("refusal", "max_tokens"):
        return {}, response
    data = json.loads(next(b.text for b in response.content if b.type == "text"))
    return {it["id"]: it["pl"].strip() for it in data["items"]}, response


def pilot_grouped(n: int, group: int, seed: int):
    have = {(d, s) for d, s, _ in done()}
    items = [i for i in sections() if (i["doc_id"], i["section_id"]) not in have]
    picked = random.Random(seed).sample(items, n)
    api = client()
    usage = {"input": 0, "output": 0}
    with OUT.open("a", encoding="utf-8") as fh:
        for start in range(0, len(picked), group):
            batch = picked[start:start + group]
            t0 = time.time()
            out, resp = translate_group(api, batch)
            usage["input"] += resp.usage.input_tokens
            usage["output"] += resp.usage.output_tokens
            for k, item in enumerate(batch):
                text = out.get(k)
                rec = {"doc_id": item["doc_id"], "section_id": item["section_id"], "source_sha256": sha(item["text"]),
                       "topic": item["topic"], "country_code": item["country_code"], "model": resp.model, "mode": f"group{group}",
                       "created_at": datetime.now(timezone.utc).isoformat(timespec="seconds"), "translation": text,
                       "refused": resp.stop_reason == "refusal", "problems": check(item["text"], text) if text else [f"brak w odpowiedzi ({resp.stop_reason})"],
                       "request_id": getattr(resp, "_request_id", None), "seconds": round(time.time() - t0, 1)}
                fh.write(json.dumps(rec, ensure_ascii=False) + "\n")
            print(f"group {start // group + 1}: {len(out)}/{len(batch)} stop={resp.stop_reason} in={resp.usage.input_tokens} out={resp.usage.output_tokens}", flush=True)
    chars = sum(len(i["text"]) for i in picked)
    print(json.dumps({"translated": len(picked), "chars": chars, "usage": usage,
                      "cost_usd_est": round(usage["input"] / 1e6 * 4 + usage["output"] / 1e6 * 20, 3)}))


def report(k: int):
    items = {(i["doc_id"], i["section_id"]): i for i in sections()}
    recs = [json.loads(l) for l in OUT.open(encoding="utf-8")]
    flagged = [r for r in recs if r["problems"]]
    print(json.dumps({"records": len(recs), "flagged": len(flagged), "problems": [r["problems"] for r in flagged]}, ensure_ascii=False))
    for r in recs[:k]:
        src = items[(r["doc_id"], r["section_id"])]["text"]
        print(f"\n=== {r['country_code']} · {r['topic']} · {r['doc_id']} {r['section_id']}\nEN: {src[:600]}\nPL: {(r['translation'] or '')[:700]}")


def main():
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("pilot"); p.add_argument("--n", type=int, default=50); p.add_argument("--seed", type=int, default=7)
    r = sub.add_parser("report"); r.add_argument("--k", type=int, default=6)
    g = sub.add_parser("pilot-grouped"); g.add_argument("--n", type=int, default=60); g.add_argument("--group", type=int, default=20); g.add_argument("--seed", type=int, default=11)
    sub.add_parser("estimate")
    a = ap.parse_args()
    if a.cmd == "pilot":
        pilot(a.n, a.seed)
    elif a.cmd == "pilot-grouped":
        pilot_grouped(a.n, a.group, a.seed)
    elif a.cmd == "report":
        report(a.k)
    else:
        items = sections()
        chars = sum(len(i["text"]) for i in items)
        print(json.dumps({"sections": len(items), "chars": chars, "pending": len(items) - len(done())}))


if __name__ == "__main__":
    main()
