"""World-comparison fragments for the Polish view (prevalence of CCP topics, art. 235 path)."""

import csv
import json
from html import escape
from pathlib import Path

FEATURES = Path(__file__).resolve().parent.parent / "features"
CHAPTERS = [(1, 29, "I"), (30, 86, "II"), (87, 94, "III"), (95, 125, "IV"), (126, 145, "V"), (146, 162, "VI"),
            (163, 172, "VII"), (173, 201, "VIII"), (202, 215, "IX"), (216, 227, "X"), (228, 234, "XI"), (235, 243, "XII")]
REFERENDUM_CHAPTERS = {"I", "II", "XII"}
RARE_KEPT = ["hogdlim", "judcrts5", "scifree", "medcom", "conlim", "corppun", "conright", "partunco"]
VERDICT_PL = {
    "luka": "brak w Konstytucji RP (sprawdzone)",
    "luka_celowa": "brak, rozwiązanie celowe (sprawdzone)",
    "inna_technika": "ujęte ogólną klauzulą, nie wprost",
    "czesciowo": "częściowo",
    "artefakt": "jest, choć CCP nie oznaczył",
    "nie_dotyczy": "nie dotyczy",
}


def load():
    evidence = json.loads((FEATURES / "proposals_evidence.json").read_text())
    labels = json.loads((FEATURES / "topic_labels_pl.json").read_text())
    review = {r["topic"]: r for r in csv.DictReader(open(FEATURES / "poland_gap_review.csv", encoding="utf-8"))}
    prevalence = {r["topic"]: r for r in csv.DictReader(open(FEATURES / "prevalence.csv", encoding="utf-8"))}
    return evidence, labels, review, prevalence


def chapter(article):
    for lo, hi, name in CHAPTERS:
        if lo <= article <= hi:
            return name
    raise ValueError(article)


def poland_state(topic, row, review):
    if row["poland"] == "1":
        return "tak", f'tak ({escape(row["poland_articles"].replace("Article", "art."))})'
    rev = review.get(topic)
    if rev is None:
        return "nieznane", "brak tagu CCP, niesprawdzone ręcznie"
    state = "tak" if rev["verdict"] == "artefakt" else "czesc" if rev["verdict"] in ("inna_technika", "czesciowo") else "nie"
    basis = f' ({escape(rev["polish_basis"])})' if rev["polish_basis"] else ""
    return state, f'{VERDICT_PL[rev["verdict"]]}{basis}'


def bars(row):
    out = []
    for key, label, total in (("share", "świat", "188"), ("share_2000plus", "od 2000 r.", "49"), ("share_eu27", "UE-27", "27")):
        share = float(row[key])
        count = row[{"share": "count", "share_2000plus": "count_2000plus", "share_eu27": "count_eu27"}[key]]
        out.append(f'<div class="bar-row"><span>{label}</span><span class="bar"><i style="width:{share * 100:.1f}%"></i></span>'
                   f'<b>{share:.0%}</b><small>{count}/{total}</small></div>')
    return "".join(out)


def card_block(pid, evidence, labels, review):
    items = evidence["proposals"].get(pid)
    if not items:
        note = evidence["unmapped"].get(pid, "Brak odpowiadającego tematu CCP.")
        return f'<div class="world"><h3>Na tle świata</h3><p class="world-note">{escape(note)} Rozpowszechnienia nie mierzymy.</p></div>'
    parts = []
    for item in items:
        state, text = poland_state(item["topic"], item, review)
        proxy = ' <span class="proxy" title="Temat CCP jest szerszy niż propozycja; odsetek to górna granica.">temat szerszy</span>' if item["match"] == "proxy" else ""
        examples = ", ".join(item["examples"][:5])
        parts.append(f'<div class="world-item"><p class="world-topic"><a href="../tematy/{item["topic"]}.html">{escape(labels[item["topic"]])}</a>{proxy}</p>{bars(item)}'
                     f'<p class="pl-state {state}">Polska: {text}</p><p class="world-examples">Np. {escape(examples)}</p></div>')
    return f'<div class="world"><h3>Na tle świata <span>188 obowiązujących konstytucji, kodowanie CCP</span></h3>{"".join(parts)}</div>'


def path_block(proposal):
    if proposal["level"] == "ustawa":
        return ('<p class="path"><b>Ścieżka:</b> najpierw ustawa, zwykła większość. Zmiana konstytucji dopiero, '
                'gdy rozwiązanie sprawdzi się w praktyce.</p>')
    chapters = sorted({chapter(a) for a in proposal["polish_articles"]}, key=lambda c: [x[2] for x in CHAPTERS].index(c))
    referendum = REFERENDUM_CHAPTERS & set(chapters)
    text = ("<b>Ścieżka (art. 235):</b> 2/3 głosów w Sejmie przy obecności co najmniej połowy posłów i bezwzględna większość w Senacie. "
            f"Dotyczy rozdz. {', '.join(chapters)}.")
    if referendum:
        text += (f" Zmiana rozdz. {', '.join(sorted(referendum))} pozwala Prezydentowi, Senatowi lub 1/5 posłów zażądać "
                 "referendum zatwierdzającego, a głosowanie w Sejmie odbywa się najwcześniej 60. dnia po pierwszym czytaniu.")
    return f'<p class="path">{text}</p>'


def overview(labels, review, prevalence):
    gaps = [(t, prevalence[t]) for t, r in review.items() if r["verdict"] == "luka"]
    gaps.sort(key=lambda x: -float(x[1]["share_eu27"]))
    gap_rows = "".join(
        f'<tr><th scope="row"><a href="../tematy/{t}.html">{escape(labels[t])}</a></th><td>{float(p["share"]):.0%}</td><td>{float(p["share_2000plus"]):.0%}</td>'
        f'<td>{p["count_eu27"]}/27</td><td>{escape(review[t]["note"])}</td></tr>' for t, p in gaps)
    rare = "".join(
        f'<li><b>{escape(labels[t])}</b> ({escape(prevalence[t]["poland_articles"].replace("Article", "art."))}): '
        f'{prevalence[t]["count"]} ze 188 konstytucji, {prevalence[t]["count_eu27"]} w UE.</li>' for t in RARE_KEPT)
    artefacts = ", ".join(f'{escape(labels.get(t, t)[0].lower() + labels.get(t, t)[1:])} ({escape(r["polish_basis"])})' for t, r in review.items()
                          if r["verdict"] == "artefakt" and t in labels) or "barwy narodowe (art. 28), zakaz wstecznego karania (art. 42)"
    return f'''<section class="world-overview" id="na-tle-swiata" aria-labelledby="world-title"><div class="section-title"><p class="eyebrow">Polska na tle świata</p><h2 id="world-title">Czego brakuje, a co mamy rzadkiego</h2><p>Porównanie z 188 obowiązującymi konstytucjami w kodowaniu Comparative Constitutions Project (wydania angielskie Constitute, jedna na państwo). Każdą lukę Polski sprawdzono ręcznie w tekście Konstytucji RP.</p></div>
<div class="table-scroll"><table class="gap-table"><caption>Rozwiązania nieobecne w Konstytucji RP, uporządkowane według częstości w UE</caption><thead><tr><th scope="col">Rozwiązanie</th><th scope="col">Świat</th><th scope="col">Od 2000 r.</th><th scope="col">UE-27</th><th scope="col">Stan w Polsce</th></tr></thead><tbody>{gap_rows}</tbody></table></div>
<div class="rare"><h3>Rzadkie rozwiązania, które Polska już ma</h3><ul>{rare}</ul></div>
<p class="world-note">Brak tagu CCP nie dowodzi braku przepisu. Część pozornych luk to różnice kodowania, m.in. {artefacts}; inne wynikają z ogólnego zakazu dyskryminacji w art. 32 zamiast wyliczenia kryteriów. Częstość nie jest dowodem skuteczności rozwiązania. <a href="../features/prevalence.csv">Pełna tabela 331 tematów (CSV)</a> · <a href="../features/poland_gap_review.csv">Przegląd luk (CSV)</a></p></section>'''
