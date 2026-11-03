#!/usr/bin/env python3
"""Translation plus light structured mapping in one pass (grouped, Claude Opus 5.5).

Per section: Polish translation, one-sentence plain-language summary, normative strength
(closed list, 'niejasne' allowed) and 0-3 Polish-debate problem tags (closed list).
Pilot: same 60 sections as the plain grouped pilot -> translations-rich.jsonl.
"""
import json
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import translate as t  # noqa: E402

VOCAB = json.loads((HERE / "slowniki.json").read_text())
OUT = HERE / "translations-rich.jsonl"
NOTE = (
    "\n6. Dostajesz listę fragmentów w JSON jako [{\"id\": n, \"text\": ...}]. Każdy fragment opracuj osobno i zwróć te same id, każdy raz."
    "\n7. Dla każdego fragmentu podaj także:"
    "\n   - 'streszczenie': jedno zdanie po polsku, najwyżej 25 słów, prostym językiem dla osoby bez wykształcenia prawniczego; bez ocen i bez informacji spoza fragmentu;"
    "\n   - 'sila': jedna wartość z listy " + json.dumps(list(VOCAB["sila"]), ensure_ascii=False) +
    " (prawo_podmiotowe tylko gdy przepis przyznaje uprawnienie konkretnym osobom; cel_programowy gdy państwo 'dąży', 'wspiera', 'promuje'; niejasne gdy fragment nie wystarcza);"
    "\n   - 'problemy': od 0 do 3 kodów z listy " + json.dumps(list(VOCAB["problemy"]), ensure_ascii=False) +
    ", tylko gdy fragment wprost dotyczy danego problemu; lepiej mniej niż za dużo."
    "\n8. Najważniejszy jest wierny przekład; dodatkowe pola nie mogą wpływać na jego treść."
)
SCHEMA = {"type": "object", "properties": {"items": {"type": "array", "items": {"type": "object", "properties": {
    "id": {"type": "integer"}, "pl": {"type": "string"}, "streszczenie": {"type": "string"},
    "sila": {"type": "string", "enum": list(VOCAB["sila"])},
    "problemy": {"type": "array", "items": {"type": "string", "enum": list(VOCAB["problemy"])}}},
    "required": ["id", "pl", "streszczenie", "sila", "problemy"], "additionalProperties": False}}},
    "required": ["items"], "additionalProperties": False}


def request_params(batch):
    payload = json.dumps([{"id": k, "text": it["text"]} for k, it in enumerate(batch)], ensure_ascii=False)
    return dict(model=t.MODEL, max_tokens=16000, system=t.SYSTEM + NOTE,
                output_config={"effort": "low", "format": {"type": "json_schema", "schema": SCHEMA}},
                messages=[{"role": "user", "content": payload}])


def validate(item, out):
    problems = t.check(item["text"], out["pl"]) if out.get("pl") else ["brak przekładu"]
    words = len(out.get("streszczenie", "").split())
    if not 3 <= words <= 32:
        problems.append(f"streszczenie: {words} słów")
    if len(out.get("problemy", [])) > 3:
        problems.append("ponad 3 problemy")
    return problems


def record(item, out, model, mode, extra=None):
    return {"doc_id": item["doc_id"], "section_id": item["section_id"], "source_sha256": t.sha(item["text"]),
            "topic": item["topic"], "country_code": item["country_code"], "model": model, "mode": mode,
            "created_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "translation": out.get("pl"), "streszczenie": out.get("streszczenie"), "sila": out.get("sila"),
            "problemy": sorted(set(out.get("problemy", [])))[:3], "problems": validate(item, out) if out else ["brak w odpowiedzi"], **(extra or {})}


def pilot(group=20):
    sections = {(i["doc_id"], i["section_id"]): i for i in t.sections()}
    plain = [json.loads(l) for l in t.OUT.open(encoding="utf-8")]
    picked = [sections[(r["doc_id"], r["section_id"])] for r in plain if r.get("mode") == "group20"]
    api = t.client()
    usage = {"input": 0, "output": 0}
    with OUT.open("a", encoding="utf-8") as fh:
        for start in range(0, len(picked), group):
            batch = picked[start:start + group]
            resp = api.beta.messages.create(betas=["server-side-fallback-2026-07-01"], fallbacks="default", **request_params(batch))
            usage["input"] += resp.usage.input_tokens
            usage["output"] += resp.usage.output_tokens
            outs = {} if resp.stop_reason in ("refusal", "max_tokens") else {
                i["id"]: i for i in json.loads(next(b.text for b in resp.content if b.type == "text"))["items"]}
            for k, item in enumerate(batch):
                fh.write(json.dumps(record(item, outs.get(k, {}), resp.model, f"rich{group}"), ensure_ascii=False) + "\n")
            print(f"group {start // group + 1}: {len(outs)}/{len(batch)} stop={resp.stop_reason} in={resp.usage.input_tokens} out={resp.usage.output_tokens}", flush=True)
    chars = sum(len(i["text"]) for i in picked)
    total = sum(len(i["text"]) for i in sections.values())
    cost = usage["input"] / 1e6 * 4 + usage["output"] / 1e6 * 20
    print(json.dumps({"usage": usage, "pilot_usd": round(cost, 3), "full_run_batch_usd": round(cost * total / chars / 2)}))




# ---------- full run via Message Batches API ----------
MANIFEST = HERE / "batch_manifest.json"
MAX_GROUP_CHARS = 9000
BUDGET_USD = 150  # pre-committed ceiling for the full run (pilot estimate: ~121 USD)


def pending_groups(group=20):
    have = set()
    if OUT.exists():
        have = {(r["doc_id"], r["section_id"], r["source_sha256"]) for r in map(json.loads, OUT.open(encoding="utf-8")) if r.get("translation")}
    items = [i for i in t.sections() if (i["doc_id"], i["section_id"], t.sha(i["text"])) not in have]
    items.sort(key=lambda i: i["doc_id"])  # stable: keeps document order from ccp_sections.csv
    groups, cur, size = [], [], 0
    for it in items:  # at most `group` sections and MAX_GROUP_CHARS characters per request
        if cur and (len(cur) >= group or size + len(it["text"]) > MAX_GROUP_CHARS):
            groups.append(cur)
            cur, size = [], 0
        cur.append(it)
        size += len(it["text"])
    if cur:
        groups.append(cur)
    return groups


def submit(group=20):
    from anthropic.types.message_create_params import MessageCreateParamsNonStreaming
    from anthropic.types.messages.batch_create_params import Request
    groups = pending_groups(group)
    chars = sum(len(i["text"]) for g in groups for i in g)
    est = 121 * chars / sum(len(i["text"]) for i in t.sections())
    print(json.dumps({"groups": len(groups), "sections": sum(map(len, groups)), "estimate_usd": round(est, 1)}))
    if est > BUDGET_USD:
        raise SystemExit(f"estimate {est:.0f} USD exceeds budget {BUDGET_USD} USD")
    api = t.client()
    requests, manifest = [], {}
    for n, g in enumerate(groups):
        cid = f"g{n:05d}"
        manifest[cid] = [[i["doc_id"], i["section_id"], t.sha(i["text"])] for i in g]
        requests.append(Request(custom_id=cid, params=MessageCreateParamsNonStreaming(**request_params(g))))
    batch = api.messages.batches.create(requests=requests)
    MANIFEST.write_text(json.dumps({"batch_id": batch.id, "created_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
                                    "group": group, "groups": manifest}, indent=0))
    print(json.dumps({"batch_id": batch.id, "status": batch.processing_status}))


def status():
    api = t.client()
    m = json.loads(MANIFEST.read_text())
    b = api.messages.batches.retrieve(m["batch_id"])
    print(json.dumps({"batch_id": b.id, "status": b.processing_status, "counts": b.request_counts.to_dict()}))
    return b.processing_status


def collect():
    api = t.client()
    m = json.loads(MANIFEST.read_text())
    sections = {(i["doc_id"], i["section_id"]): i for i in t.sections()}
    usage = {"input": 0, "output": 0}
    failed, written = [], 0
    with OUT.open("a", encoding="utf-8") as fh:
        for res in api.messages.batches.results(m["batch_id"]):
            keys = m["groups"][res.custom_id]
            if res.result.type != "succeeded" or res.result.message.stop_reason in ("refusal", "max_tokens"):
                failed.append(res.custom_id)
                continue
            msg = res.result.message
            usage["input"] += msg.usage.input_tokens
            usage["output"] += msg.usage.output_tokens
            try:
                outs = {i["id"]: i for i in json.loads(next(b.text for b in msg.content if b.type == "text"))["items"]}
            except (StopIteration, ValueError, KeyError):
                failed.append(res.custom_id)
                continue
            for k, (doc, sec, h) in enumerate(keys):
                item = sections.get((doc, sec))
                if item is None or t.sha(item["text"]) != h:
                    continue
                fh.write(json.dumps(record(item, outs.get(k, {}), msg.model, f"batch{m['group']}", {"batch": m["batch_id"], "custom_id": res.custom_id}), ensure_ascii=False) + "\n")
                written += 1
    cost = (usage["input"] / 1e6 * 4 + usage["output"] / 1e6 * 20) / 2
    print(json.dumps({"written": written, "failed_groups": failed, "usage": usage, "cost_usd": round(cost, 2)}))




def retry():
    """Re-translate, one section per call, every section whose latest translation is missing or fails checks."""
    import store
    sections = {(i["doc_id"], i["section_id"]): i for i in t.sections()}
    latest = store.load({k: v["text"] for k, v in sections.items()})
    todo = [i for k, i in sections.items() if k not in latest or not latest[k]["usable"] or t.check(i["text"], latest[k]["translation"])]
    api = t.client()
    usage = {"input": 0, "output": 0}
    fixed = 0
    with OUT.open("a", encoding="utf-8") as fh:
        for n, item in enumerate(todo, 1):
            resp = api.beta.messages.create(betas=["server-side-fallback-2026-07-01"], fallbacks="default", **request_params([item]))
            usage["input"] += resp.usage.input_tokens
            usage["output"] += resp.usage.output_tokens
            outs = {} if resp.stop_reason in ("refusal", "max_tokens") else {
                i["id"]: i for i in json.loads(next(b.text for b in resp.content if b.type == "text"))["items"]}
            rec = record(item, outs.get(0, {}), resp.model, "retry1")
            fixed += not rec["problems"]
            fh.write(json.dumps(rec, ensure_ascii=False) + "\n")
            print(f"{n}/{len(todo)} {item['country_code']} {rec['problems']}", flush=True)
    print(json.dumps({"retried": len(todo), "clean": fixed, "usage": usage,
                      "cost_usd": round(usage["input"] / 1e6 * 4 + usage["output"] / 1e6 * 20, 2)}))


if __name__ == "__main__":
    if len(sys.argv) == 1:
        pilot()
    else:
        {"submit": submit, "status": status, "collect": collect, "retry": retry}[sys.argv[1]]()
