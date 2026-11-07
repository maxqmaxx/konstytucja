#!/usr/bin/env python3
"""Konstruktor: pick variants for the 23 key topics and see which constitutions share your set, how it differs
from the Polish Constitution, and which combinations deserve a second thought. Static page, no server.

Data: analysis/warianty (records with a verified quote, plus documented corrections). No provision text is embedded.
Usage: python3 analysis/konstruktor/build.py
"""
from __future__ import annotations

import json
import sys
from collections import Counter
from html import escape
from pathlib import Path

HERE = Path(__file__).resolve().parent
A = HERE.parent
sys.path.insert(0, str(A / "features"))
sys.path.insert(0, str(A / "panstwa"))
sys.path.insert(0, str(A / "warianty"))
import ccp_data  # noqa: E402
import load as warianty_load  # noqa: E402
from build import page, name_pl  # noqa: E402

EU27 = {"AT", "BE", "BG", "HR", "CY", "CZ", "DK", "EE", "FI", "FR", "DE", "GR", "HU", "IE", "IT",
        "LV", "LT", "LU", "MT", "NL", "PL", "PT", "RO", "SK", "SI", "ES", "SE"}
DATA_DATE = "2026-11-07"
GROUPS = [("Głowa państwa", ["hosterml", "hosterm", "override", "hosdec", "hosdiss"]),
          ("Parlament i rząd", ["lhselect", "legapp", "legini", "hogelect", "cabdiss", "legdiss", "hogdlim", "hospow", "immunity"]),
          ("Sądy i prokuratura", ["consel", "conterm", "conlim", "conpow", "jc", "jrem", "atgen"]),
          ("Zmiana konstytucji", ["amend", "unamend"]),
          ("Obywatele", ["referen", "initiat", "ombuds", "infoacc", "citrev"]),
          ("Wybory, partie, przejrzystość", ["ecom", "partprh", "camppubf", "assets"]),
          ("Prawa i wartości", ["health", "water", "env", "privacy", "offrel"]),
          ("Państwo w świecie i obronność", ["intorgs", "treatcon", "treat", "war", "milrest", "milserv"]),
          ("Kryzys, finanse, majątek", ["em", "budget", "balbudgt", "bank", "transfer", "resrce"])]

CSS = """
.k-layout{display:grid;grid-template-columns:minmax(0,1.15fr) minmax(0,1fr);gap:28px;align-items:start}
.k-form h2{margin-top:26px}.k-topic{background:var(--c-ffffff,#fff);border:1px solid var(--line);padding:4px 16px 12px;margin:10px 0}
.k-topic>summary{cursor:pointer;font:600 17px/1.3 Georgia,serif;padding:10px 0;list-style-position:outside}
.k-topic>summary small{font:400 12px system-ui,sans-serif;color:var(--muted);margin-left:6px}
.k-topic[data-active]>summary::after{content:" ●";color:var(--green)}
.k-field{margin:10px 0 4px}.k-field>span{display:block;font-size:13px;font-weight:650;margin-bottom:4px}
.k-field select,.k-field input[type=number]{width:100%;min-height:40px;border:1px solid var(--c-c8d1c6,#c8d1c6);background:var(--c-ffffff,#fff);padding:6px 8px;border-radius:4px}
.k-field .nums{display:flex;gap:8px;align-items:center}.k-field .nums input{max-width:120px}
.k-field .checks{display:flex;flex-wrap:wrap;gap:4px 14px;font-size:14px}.k-field .checks label{display:flex;gap:6px;align-items:center;min-height:32px}
.k-hint{font-size:12px;color:var(--muted);margin:3px 0 0}.k-hint b{color:var(--ink)}
.k-out{position:sticky;top:12px;max-height:calc(100vh - 24px);overflow:auto;background:var(--c-ffffff,#fff);border:1px solid var(--line);border-top:4px solid var(--green);padding:14px 18px}
.k-out h2{margin:14px 0 6px;font-size:19px}.k-out h2:first-child{margin-top:0}
.k-actions{display:flex;flex-wrap:wrap;gap:8px;margin:8px 0 4px}.k-actions button{min-height:40px;padding:6px 12px;border:1px solid var(--c-9fb7ac,#9fb7ac);background:var(--c-ffffff,#fff);color:var(--green);border-radius:4px;font:600 13px system-ui,sans-serif;cursor:pointer}
.k-actions button.primary{background:var(--green);color:var(--c-ffffff,#fff);border-color:var(--green)}
.k-list{list-style:none;padding:0;margin:6px 0}.k-list li{padding:6px 0;border-bottom:1px solid var(--line);font-size:14px}
.k-sim{display:grid;grid-template-columns:minmax(0,1fr) 110px;gap:4px 10px;align-items:center}
.k-bar{height:8px;background:var(--c-eef1ea,#eef1ea);border-radius:4px;overflow:hidden;display:flex;gap:2px}.k-bar i{display:block;background:var(--green);border-radius:4px}.k-bar i.no{background:var(--c-c49260,#c49260)}
.k-sim small{grid-column:1/-1;color:var(--muted);font-size:12px}
.k-tension{border-left:3px solid var(--c-c49260,#c49260);background:var(--c-fbf4e6,#fbf4e6);padding:8px 10px;margin:8px 0;font-size:14px}
.k-diff .same{color:var(--muted)}.k-diff b{font-weight:650}
.k-filters{display:flex;gap:14px;font-size:13px;margin:4px 0}.k-filters label{display:flex;gap:6px;align-items:center}
.k-empty{color:var(--muted);font-size:14px}.k-filters[hidden]{display:none}
.k-jump{display:none}
@media (max-width:900px){.k-layout{grid-template-columns:1fr}.k-out{position:static;max-height:none}
.k-jump{display:block;position:fixed;left:16px;bottom:16px;z-index:40;background:var(--green);color:var(--c-ffffff,#fff);padding:10px 14px;border-radius:22px;font:600 14px system-ui,sans-serif;text-decoration:none;box-shadow:0 4px 14px #0003}}
"""

JS = r"""
(() => {
const D = JSON.parse(document.getElementById('k-data').textContent);
const $ = s => document.querySelector(s), $$ = s => [...document.querySelectorAll(s)];
const T = Object.fromEntries(D.topics.map(t => [t.key, t]));
const F = {}; D.topics.forEach(t => t.fields.forEach(f => F[t.key + '.' + f.key] = { ...f, topic: t.key, ttitle: t.title }));
const label = (id, v) => { const f = F[id]; if (v == null) return '—'; if (f.type === 'int') return Array.isArray(v) ? (v[0] === v[1] ? String(v[0]) : `${v[0] ?? '…'}–${v[1] ?? '…'}`) : String(v);
  const m = Object.fromEntries(f.values); return Array.isArray(v) ? v.map(x => m[x] || x).join(', ') : (m[v] || v); };
let choice = {};

function read() {
  choice = {};
  $$('[data-id]').forEach(el => {
    const id = el.dataset.id, f = F[id];
    if (f.type === 'multi') { const v = [...el.querySelectorAll('input:checked')].map(i => i.value); if (v.length) choice[id] = v; }
    else if (f.type === 'int') { const [a, b] = [...el.querySelectorAll('input')].map(i => i.value === '' ? null : +i.value); if (a != null || b != null) choice[id] = [a, b]; }
    else { const v = el.querySelector('select').value; if (v) choice[id] = v; }
  });
}
function write() {
  $$('[data-id]').forEach(el => {
    const id = el.dataset.id, f = F[id], v = choice[id];
    if (f.type === 'multi') el.querySelectorAll('input').forEach(i => i.checked = !!v && v.includes(i.value));
    else if (f.type === 'int') { const ins = el.querySelectorAll('input'); ins[0].value = v ? (v[0] ?? '') : ''; ins[1].value = v ? (v[1] ?? '') : ''; }
    else el.querySelector('select').value = v || '';
    if (v !== undefined) el.closest('details').open = true;
  });
}
function test(id, cv, v) {
  const f = F[id];
  if (cv === undefined) return null;
  if (f.type === 'multi') return v.every(x => cv.includes(x));
  if (f.type === 'int') return (v[0] == null || cv >= v[0]) && (v[1] == null || cv <= v[1]);
  return cv === v;
}
const val = (cc, id) => { const [t, k] = id.split('.'); const c = D.countries[cc]; return c && c.v[t] ? c.v[t][k] : undefined; };
function tensions() {
  const c = id => choice[id], has = (id, x) => Array.isArray(choice[id]) && choice[id].includes(x);
  return D.tensions.filter(t => { try { return new Function('c', 'has', 'return ' + t.when)(c, has); } catch { return false; } });
}
function hash() {
  const p = new URLSearchParams();
  Object.entries(choice).forEach(([id, v]) => p.set(id, Array.isArray(v) ? (F[id].type === 'int' ? `${v[0] ?? ''}-${v[1] ?? ''}` : v.join(',')) : v));
  return p.toString();
}
function fromHash() {
  choice = {};
  try { new URLSearchParams(location.hash.slice(1)).forEach((v, id) => { const f = F[id]; if (!f) return;
    if (f.type === 'multi') choice[id] = v.split(',').filter(Boolean);
    else if (f.type === 'int') { const [a, b] = v.split('-'); choice[id] = [a === '' ? null : +a, b === '' ? null : +b]; }
    else choice[id] = v; }); } catch { /* ignore */ }
}
function render() {
  const ids = Object.keys(choice);
  $$('.k-topic').forEach(d => { if (ids.some(id => id.startsWith(d.dataset.topic + '.'))) d.dataset.active = ''; else delete d.dataset.active; });
  try { history.replaceState(null, '', ids.length ? '#' + hash() : location.pathname); } catch { /* file:// */ }
  $('#k-count').textContent = ids.length ? `Wybrano ${ids.length} ${ids.length === 1 ? 'rozwiązanie' : ids.length < 5 ? 'rozwiązania' : 'rozwiązań'}.` : 'Nic jeszcze nie wybrano.';
  $('#k-jump').textContent = `Wynik (${ids.length}) ↓`;
  const out = $('#k-result');
  if (!ids.length) { out.innerHTML = '<p class="k-empty">Wybierz odpowiedzi w dowolnych tematach albo zacznij od obecnej Konstytucji RP i zmieniaj pojedyncze rozwiązania.</p>'; return; }
  // choices with world counts and difference to Poland
  const rows = ids.map(id => {
    const v = choice[id]; let n = 0, known = 0;
    Object.keys(D.countries).forEach(cc => { if (cc === 'PL') return; const r = test(id, val(cc, id), v); if (r !== null) { known++; if (r) n++; } });
    const pv = val('PL', id), pr = test(id, pv, v);
    const pl = pr === null ? '<span>RP: nie reguluje lub nie ustalono</span>' : pr ? '<span class="same">jak w Konstytucji RP</span>' : `<b>zmiana; RP: ${esc(label(id, pv))}</b>`;
    return `<li><a href="../tematy/${F[id].topic}.html">${esc(F[id].ttitle)}</a>: ${esc(F[id].label)} = <b>${esc(label(id, v))}</b><br><small>${n} z ${known} konstytucji, w których to ustalono · ${pl}</small></li>`;
  });
  const onlyEu = $('#k-eu').checked, recent = $('#k-recent').checked;
  const sims = Object.entries(D.countries).filter(([cc, c]) => cc !== 'PL' && (!onlyEu || c.eu) && (!recent || c.y >= 2000)).map(([cc, c]) => {
    let yes = 0, no = 0; ids.forEach(id => { const r = test(id, val(cc, id), choice[id]); if (r === true) yes++; else if (r === false) no++; });
    return { cc, c, yes, no, unk: ids.length - yes - no };
  }).filter(s => s.yes + s.no > 0).sort((a, b) => (b.yes - b.no) - (a.yes - a.no) || b.yes - a.yes || a.c.n.localeCompare(b.c.n, 'pl')).slice(0, 15);
  const plS = (() => { let yes = 0, no = 0; ids.forEach(id => { const r = test(id, val('PL', id), choice[id]); if (r === true) yes++; else if (r === false) no++; }); return { yes, no }; })();
  const simHtml = sims.map(s => `<li class="k-sim"><a href="../panstwa/${s.cc.toLowerCase()}.html">${esc(s.c.n)}</a><span class="k-bar" title="zgodne ${s.yes}, niezgodne ${s.no}"><i style="width:${s.yes / ids.length * 100}%"></i><i class="no" style="width:${s.no / ids.length * 100}%"></i></span><small>zgodne ${s.yes} · niezgodne ${s.no} · brak danych ${s.unk}${s.c.eu ? ' · UE' : ''}${s.c.y ? ' · ' + s.c.y : ''}</small></li>`).join('');
  const ts = tensions();
  out.innerHTML = `<h2>Najbliższe konstytucje</h2><div class="k-filters"><label><input type="checkbox" id="k-eu2" ${onlyEu ? 'checked' : ''}> tylko UE</label><label><input type="checkbox" id="k-recent2" ${recent ? 'checked' : ''}> uchwalone od 2000 r.</label></div>
<p class="note">Konstytucja RP: zgodne ${plS.yes}, niezgodne ${plS.no}. Brak danych znaczy, że tekst tego nie określa albo temat nie został odczytany.</p>
<ol class="k-list">${simHtml || '<li class="k-empty">Brak państw z danymi dla tych wyborów.</li>'}</ol>
<h2>Do przemyślenia</h2>${ts.length ? ts.map(t => `<div class="k-tension"><b>${esc(t.title)}</b><br>${esc(t.text)}</div>`).join('') : '<p class="k-empty">Nie widać znanych napięć między wybranymi rozwiązaniami. To krótka lista typowych problemów, nie pełna analiza.</p>'}
<h2>Twój zestaw i Konstytucja RP</h2><ul class="k-list k-diff">${rows.join('')}</ul>`;
  $('#k-eu2').addEventListener('change', e => { $('#k-eu').checked = e.target.checked; render(); });
  $('#k-recent2').addEventListener('change', e => { $('#k-recent').checked = e.target.checked; render(); });
}
const esc = v => String(v ?? '').replace(/[&<>"']/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));
function fromPoland() {
  choice = {};
  Object.keys(F).forEach(id => { const v = val('PL', id); if (v === undefined) return; choice[id] = F[id].type === 'int' ? [v, v] : v; });
}
function toTeczka(btn) {
  if (!window.Teczka) return;
  const ids = Object.keys(choice); if (!ids.length) return;
  const lines = ids.map(id => `${F[id].ttitle}: ${F[id].label} = ${label(id, choice[id])}`);
  const ts = tensions().map(t => `Do przemyślenia: ${t.title}. ${t.text}`);
  const sims = [...document.querySelectorAll('.k-sim a')].slice(0, 5).map(a => a.textContent);
  const items = Teczka.load();
  items.push({ id: 'konstruktor-' + Date.now(), type: 'konstruktor', title: `Własny zestaw rozwiązań (${ids.length})`,
    cite: 'Konstytucje świata, Konstruktor; dane: warianty __NTOPICS__ tematów odczytane z 188 konstytucji (Claude Opus 5.5, cytaty sprawdzone), stan __DATE__',
    text: lines.join('\n') + (sims.length ? '\n\nNajbliższe konstytucje: ' + sims.join(', ') : '') + (ts.length ? '\n\n' + ts.join('\n') : ''),
    note: '', added: new Date().toISOString().slice(0, 10), page: location.href, url: location.href });
  if (Teczka.save(items)) { btn.textContent = '✓ Zapisano w teczce'; Teczka.attach(); setTimeout(() => btn.textContent = '+ Do teczki', 2500); }
  else btn.textContent = 'Przeglądarka blokuje zapis';
}
document.addEventListener('change', e => { if (e.target.closest('[data-id]') || e.target.matches('#k-eu,#k-recent')) { read(); render(); } });
document.addEventListener('input', e => { if (e.target.matches('[data-id] input[type=number]')) { read(); render(); } });
$('#k-pl').addEventListener('click', () => { fromPoland(); write(); render(); });
$('#k-clear').addEventListener('click', () => { choice = {}; write(); render(); });
$('#k-link').addEventListener('click', e => { const b = e.currentTarget; const url = location.href.split('#')[0] + (Object.keys(choice).length ? '#' + hash() : '');
  (navigator.clipboard ? navigator.clipboard.writeText(url) : Promise.reject()).then(() => { b.textContent = '✓ Skopiowano link'; }, () => { prompt('Link do zestawu:', url); }).finally(() => setTimeout(() => b.textContent = 'Kopiuj link do zestawu', 2500)); });
$('#k-teczka').addEventListener('click', e => toTeczka(e.currentTarget));
fromHash(); write(); render();
})();
"""

# Combinations that the comparative literature commonly flags. Phrased as questions, not verdicts.
TENSIONS = [
    {"when": "c('amend.prog_parlament')==='zwykla_lub_bezwzgledna' && c('amend.referendum')!=='zawsze' && c('amend.dwa_glosowania')!=='tak'",
     "title": "Łatwa zmiana konstytucji",
     "text": "Zwykła lub bezwzględna większość bez obowiązkowego referendum i bez odstępu czasu pozwala jednej większości zmienić reguły gry. Czy to zamierzone?"},
    {"when": "c('hogdlim.konstruktywne_wotum')==='tak' && (c('legdiss.kto_moze')||[]).includes('glowa_panstwa') && c('legdiss.tylko_w_okreslonych_sytuacjach')!=='tak'",
     "title": "Konstruktywne wotum a swobodne rozwiązanie parlamentu",
     "text": "Konstruktywne wotum stabilizuje rząd, ale jeśli głowa państwa może rozwiązać parlament bez ograniczeń, tę stabilność można obejść."},
    {"when": "c('em.zatwierdzenie_parlamentu')==='brak' || c('em.przedluzenie')==='bez_zgody'",
     "title": "Stan nadzwyczajny bez kontroli parlamentu",
     "text": "Bez zatwierdzenia albo przy przedłużaniu bez zgody parlamentu nic nie zatrzymuje przedłużania stanu w nieskończoność."},
    {"when": "c('em.ochrona_instytucji')==='nie'",
     "title": "Wybory i konstytucja w czasie stanu nadzwyczajnego",
     "text": "Bez zakazu zmiany konstytucji, rozwiązania parlamentu czy przesunięcia wyborów w czasie stanu nadzwyczajnego kryzys może posłużyć do zmiany ustroju."},
    {"when": "(c('em.maks_dni')||[])[0]>90",
     "title": "Długi pierwszy okres stanu nadzwyczajnego",
     "text": "Większość konstytucji, które to określają, przewiduje 30–90 dni do pierwszej oceny przez parlament."},
    {"when": "JSON.stringify(c('consel.kto_wybiera'))==='[\"parlament\"]' && c('consel.wiekszosc_kwalifikowana')!=='tak'",
     "title": "Sąd konstytucyjny wybierany przez bieżącą większość",
     "text": "Gdy wszystkich sędziów wybiera parlament zwykłą większością, jedna większość może obsadzić cały sąd. Pomaga większość kwalifikowana albo podział wyboru między kilka organów."},
    {"when": "c('conlim.ponowny_wybor')==='dozwolony' || c('conlim.ponowny_wybor')==='dozwolony_raz'",
     "title": "Ponowny wybór sędziów konstytucyjnych",
     "text": "Możliwość ponownego wyboru może skłaniać sędziów do zabiegania o względy tych, którzy wybierają."},
    {"when": "c('conterm.lata')&&c('conterm.lata')[1]!=null&&c('conterm.lata')[1]<=5",
     "title": "Krótka kadencja sędziów konstytucyjnych",
     "text": "Kadencja krótsza niż kadencja parlamentu pozwala jednej większości wymienić większość składu."},
    {"when": "c('jc.sedziowie_wiekszoscia')==='nie' || c('jc.kto_wybiera_sedziow_czlonkow')==='parlament'",
     "title": "Rada sądownictwa zależna od polityków",
     "text": "Gdy sędziowie nie stanowią większości rady albo sędziów-członków wybiera parlament, rada słabiej chroni niezależność sądów. To jeden z głównych sporów polskiej debaty po 2017 r."},
    {"when": "(c('jrem.kto_decyduje')||[]).some(x=>['parlament','glowa_panstwa','rzad'].includes(x)) && c('jrem.tylko_z_przyczyn_w_ustawie')!=='tak'",
     "title": "Odwołanie sędziów przez polityków",
     "text": "Odwołanie przez parlament, rząd lub głowę państwa bez zamkniętej listy przyczyn osłabia nieusuwalność sędziów."},
    {"when": "c('hosdec.moc')==='moc_ustawy' && c('hosdec.tylko_w_nadzwyczajnych')!=='tak' && c('hosdec.zatwierdzenie_parlamentu')!=='tak'",
     "title": "Dekrety z mocą ustawy bez parlamentu",
     "text": "Dekrety z mocą ustawy poza stanem nadzwyczajnym i bez zatwierdzenia przez parlament pozwalają rządzić z pominięciem ustawodawcy."},
    {"when": "(c('override.prog_odrzucenia')==='dwie_trzecie' || c('override.prog_odrzucenia')==='trzy_piate') && c('override.kto_ma_weto')!=='druga_izba'",
     "title": "Wysoki próg odrzucenia weta",
     "text": "Przy prezydencie z innego obozu niż większość wysoki próg pozwala blokować większość ustaw. Część państw ma niższy próg albo tylko weto zawieszające."},
    {"when": "c('hosterml.limit')==='trzy_lub_wiecej' || c('hosterml.ochrona_przed_zmiana')==='nie'",
     "title": "Słaby limit kadencji",
     "text": "Limit kadencji, który urzędująca osoba może zmienić na swoją korzyść, w praktyce bywa znoszony. Część konstytucji zakazuje takich zmian."},
    {"when": "c('referen.wiazace')==='tak' && c('referen.prog_frekwencji')==='nie' && c('referen.wylaczone_sprawy')==='nie'",
     "title": "Wiążące referendum bez progów i wyłączeń",
     "text": "Bez progu i bez spraw wyłączonych o prawach mniejszości lub budżecie może rozstrzygnąć mała część wyborców."},
    {"when": "c('immunity.zakres')==='formalny' && c('immunity.kto_uchyla')==='izba'",
     "title": "Immunitet uchylany przez samą izbę",
     "text": "Formalny immunitet, o którego uchyleniu decydują koledzy z izby, bywa używany do ochrony własnych członków. Alternatywa: decyzja sądu albo immunitet tylko za wypowiedzi."},
    {"when": "c('bank.niezaleznosc')==='nie'",
     "title": "Bank centralny bez niezależności",
     "text": "Bank centralny podporządkowany rządowi może być używany do finansowania bieżących wydatków. W UE niezależność wymagają traktaty."},
]


def main() -> int:
    ccp = ccp_data.load()
    facets = warianty_load.FACETS
    recs = warianty_load.load()
    topics = []
    for _, keys in GROUPS:
        for k in keys:
            spec = facets[k]
            fields = []
            for fk, f in spec["fields"].items():
                counts = Counter()
                for (t, c), r in recs.items():
                    v = r["values"].get(fk) if t == k else None
                    if v in (None, "nie_wynika", []):
                        continue
                    for x in (v if isinstance(v, list) else [v]):
                        counts[x] += 1
                values = [[vk, vl] for vk, vl in f.get("values", {}).items() if vk != "nie_wynika"] if f["type"] != "bool3" else [["tak", "tak"], ["nie", "nie"]]
                fields.append({"key": fk, "label": f["label"], "type": f["type"], "values": values, "counts": counts})
            topics.append({"key": k, "title": spec["title"], "fields": fields})
    countries = {}
    for (t, c), r in recs.items():
        if c not in ccp.by_code:
            continue
        d = ccp.by_code[c]
        y = str(d.get("year_enacted") or "")[:4]
        e = countries.setdefault(c, {"n": name_pl(c, c), "eu": int(c in EU27), "y": int(y) if y.isdigit() else 0, "v": {}})
        vals = {fk: v for fk, v in r["values"].items() if v not in (None, "nie_wynika", [])}
        if vals:
            e["v"][t] = vals
    pl = countries.get("PL", {"v": {}})["v"]

    def hint(t, f):
        if f["type"] == "int":
            nums = sorted(int(k) for k, n in f["counts"].items() for _ in range(n))
            if not nums:
                return ""
            plv = pl.get(t["key"], {}).get(f["key"])
            return f'<p class="k-hint">Mediana <b>{nums[len(nums) // 2]}</b>, zakres {nums[0]}–{nums[-1]} ({len(nums)} konstytucji){f" · RP: <b>{plv}</b>" if plv is not None else ""}</p>'
        return ""

    blocks = []
    for gname, keys in GROUPS:
        blocks.append(f"<h2>{escape(gname)}</h2>")
        for t in (x for x in topics if x["key"] in keys):
            fields_html = []
            for f in t["fields"]:
                fid = f'{t["key"]}.{f["key"]}'
                plv = pl.get(t["key"], {}).get(f["key"])
                if f["type"] == "int":
                    ctrl = (f'<div class="nums"><input type="number" min="0" placeholder="od" aria-label="{escape(f["label"])}: od">'
                            f'<span>–</span><input type="number" min="0" placeholder="do" aria-label="{escape(f["label"])}: do"></div>')
                elif f["type"] == "multi":
                    ctrl = '<div class="checks">' + "".join(
                        f'<label><input type="checkbox" value="{vk}"> {escape(vl)} <small>({f["counts"].get(vk, 0)}{", RP" if isinstance(plv, list) and vk in plv else ""})</small></label>'
                        for vk, vl in f["values"]) + "</div>"
                else:
                    ctrl = f'<select aria-label="{escape(f["label"])}"><option value="">dowolnie</option>' + "".join(
                        f'<option value="{vk}">{escape(vl)} · {f["counts"].get(vk, 0)}{" · RP" if plv == vk else ""}</option>' for vk, vl in f["values"]) + "</select>"
                tag = "div" if f["type"] in ("multi", "int") else "label"
                fields_html.append(f'<{tag} class="k-field" data-id="{fid}"><span>{escape(f["label"])}{" (musi zawierać)" if f["type"] == "multi" else ""}</span>{ctrl}{hint(t, f)}</{tag}>')
            n = sum(1 for c in countries.values() if t["key"] in c["v"])
            blocks.append(f'<details class="k-topic" data-topic="{t["key"]}"><summary>{escape(t["title"])}<small>dane dla {n} konstytucji · <a href="../tematy/{t["key"]}.html">temat</a></small></summary>{"".join(fields_html)}</details>')

    data = {"topics": [{"key": t["key"], "title": t["title"], "fields": [{k: f[k] for k in ("key", "label", "type", "values")} for f in t["fields"]]} for t in topics],
            "countries": countries, "tensions": TENSIONS}
    body = f'''<p class="crumbs">Konstruktor</p><h1>Złóż własny zestaw rozwiązań</h1>
<p class="sub">Wybierz, jak Twoim zdaniem powinny działać kluczowe instytucje: kadencje, weto, stany nadzwyczajne, sądy, referendum, wybory i partie, prawa, obronność, umowy międzynarodowe, dług i majątek państwa. Zobaczysz, które konstytucje mają podobny zestaw, czym różni się on od obecnej Konstytucji RP i jakie połączenia warto przemyśleć. Zostaw „dowolnie” tam, gdzie nie masz zdania.</p>
<div class="k-actions"><button type="button" id="k-pl" class="primary">Zacznij od obecnej Konstytucji RP</button><button type="button" id="k-clear">Wyczyść</button><button type="button" id="k-link">Kopiuj link do zestawu</button><button type="button" id="k-teczka">+ Do teczki</button></div>
<p class="note" id="k-count" aria-live="polite"></p>
<div class="k-layout"><form class="k-form" onsubmit="return false">{"".join(blocks)}
<p class="note">Liczby przy odpowiedziach to liczba konstytucji z danym rozwiązaniem; „RP” oznacza obecną Konstytucję RP. Wartości odczytano automatycznie (Claude Opus 5.5) z 188 obowiązujących konstytucji, każda z cytatem sprawdzonym w źródle. To nawigacja, nie ocena prawna. <a href="../tematy/index.html">Tematy</a> pokazują przepisy.</p></form>
<aside class="k-out" id="wynik" aria-live="polite"><div class="k-filters" hidden><label><input type="checkbox" id="k-eu"> tylko UE</label><label><input type="checkbox" id="k-recent"> od 2000 r.</label></div><div id="k-result"></div></aside></div>
<a class="k-jump" id="k-jump" href="#wynik">Wynik ↓</a>
<script type="application/json" id="k-data">{json.dumps(data, ensure_ascii=False, separators=(",", ":")).replace("</", "<\\/")}</script>
<script>{JS.replace('__NTOPICS__', str(len(topics))).replace('__DATE__', DATA_DATE)}</script>'''
    html = page("Konstruktor: złóż własny zestaw rozwiązań", body, description="Wybierz rozwiązania dla 23 kluczowych tematów i porównaj z konstytucjami świata i Konstytucją RP.",
                css="../panstwa/style.css", current="konstruktor")
    html = html.replace("</head>", f"<style>{CSS}</style></head>").replace("</body>", '<script src="../teczka/teczka.js"></script></body>')
    (HERE / "index.html").write_text(html, encoding="utf-8")
    print(json.dumps({"topics": len(topics), "countries": len(countries), "fields": sum(len(t["fields"]) for t in topics), "bytes": len(html)}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
