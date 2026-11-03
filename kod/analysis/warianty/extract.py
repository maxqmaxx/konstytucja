#!/usr/bin/env python3
"""Extract structured variants (facets.json) per country x topic from CCP-tagged provisions, with verbatim-quote checks.

  .venv/bin/python analysis/warianty/extract.py pilot hosterml em     # synchronous, selected topics
  .venv/bin/python analysis/warianty/extract.py submit                # Batches API, all remaining topics
  .venv/bin/python analysis/warianty/extract.py status | collect | summary

Output: warianty.jsonl (one record per country x topic). Values come only from the excerpt;
'nie_wynika'/null when not stated. A record is shown only if its quote is found verbatim in the source.
"""
from __future__ import annotations

import csv
import json
import re
import sys
import time
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
A = HERE.parent
sys.path.insert(0, str(A / "features"))
sys.path.insert(0, str(A / "tlumaczenia"))
import ccp_data  # noqa: E402
import translate as t  # noqa: E402  (client, MODEL)

SPEC = {k: v for k, v in json.loads((HERE / "facets.json").read_text()).items() if not k.startswith("_")}
OUT = HERE / "warianty.jsonl"
MANIFEST = HERE / "batch_manifest.json"
GROUP = 8
MAX_CHARS = 12000
BUDGET_USD = 40
SYSTEM = (
    "You read excerpts of national constitutions and fill a fixed schema. Rules:\n"
    "1. Use only the excerpt. Do not use outside knowledge about the country.\n"
    "2. If the excerpt does not state something, answer 'nie_wynika' (or null for numbers, [] for lists). Prefer 'nie_wynika' to guessing.\n"
    "3. 'cytat': copy verbatim (exact characters) the shortest passage of the excerpt (max 300 characters) that best supports your main answer. Do not translate or paraphrase it.\n"
    "4. Numbers: days for durations of emergencies (convert months to days: 1 month = 30), years for terms, absolute counts for signatures.\n"
    "5. Return every id exactly once."
)


def norm(s: str) -> str:
    return re.sub(r"\s+", " ", s or "").strip().lower()


def schema_for(topic):
    props = {"id": {"type": "integer"}, "cytat": {"type": "string"}}
    for name, f in SPEC[topic]["fields"].items():
        if f["type"] == "enum":
            props[name] = {"type": "string", "enum": list(f["values"])}
        elif f["type"] == "multi":
            props[name] = {"type": "array", "items": {"type": "string", "enum": list(f["values"])}}
        elif f["type"] == "int":
            props[name] = {"type": ["integer", "null"]}
        else:
            props[name] = {"type": "string", "enum": ["tak", "nie", "nie_wynika"]}
    return {"type": "object", "properties": {"items": {"type": "array", "items": {"type": "object", "properties": props,
            "required": list(props), "additionalProperties": False}}}, "required": ["items"], "additionalProperties": False}


def field_guide(topic):
    lines = [f"Topic: {SPEC[topic]['title']}"]
    for name, f in SPEC[topic]["fields"].items():
        vals = "; ".join(f"{k} = {v}" for k, v in f.get("values", {}).items()) if f.get("values") else {"int": "integer or null", "bool3": "tak / nie / nie_wynika"}[f["type"]]
        lines.append(f"- {name} ({f['label']}): {vals}")
    return "\n".join(lines)


ART_NUM = re.compile(r"^(?:article|art\.?|section)\s+(\d+[a-z]?)\b", re.I)
REF_RE = re.compile(r"\b(?:articles?|art\.|sections?)\s+((?:\d+[a-z]?)(?:\s*(?:,|and|or|to|-)\s*\d+[a-z]?)*)", re.I)
MAX_REFS, REF_CHARS, KW_ARTICLES = 4, 1500, 3


def articles():
    """Per in-force constitution: articles in document order (label, text) and topic -> tagged passages (article, text). Cached."""
    import ccp_topics
    cache = HERE / "articles_cache.json"
    if cache.exists():
        return json.loads(cache.read_text())
    ccp = ccp_data.load()
    out = {}
    for doc_id, doc in sorted(ccp.docs.items()):
        rows = ccp_topics.parse(A.parent / doc["html"], limit=None, include_untagged=True)
        arts, tagged = {}, defaultdict(list)
        for r in rows:
            # every section's own text (tagged or not), so an article is complete whatever topics it carries
            if r["text"] and not any(r["text"] in t for t in arts.setdefault(r["article"], [])):
                arts[r["article"]].append(r["text"])
            if r["topic"] is not None:
                tagged[r["topic"]].append([r["article"], r["text"]])
        out[doc_id] = {"country_code": doc["country_code"], "articles": [[a, "\n".join(t)] for a, t in arts.items()], "tagged": tagged}
    cache.write_text(json.dumps(out, ensure_ascii=False))
    return out


def kw_match(groups, text):
    """Number of hits if every OR-group matches, else 0."""
    hits = 0
    for g in groups:
        n = sum(len(re.findall(rx, text, re.I)) for rx in g)
        if not n:
            return 0
        hits += n
    return hits


def expand_refs(text, by_num, have):
    """Append the text of articles the excerpt refers to ("Articles 1 and 20"), so cross-references can be resolved."""
    extra = []
    for m in REF_RE.finditer(text):
        for num in re.findall(r"\d+[a-z]?", m.group(1), re.I):
            label = by_num.get(num.lower())
            if label and label not in have and len(extra) < MAX_REFS:
                have.add(label)
                extra.append(f"[Referenced {label}] {by_num[num.lower()+'#text'][:REF_CHARS]}")
    return extra


def units():
    """Per topic x in-force constitution: tagged passages plus their full articles (CCP often tags only the heading of an
    enumeration), plus articles the text refers to. Where CCP did not tag the topic, up to three articles found by keywords."""
    cache = HERE / "units_cache.json"
    if cache.exists():
        return json.loads(cache.read_text())
    out = []
    for doc_id, d in sorted(articles().items()):
        arts = dict((a, t) for a, t in d["articles"])
        by_num = {}
        for a, t in d["articles"]:
            m = ART_NUM.match(a)
            if m and m.group(1).lower() not in by_num:
                by_num[m.group(1).lower()] = a
                by_num[m.group(1).lower() + "#text"] = t
        for topic, spec in SPEC.items():
            parts, labels = [], []
            if topic in d["tagged"]:
                source = "tag"
                for a, t in d["tagged"][topic]:
                    for chunk in [t, arts.get(a, "")]:
                        if chunk.strip() and not any(chunk in p for p in parts):
                            parts.append(chunk)
                    if a not in labels:
                        labels.append(a)
            else:
                source = "slowa"
                scored = sorted(((kw_match(spec.get("keywords", []), f"{a} {t}"), i, a) for i, (a, t) in enumerate(d["articles"]) if t.strip()), reverse=True)
                for score, _, a in sorted([x for x in scored if x[0] > 0][:KW_ARTICLES], key=lambda x: x[1]):
                    parts.append(f"{a}: {arts[a]}")
                    labels.append(a)
            if not parts:
                continue
            body = "\n\n".join(parts)[:MAX_CHARS - 2000]
            refs = expand_refs(body, by_num, set(labels))
            text = "\n\n".join([body] + refs)[:MAX_CHARS]
            out.append({"topic": topic, "country_code": d["country_code"], "doc_id": doc_id, "source": source, "articles": labels, "text": text})
    cache.write_text(json.dumps(out, ensure_ascii=False))
    return out


def params(batch):
    topic = batch[0]["topic"]
    payload = json.dumps([{"id": k, "country_excerpt": u["text"]} for k, u in enumerate(batch)], ensure_ascii=False)
    return dict(model=t.MODEL, max_tokens=16000, system=SYSTEM + "\n\n" + field_guide(topic),
                output_config={"effort": "low", "format": {"type": "json_schema", "schema": schema_for(topic)}},
                messages=[{"role": "user", "content": payload}])


def records(batch, outs, model, mode):
    recs = []
    for k, u in enumerate(batch):
        o = outs.get(k)
        values = {n: o.get(n) for n in SPEC[u["topic"]]["fields"]} if o else {}
        quote = (o or {}).get("cytat", "")
        recs.append({"topic": u["topic"], "country_code": u["country_code"], "doc_id": u["doc_id"], "source": u.get("source", "tag"), "articles": u.get("articles", []), "values": values, "cytat": quote,
                     "cytat_ok": bool(quote) and norm(quote) in norm(u["text"]), "model": model, "mode": mode,
                     "created_at": datetime.now(timezone.utc).isoformat(timespec="seconds"), "ok": bool(o)})
    return recs


def groups(topics=None):
    done = set()
    if OUT.exists():
        done = {(r["topic"], r["doc_id"]) for r in map(json.loads, OUT.open(encoding="utf-8")) if r["ok"]}
    by_topic = defaultdict(list)
    for u in units():
        if (not topics or u["topic"] in topics) and (u["topic"], u["doc_id"]) not in done:
            by_topic[u["topic"]].append(u)
    return [us[i:i + GROUP] for us in by_topic.values() for i in range(0, len(us), GROUP)]


def pilot(topics):
    api = t.client()
    usage = Counter()
    with OUT.open("a", encoding="utf-8") as fh:
        for g in groups(topics):
            resp = api.beta.messages.create(betas=["server-side-fallback-2026-07-01"], fallbacks="default", **params(g))
            usage["in"] += resp.usage.input_tokens
            usage["out"] += resp.usage.output_tokens
            outs = {} if resp.stop_reason in ("refusal", "max_tokens") else {
                o["id"]: o for o in json.loads(next(b.text for b in resp.content if b.type == "text"))["items"]}
            for r in records(g, outs, resp.model, "pilot"):
                fh.write(json.dumps(r, ensure_ascii=False) + "\n")
            print(f"{g[0]['topic']} {len(outs)}/{len(g)} stop={resp.stop_reason}", flush=True)
    print(json.dumps({"usage": usage, "cost_usd": round(usage["in"] / 1e6 * 4 + usage["out"] / 1e6 * 20, 2)}))


def submit():
    from anthropic.types.message_create_params import MessageCreateParamsNonStreaming
    from anthropic.types.messages.batch_create_params import Request
    gs = groups()
    est = sum(len(u["text"]) for g in gs for u in g) / 4 / 1e6 * 2 + len(gs) * 3000 / 1e6 * 10
    print(json.dumps({"groups": len(gs), "units": sum(map(len, gs)), "estimate_usd": round(est, 1)}))
    if est > BUDGET_USD:
        raise SystemExit("over budget")
    api = t.client()
    manifest = {f"w{n:04d}": [[u["topic"], u["doc_id"]] for u in g] for n, g in enumerate(gs)}
    batch = api.messages.batches.create(requests=[Request(custom_id=c, params=MessageCreateParamsNonStreaming(**params(g)))
                                                  for c, g in zip(manifest, gs)])
    MANIFEST.write_text(json.dumps({"batch_id": batch.id, "groups": manifest}))
    print(json.dumps({"batch_id": batch.id}))


def status():
    m = json.loads(MANIFEST.read_text())
    b = t.client().messages.batches.retrieve(m["batch_id"])
    print(json.dumps({"status": b.processing_status, "counts": b.request_counts.to_dict()}))


def collect():
    m = json.loads(MANIFEST.read_text())
    by_key = {(u["topic"], u["doc_id"]): u for u in units()}
    usage, failed, n = Counter(), [], 0
    with OUT.open("a", encoding="utf-8") as fh:
        for res in t.client().messages.batches.results(m["batch_id"]):
            batch = [by_key[tuple(k)] for k in m["groups"][res.custom_id]]
            if res.result.type != "succeeded" or res.result.message.stop_reason in ("refusal", "max_tokens"):
                failed.append(res.custom_id)
                continue
            msg = res.result.message
            usage["in"] += msg.usage.input_tokens
            usage["out"] += msg.usage.output_tokens
            outs = {o["id"]: o for o in json.loads(next(b.text for b in msg.content if b.type == "text"))["items"]}
            for r in records(batch, outs, msg.model, "batch"):
                fh.write(json.dumps(r, ensure_ascii=False) + "\n")
                n += 1
    print(json.dumps({"written": n, "failed": failed, "cost_usd": round((usage["in"] / 1e6 * 4 + usage["out"] / 1e6 * 20) / 2, 2)}))


def latest():
    out = {}
    if OUT.exists():
        for r in map(json.loads, OUT.open(encoding="utf-8")):
            if r["ok"]:
                out[(r["topic"], r["country_code"])] = r
    return out


def summary(topics=None):
    L = latest()
    for topic in topics or SPEC:
        recs = [r for (tp, _), r in L.items() if tp == topic]
        if not recs:
            continue
        ok = [r for r in recs if r["cytat_ok"]]
        print(f"\n== {SPEC[topic]['title']} ({topic}): {len(recs)} państw, cytat zgodny {len(ok)}")
        for name, f in SPEC[topic]["fields"].items():
            vals = Counter()
            for r in ok:
                v = r["values"].get(name)
                for x in (v if isinstance(v, list) else [v]):
                    vals[str(x)] += 1
            print(f"  {f['label']}: {dict(vals.most_common(8))}")
        pl = L.get((topic, "PL"))
        if pl:
            print(f"  POLSKA: {pl['values']} | cytat_ok={pl['cytat_ok']} | {pl['cytat'][:160]}")


if __name__ == "__main__":
    cmd, args = sys.argv[1], sys.argv[2:]
    {"pilot": lambda: pilot(args), "submit": submit, "status": status, "collect": collect, "summary": lambda: summary(args or None)}[cmd]()
