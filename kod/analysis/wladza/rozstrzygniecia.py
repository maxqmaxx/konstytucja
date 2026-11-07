#!/usr/bin/env python3
"""Adjudicate disagreements between our readings and the CCP expert coding (walidacja_roznice.json).

For each disagreement the model gets the question in OUR definition, a wider excerpt of the constitution (our excerpt
for the topic plus keyword-matched articles) and answers in our vocabulary with a verbatim quote. It is not told which
answer is ours or CCP's. Where the verdict differs from our value and the quote is found in the text, `apply` writes a
correction to ../warianty/korekty.json marked "metoda": "rozstrzygniecie" (not a manual review).

  .venv/bin/python analysis/wladza/rozstrzygniecia.py submit | status | collect [results.jsonl] | apply
"""
from __future__ import annotations

import json
import re
import sys
from collections import Counter
from datetime import date
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "warianty"))
import extract as ex  # noqa: E402
import load as variants  # noqa: E402

OUT = HERE / "rozstrzygniecia.jsonl"
DIFFS = HERE / "rozstrzygniecia_roznice.json"  # the disagreements as they were when adjudicated (frozen by submit)
MANIFEST = HERE / "rozstrzygniecia_batch.json"
MAX_CHARS = 30000
YN = ["tak", "nie", "nie_wynika"]
# pole -> question, answers, topic, field, how to apply, keywords
Q = {
    "Parlament może odwołać rząd": dict(
        q="Can the legislature (or one of its chambers) remove the head of government or the cabinet by a vote of no confidence, censure or a similar political vote? Impeachment for crimes does not count.",
        a=YN, topic="cabdiss", field="kto_odwoluje", item="parlament", kw=r"no.confidence|censure|confidence|dismiss|remov"),
    "Głowa państwa może odwołać rząd": dict(
        q="Can the head of state dismiss the head of government or the whole cabinet on his or her own decision? Answer 'nie' if the head of state only formally accepts a resignation, acts after a parliamentary vote, or acts on the head of government's proposal. Where the head of state is also the head of the executive, answer whether he or she can dismiss the ministers.",
        a=YN, topic="cabdiss", field="kto_odwoluje", item="glowa_panstwa", kw=r"dismiss|remov|relieve|terminat"),
    "Rząd ma inicjatywę ustawodawczą": dict(
        q="Can the government, cabinet or head of government (or, where the head of state heads the executive, the head of state) introduce bills in the legislature?",
        a=YN, topic="legini", field="kto_ma", item="rzad", kw=r"introduc|initiative|submit.{0,20}bill|bills? may be"),
    "Głowa państwa może zawetować ustawę": dict(
        q="What can the head of state do with a bill passed by the legislature? 'weto': refuse assent, veto or return it for reconsideration; 'tylko_sad': only refer it to a court; 'formalny_podpis': must sign or promulgate.",
        a=["weto", "tylko_sad", "formalny_podpis", "nie_wynika"], topic="legapp", field="glowa_panstwa_ustawy", kw=r"assent|veto|return|promulgat|reconsider"),
    "Głowa państwa kieruje rządem": dict(
        q="Who heads the government? 'odrebny_premier': a separate head of government (prime minister, chancellor, premier) distinct from the head of state; 'glowa_panstwa': the head of state heads the government or the cabinet (no separate prime minister, or the prime minister only coordinates under the president).",
        a=["odrebny_premier", "glowa_panstwa", "nie_wynika"], topic="hogelect", field="szef_rzadu", kw=r"prime minister|head of (the )?government|chancellor|premier|executive power"),
    "Zmiana konstytucji wymaga większości kwalifikowanej": dict(
        q="What majority of the legislature is required to adopt a constitutional amendment in the standard procedure? 'zwykla_lub_bezwzgledna': simple or absolute majority; otherwise the qualified fraction.",
        a=["zwykla_lub_bezwzgledna", "trzy_piate", "dwie_trzecie", "trzy_czwarte", "inny", "nie_wynika"], topic="amend", field="prog_parlament", kw=r"amend"),
    "Głowa państwa wybiera sędziów TK": dict(
        q="Does the head of state select, nominate or appoint (some of) the judges of the constitutional court or constitutional council? A purely formal appointment of persons chosen by another body counts as 'nie'.",
        a=YN, topic="consel", field="kto_wybiera", item="glowa_panstwa", kw=r"constitutional (court|council|tribunal)"),
    "Parlament wybiera sędziów TK": dict(
        q="Does the legislature (or one of its chambers) elect, nominate or confirm (some of) the judges of the constitutional court or constitutional council?",
        a=YN, topic="consel", field="kto_wybiera", item="parlament", kw=r"constitutional (court|council|tribunal)"),
    "Głowa państwa może rozwiązać parlament": dict(
        q="Can the head of state dissolve the legislature (or its lower chamber), alone or in specified situations?",
        a=YN, topic="legdiss", field="kto_moze", item="glowa_panstwa", kw=r"dissol"),
    "Liczba izb": dict(q="How many chambers does the national legislature have?", a=["jedna", "dwie", "nie_wynika"], topic="legapp", field="izby",
                       kw=r"senate|chamber|house of|national assembly|parliament (shall )?consist"),
    "Kto ogłasza stan nadzwyczajny": dict(
        q="Who declares a state of emergency (or siege, martial law)? Choose the actor that makes the declaration.",
        a=["glowa_panstwa", "rzad", "parlament", "inne", "nie_wynika"], topic="em", field="kto_oglasza", kw=r"emergency|siege|martial law|state of (war|exception|defen)"),
    "Próg odrzucenia weta": dict(
        q="What majority does the legislature need to override the head of state's veto of an ordinary bill?",
        a=["zwykla_lub_bezwzgledna", "trzy_piate", "dwie_trzecie", "inny", "weto_ostateczne", "nie_wynika"], topic="override", field="prog_odrzucenia", kw=r"veto|reconsider|return|assent"),
}
# verdicts rejected on review: (pole, country) -> reason
REJECT = {("Głowa państwa może odwołać rząd", "IR"): "art. 110 ust. 10: Najwyższy Przywódca (głowa państwa) może odwołać Prezydenta (szefa rządu); werdykt „nie” pominięto"}
SYSTEM = ("You answer one question about a national constitution using only the excerpt. Do not use outside knowledge. "
          "If the excerpt does not settle the question, answer 'nie_wynika'. 'cytat': copy verbatim (exact characters) the shortest passage "
          "(max 300 characters) that decides your answer. 'artykul': the article label containing it.")


def items():
    if not DIFFS.exists():
        DIFFS.write_text((HERE / "walidacja_roznice.json").read_text(), encoding="utf-8")
    diffs = json.loads(DIFFS.read_text())
    units = {(u["topic"], u["country_code"]): u for u in ex.all_units()}
    arts = {d["country_code"]: d for d in ex.articles().values()}
    out = []
    for k, d in enumerate(diffs):
        spec = Q.get(d["pole"])
        if not spec or d["kod"] not in arts:
            continue
        doc = arts[d["kod"]]
        parts = [units[(spec["topic"], d["kod"])]["text"]] if (spec["topic"], d["kod"]) in units else []
        for a, t in doc["articles"]:
            if re.search(spec["kw"], t, re.I) and sum(map(len, parts)) < MAX_CHARS:
                chunk = f"{a}: {t}"
                if not any(t[:200] in p for p in parts):
                    parts.append(chunk[:6000])
        out.append({"id": f"r{k:04d}", "pole": d["pole"], "kod": d["kod"], "text": "\n\n".join(parts)[:MAX_CHARS]})
    return out


def params(it):
    spec = Q[it["pole"]]
    schema = {"type": "object", "properties": {"odpowiedz": {"type": "string", "enum": spec["a"]}, "cytat": {"type": "string"}, "artykul": {"type": "string"}},
              "required": ["odpowiedz", "cytat", "artykul"], "additionalProperties": False}
    return dict(model=ex.t.MODEL, max_tokens=2000, system=SYSTEM,
                output_config={"effort": "medium", "format": {"type": "json_schema", "schema": schema}},
                messages=[{"role": "user", "content": f"Question: {spec['q']}\nAllowed answers: {', '.join(spec['a'])}\n\nExcerpt:\n{it['text']}"}])


def submit():
    from anthropic.types.message_create_params import MessageCreateParamsNonStreaming
    from anthropic.types.messages.batch_create_params import Request
    its = items()
    est = sum(len(i["text"]) for i in its) / 4 / 1e6 * 2 + len(its) * 500 / 1e6 * 10
    print(json.dumps({"items": len(its), "by_field": Counter(i["pole"] for i in its), "estimate_usd": round(est, 2)}, ensure_ascii=False))
    if est > 15:
        raise SystemExit("over budget")
    b = ex.t.client().messages.batches.create(requests=[Request(custom_id=i["id"], params=MessageCreateParamsNonStreaming(**params(i))) for i in its])
    MANIFEST.write_text(json.dumps({"batch_id": b.id, "items": {i["id"]: {k: i[k] for k in ("pole", "kod")} for i in its}}, ensure_ascii=False))
    print(b.id)


def status():
    m = json.loads(MANIFEST.read_text())
    b = ex.t.client().messages.batches.retrieve(m["batch_id"])
    print(b.processing_status, b.request_counts.to_dict())


def collect():
    m = json.loads(MANIFEST.read_text())
    texts = {i["id"]: i["text"] for i in items()}
    n = 0
    src = sys.argv[2] if len(sys.argv) > 2 else None  # optional downloaded results .jsonl (streaming can fail)
    if src:
        results = [json.loads(line) for line in open(src, encoding="utf-8")]
        get = lambda r: (r["custom_id"], r["result"]["type"], next((c["text"] for c in r["result"].get("message", {}).get("content", []) if c["type"] == "text"), None))  # noqa: E731
    else:
        results = ex.t.client().messages.batches.results(m["batch_id"])
        get = lambda r: (r.custom_id, r.result.type, next((c.text for c in r.result.message.content if c.type == "text"), None) if r.result.type == "succeeded" else None)  # noqa: E731
    with OUT.open("w", encoding="utf-8") as fh:
        for r in results:
            cid, typ, txt = get(r)
            meta = m["items"][cid]
            if typ != "succeeded" or not txt:
                continue
            o = json.loads(txt)
            o.update(meta, id=cid, cytat_ok=bool(o["cytat"]) and ex.norm(o["cytat"]) in ex.norm(texts[cid]))
            fh.write(json.dumps(o, ensure_ascii=False) + "\n")
            n += 1
    print(n)


def apply():
    path = HERE.parent / "warianty" / "korekty.json"
    K = [k for k in json.loads(path.read_text()) if k.get("metoda") != "rozstrzygniecie"]  # re-applying replaces earlier adjudications
    path.write_text(json.dumps(K, ensure_ascii=False, indent=1) + "\n")  # so that the values below are the readings before adjudication
    R = variants.load()
    diffs = {(d["pole"], d["kod"]): d for d in json.loads(DIFFS.read_text())}
    manual = {(k["topic"], k["country_code"], k["field"]) for k in K}
    stats, new = Counter(), []
    for o in map(json.loads, OUT.open(encoding="utf-8")):
        spec, d = Q[o["pole"]], diffs.get((o["pole"], o["kod"]))
        if d is None:
            continue
        if (o["pole"], o["kod"]) in REJECT:
            stats["odrzucone_po_przegladzie"] += 1
            continue
        verdict = o["odpowiedz"]
        if not o["cytat_ok"] or verdict == "nie_wynika":
            stats["nierozstrzygniete"] += 1
            continue
        rec = R.get((spec["topic"], o["kod"]))
        cur = rec["values"].get(spec["field"]) if rec else None
        if "item" in spec:
            has = spec["item"] in (cur or [])
            want = verdict == "tak"
            if has == want:
                stats["potwierdza_nasze"] += 1
                continue
            value = sorted(set(cur or []) | {spec["item"]}) if want else [x for x in (cur or []) if x != spec["item"]]
        else:
            if verdict == cur:
                stats["potwierdza_nasze"] += 1
                continue
            value = verdict
        if rec is None or (spec["topic"], o["kod"], spec["field"]) in manual:
            stats["pominiete"] += 1
            continue
        stats["poprawka"] += 1
        new.append({"topic": spec["topic"], "country_code": o["kod"], "field": spec["field"], "value": value,
                    "basis": f"rozstrzygnięcie rozbieżności z kodowaniem CCP ({o['pole'].lower()}): „{o['cytat'][:240]}” ({o['artykul']})",
                    "reviewed": date.today().isoformat(), "metoda": "rozstrzygniecie"})
    path.write_text(json.dumps(K + new, ensure_ascii=False, indent=1) + "\n")
    print(json.dumps(stats))


if __name__ == "__main__":
    {"submit": submit, "status": status, "collect": collect, "apply": apply}[sys.argv[1]]()
