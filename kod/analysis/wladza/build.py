#!/usr/bin/env python3
"""Władza: who decides and who blocks in each constitution (page analysis/wladza/index.html).

Reads wladza.json from model.py. Country and decision views are rendered in the browser from embedded data;
comparisons are static. No quotes from the Constitute editions are shown (publisher rights); article numbers link
to the topic pages. Usage: python3 analysis/wladza/model.py && python3 analysis/wladza/build.py
"""
from __future__ import annotations

import json
import statistics
import sys
from collections import Counter
from html import escape
from pathlib import Path

HERE = Path(__file__).resolve().parent
A = HERE.parent
sys.path.insert(0, str(A / "panstwa"))
from build import page, name_pl  # noqa: E402
sys.path.insert(0, str(HERE))
import symulator  # noqa: E402

DATA_DATE = "2026-11-07"
EU27 = {"AT", "BE", "BG", "HR", "CY", "CZ", "DK", "EE", "FI", "FR", "DE", "GR", "HU", "IE", "IT",
        "LV", "LT", "LU", "MT", "NL", "PL", "PT", "RO", "SK", "SI", "ES", "SE"}
ORDER = ["L1", "L2", "G", "HS", "P", "CC", "J"]
COLORS = {"L1": "#006858", "L2": "#5fa58f", "G": "#c49260", "HS": "#b4532a", "P": "#6c5a9e", "CC": "#41525e", "J": "#8c9aa3"}
TOPIC_PAGE = {"legapp": "legapp", "override": "override", "hospow": "hospow", "budget": "budget", "legini": "legini",
              "amend": "amend", "hogelect": "hogelect", "cabdiss": "cabdiss", "hogdlim": "hogdlim", "legdiss": "legdiss",
              "consel": "consel", "em": "em", "war": "war", "treat": "treat", "hosdiss": "hosdiss"}
IND = {"opozycja_do_sadu": "Mniejszość parlamentarna lub każdy może zaskarżyć ustawę do sądu konstytucyjnego",
       "obywatel_do_sadu": "Obywatel może wnieść skargę do sądu konstytucyjnego",
       "egzekutywa_odwoluje_sedziow": "Głowa państwa lub rząd odwołuje sędziów bez udziału organu sądowego",
       "parlament_rozwiazywalny_swobodnie": "Głowa państwa lub rząd może rozwiązać parlament bez szczególnych przesłanek",
       "konstruktywne_wotum": "Konstruktywne wotum nieufności",
       "dekrety_z_moca_ustawy": "Dekrety głowy państwa z mocą ustawy"}

CSS = """
.w-hero{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:1px;background:var(--line);border:1px solid var(--line);margin:18px 0 8px}
.w-hero div{background:#fff;padding:14px 16px}.w-hero b{display:block;font:600 28px/1.1 Georgia,serif}.w-hero span{font-size:13px;color:var(--muted)}
.box{background:#fff;border:1px solid var(--line);padding:14px 16px;margin:14px 0 22px}
.box h3{font:600 18px/1.3 Georgia,serif;margin:0 0 4px}
.stack{display:flex;height:22px;border-radius:3px;overflow:hidden;background:#eef1ec;min-width:120px}
.stack i{display:block;height:100%}
.stack.big{height:34px}
.legend{display:flex;flex-wrap:wrap;gap:6px 16px;font-size:13px;color:var(--muted);margin:6px 0}
.legend i{display:inline-block;width:12px;height:12px;border-radius:2px;margin-right:6px;vertical-align:-1px}
table.w{width:100%;border-collapse:collapse;font-size:13.5px}
table.w th,table.w td{padding:6px 6px;border-bottom:1px solid var(--line);text-align:left;vertical-align:top}
table.w td.n{text-align:right;font-variant-numeric:tabular-nums;white-space:nowrap}
table.w th{font-weight:600;color:var(--muted);font-size:12.5px}
table.w tr.pl td{background:#fbf3ec}
.flags{margin:4px 0 0;padding-left:16px;color:var(--muted);font-size:12.5px}
.src{font-size:12px;color:var(--muted)}
.tag{display:inline-block;font-size:11.5px;padding:1px 6px;border-radius:9px;background:#e8efe9;color:#1d2a35;margin:1px 2px 1px 0}
.tag.veto{background:#f3dfd2}
.controls{display:flex;flex-wrap:wrap;gap:10px;align-items:end;margin:8px 0 12px}
.controls label{display:flex;flex-direction:column;font-size:13px;color:var(--muted);gap:3px}
.controls select{font:inherit;padding:5px 8px;max-width:100%}
.tablewrap{overflow-x:auto;max-height:640px;overflow-y:auto}
.mx td.n{min-width:44px}.mx td.h{font-weight:600}
.cell{display:inline-block;min-width:36px;text-align:center;border-radius:3px;padding:1px 4px}
.two{display:grid;grid-template-columns:1fr 1fr;gap:18px}
.two>*{min-width:0}.box{overflow-x:auto}
svg.ctl{width:100%;max-width:520px;height:auto;display:block}
svg.ctl text{font:12.5px system-ui,sans-serif;fill:#1d2a35}
svg.ctl .node{fill:#fff;stroke:#41525e;stroke-width:1.2}
svg.ctl .e{fill:none;stroke-width:1.6}
.note{font-size:13px;color:var(--muted)}
@media (max-width:800px){.w-hero{grid-template-columns:1fr 1fr}.two{grid-template-columns:1fr}table.w{font-size:12.5px}}
"""

JS = r"""(()=>{
const D=JSON.parse(document.getElementById('wdata').textContent);
const M=D.meta, C=D.countries, ORDER=__ORDER__, COL=__COLORS__, TP=__TOPICS__;
const esc=v=>String(v??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const pct=x=>(Math.round(x*1000)/10).toLocaleString('pl-PL')+'%';
const stack=(s,big)=>'<div class="stack'+(big?' big':'')+'" role="img" aria-label="'+esc(ORDER.filter(o=>s[o]>0).map(o=>M.short[o]+' '+pct(s[o])).join(', '))+'">'+ORDER.filter(o=>s[o]>0.0005).map(o=>'<i style="width:'+(s[o]*100)+'%;background:'+COL[o]+'" title="'+esc(M.short[o]+': '+pct(s[o]))+'"></i>').join('')+'</div>';
const tags=(xs,cls)=>xs.map(o=>'<span class="tag '+(cls||'')+'">'+esc(M.short[o])+'</span>').join('');
const ctlSvg=c=>{const pos={L1:[90,60],L2:[90,170],HS:[420,60],G:[420,170],CC:[255,250],J:[255,250],P:[255,20]};
 const ed=[];c.control.forEach(k=>k.by.forEach(b=>{if(b!==k.target)ed.push([b,k.target,k.decision]);}));
 const nodes=[...new Set(ed.flatMap(e=>[e[0],e[1]]))];if(!nodes.length)return '<p class="note">Brak danych o odwoływaniu i powoływaniu organów.</p>';
 const lab={odwolanie_rzadu:'odwołuje rząd',rozwiazanie:'rozwiązuje parlament',usuniecie_glowy:'usuwa głowę państwa',sedziowie_tk:'wybiera sędziów TK'};
 const col={odwolanie_rzadu:'#c49260',rozwiazanie:'#b4532a',usuniecie_glowy:'#006858',sedziowie_tk:'#41525e'};
 let s='<svg class="ctl" viewBox="0 0 520 290" role="img" aria-label="Kto kogo powołuje i odwołuje"><defs>'+Object.entries(col).map(([k,v])=>'<marker id="m-'+k+'" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto"><path d="M0,0L10,5L0,10z" fill="'+v+'"/></marker>').join('')+'</defs>';
 const seen={};ed.forEach(([a,b,d])=>{const [x1,y1]=pos[a]||[255,140],[x2,y2]=pos[b]||[255,140];const k=[a,b].sort().join();seen[k]=(seen[k]||0)+1;const bend=(seen[k]%2?1:-1)*(18+8*seen[k]);
  const mx=(x1+x2)/2,my=(y1+y2)/2,dx=x2-x1,dy=y2-y1,L=Math.hypot(dx,dy)||1,cx=mx-dy/L*bend,cy=my+dx/L*bend;const sh=t=>[x1+(x2-x1)*t,y1+(y2-y1)*t];
  const [sx,sy]=[x1+dx/L*44,y1+dy/L*22],[ex,ey]=[x2-dx/L*48,y2-dy/L*24];
  s+='<path class="e" d="M'+sx+','+sy+' Q'+cx+','+cy+' '+ex+','+ey+'" stroke="'+col[d]+'" marker-end="url(#m-'+d+')"><title>'+esc(M.short[a]+' '+lab[d])+'</title></path>';});
 nodes.forEach(n=>{const [x,y]=pos[n]||[255,140];s+='<rect class="node" x="'+(x-58)+'" y="'+(y-15)+'" width="116" height="30" rx="4"/><text x="'+x+'" y="'+(y+4)+'" text-anchor="middle">'+esc(M.short[n])+'</text>';});
 s+='</svg><p class="legend">'+Object.entries(lab).map(([k,v])=>'<span><i style="background:'+col[k]+'"></i>'+v+'</span>').join('')+'</p>';return s;};
const LV={S1:'większość w izbie',S2:'większość + głowa państwa',S3:'3/5 mandatów',S4:'2/3 mandatów',poza_polityka:'poza zasięgiem samej polityki',ustawa:'decyduje ustawa'};
const blk=x=>x==null?'–':x===-1?'sprzeciwu nie da się odrzucić':(x===0?'izba nie blokuje':'ponad '+pct(x).replace(',0%','%'));
function country(code){const c=C[code];if(!c)return '';
 let h='<div class="two"><div><h3>Profil siły: '+esc(c.name)+'</h3><p class="note">Średni udział organów w '+Object.keys(c.decisions).length+' decyzjach (indeks Shapleya-Shubika). Typ: '+esc(M.types[c.type])+'. Koncentracja (HHI): '+c.hhi.toFixed(2).replace('.',',')+(c.ranked?'':' · <b>za mało kompletnych decyzji, poza rankingami</b>')+'</p>'+stack(c.profile,true)+'<p class="legend">'+ORDER.filter(o=>c.profile[o]>0.0005).map(o=>'<span><i style="background:'+COL[o]+'"></i>'+esc(M.short[o])+' '+pct(c.profile[o])+'</span>').join('')+'</p></div><div><h3>Kto kogo powołuje i odwołuje</h3>'+ctlSvg(c)+'</div></div>';
 h+='<div class="tablewrap"><table class="w"><thead><tr><th>Decyzja</th><th style="min-width:160px">Podział siły</th><th>Weto (bez nich nie da się)</th><th>Mniejszość blokująca w izbie</th><th>Podstawa</th></tr></thead><tbody>';
 for(const [d,x] of Object.entries(c.decisions)){
  const sh=ORDER.filter(o=>x.shares[o]>0.0005).map(o=>esc(M.short[o])+' '+pct(x.shares[o])).join(' · ');
  const src=Object.entries(x.sources).map(([t,s])=>'<a href="../tematy/'+(TP[t]||t)+'.html">'+esc(t)+'</a> '+esc((s.a||[]).slice(0,4).join(', ')+((s.a||[]).length>4?'…':''))+(s.k?' <span title="ręczna korekta">✎</span>':'')).join('<br>');
  h+='<tr><td><b>'+esc(M.decisions[d])+'</b>'+(x.flags.length?'<ul class="flags">'+x.flags.map(f=>'<li>'+esc(f)+'</li>').join('')+'</ul>':'')+'</td><td>'+stack(x.shares)+'<div class="src">'+sh+'</div></td><td>'+tags(x.veto,'veto')+'</td><td class="n">'+blk(x.b)+(x.bh!=null&&x.bh!==x.b?'<br><span class="src">gdy głowa państwa przeciw: '+blk(x.bh)+'</span>':'')+'</td><td class="src">'+src+'</td></tr>';}
 h+='</tbody></table></div>';
 const ind=Object.entries(c.ind).filter(([k,v])=>v).map(([k])=>'<li>'+esc(M.ind[k])+'</li>').join('');
 if(ind)h+='<p class="note" style="margin-top:10px">Mechanizmy hamujące i wzmacniające:</p><ul class="flags">'+ind+'</ul>';
 if(c.rr)h+='<p class="note">Miejsce w rankingu siły głowy państwa przy różnych założeniach: '+c.rr[0]+'–'+c.rr[1]+'.</p>';
 const cap=Object.entries(c.cap);
 h+='<div class="two" style="margin-top:12px"><div><h3>Kto przejmie instytucje</h3>'+(cap.length?'<table class="w"><tbody>'+cap.map(([k,x])=>'<tr><td>'+esc(M.institutions[k])+'</td><td>'+esc(LV[x.level])+(x.czesciowo?' (część składu wybiera polityka)':'')+'</td></tr>').join('')+'</tbody></table><p class="note">Najsłabszy obóz polityczny, który sam obsadzi instytucję.</p>':'<p class="note">Konstytucja nie opisuje tych instytucji.</p>')+'</div>';
 const j=c.jud;h+='<div><h3>Niezależność sądów w tekście: '+(j.score==null?'za mało danych':pct(j.score/100).replace(',0%','%'))+'</h3><ul class="flags">'+Object.entries(j.components).filter(([k,v])=>v!==null).map(([k,v])=>'<li>'+(v?'✓ ':'✗ ')+esc(M.judicial[k])+'</li>').join('')+'</ul></div></div>';
 return h;}
const sel=document.getElementById('kraj'),out=document.getElementById('kraj-out');
// view state in the address: #kraj=PL&decyzja=ustawa&grupa=eu (a bare #PL also works), so a view can be linked
const ds=document.getElementById('decyzja'),dout=document.getElementById('decyzja-out'),grp=document.getElementById('grupa');
const readHash=()=>{const raw=location.hash.slice(1);const h=new URLSearchParams(raw.includes('=')?raw:'kraj='+raw);
 const k=(h.get('kraj')||'').toUpperCase();if(C[k])sel.value=k;if(h.get('decyzja')&&M.decisions[h.get('decyzja')])ds.value=h.get('decyzja');
 if(h.get('grupa')&&[...grp.options].some(o=>o.value===h.get('grupa')))grp.value=h.get('grupa');return !!raw;};
const writeHash=()=>{try{const p=new URLSearchParams({kraj:sel.value});if(ds.value!==ds.options[0].value)p.set('decyzja',ds.value);if(grp.value!=='all')p.set('grupa',grp.value);history.replaceState(null,'','#'+p);}catch(e){}};
const show=()=>{out.innerHTML=country(sel.value);try{localStorage.setItem('wladza-kraj',sel.value)}catch(e){}};
if(!readHash()){try{const v=localStorage.getItem('wladza-kraj');if(v&&C[v])sel.value=v;}catch(e){}}
sel.addEventListener('change',()=>{show();writeHash();});show();
// decision view
function decision(){const d=ds.value,g=grp.value;const rows=Object.entries(C).filter(([k,c])=>c.decisions[d]&&(g==='all'||(g==='eu'?c.eu:c.type===g)));
 if(!rows.length){dout.innerHTML='<p class="note">Brak państw w tej grupie.</p>';return;}
 const avg={};ORDER.forEach(o=>avg[o]=rows.reduce((s,[k,c])=>s+(c.decisions[d].shares[o]||0),0)/rows.length);
 const vc={};rows.forEach(([k,c])=>c.decisions[d].veto.forEach(o=>vc[o]=(vc[o]||0)+1));
 const buckets=f=>{const o={};rows.forEach(([k,c])=>{const b=c.decisions[d][f];if(f==='bh'&&b==null)return;const key=b==null?'–':blk(b);(o[key]=o[key]||[]).push(k);});return o;};
 const btab=(o,title)=>'<p class="note">'+title+'</p><table class="w"><tbody>'+Object.entries(o).sort((a,b)=>b[1].length-a[1].length).map(([k,cs])=>'<tr><td>'+esc(k)+'</td><td class="n">'+cs.length+'</td><td class="src">'+cs.slice(0,40).map(x=>'<a href="#'+x+'" data-k="'+x+'">'+esc(C[x].name)+'</a>').join(', ')+(cs.length>40?' …':'')+'</td></tr>').join('')+'</tbody></table>';
 const bc=buckets('b'),bh=buckets('bh');
 let h='<h3>'+esc(M.decisions[d])+': '+rows.length+' państw</h3><p class="note">Średni podział siły</p>'+stack(avg,true)+'<p class="legend">'+ORDER.filter(o=>avg[o]>0.0005).map(o=>'<span><i style="background:'+COL[o]+'"></i>'+esc(M.short[o])+' '+pct(avg[o])+'</span>').join('')+'</p>';
 h+='<div class="two"><div><p class="note">Kto ma weto (w ilu państwach)</p><table class="w"><tbody>'+Object.entries(vc).sort((a,b)=>b[1]-a[1]).map(([o,n])=>'<tr><td>'+esc(M.short[o])+'</td><td class="n">'+n+'</td><td class="n">'+pct(n/rows.length)+'</td></tr>').join('')+'</tbody></table></div>';
 h+='<div>'+btab(bc,'Ile mandatów pierwszej izby wystarczy do zablokowania (gdy pozostałe organy są za)')+(Object.keys(bh).length?btab(bh,'Gdy głowa państwa jest przeciw: ile mandatów wystarczy, by utrzymać jej sprzeciw'):'')+'</div></div>';
 dout.innerHTML=h;}
ds.addEventListener('change',()=>{decision();writeHash();});grp.addEventListener('change',()=>{decision();writeHash();});decision();
window.addEventListener('hashchange',()=>{readHash();show();decision();});
const pick=k=>{sel.value=k;show();writeHash();document.getElementById('panstwo').scrollIntoView({behavior:'smooth'});};
dout.addEventListener('click',e=>{const a=e.target.closest('a[data-k]');if(a){e.preventDefault();pick(a.dataset.k);}});
document.addEventListener('click',e=>{const a=e.target.closest('a.cty');if(a){e.preventDefault();pick(a.dataset.k);}});
// sortable ranking
const tb=document.getElementById('rank');if(tb){tb.querySelectorAll('th[data-s]').forEach(th=>th.addEventListener('click',()=>{const i=+th.dataset.s,rows=[...tb.tBodies[0].rows];const dir=th.dataset.d=th.dataset.d==='1'?'-1':'1';
 rows.sort((a,b)=>{const x=a.cells[i].dataset.v,y=b.cells[i].dataset.v;return (isNaN(x)?x.localeCompare(y,'pl'):(x-y))*dir;});rows.forEach(r=>tb.tBodies[0].appendChild(r));}));}
})();"""


def pct(x):
    return f"{x * 100:.1f}".replace(".", ",") + "%"


def stack(s, big=False):
    parts = "".join(f'<i style="width:{s.get(o, 0) * 100:.2f}%;background:{COLORS[o]}" title="{o}"></i>' for o in ORDER if s.get(o, 0) > .0005)
    label = ", ".join(f"{o} {pct(s[o])}" for o in ORDER if s.get(o, 0) > .0005)
    return f'<div class="stack{" big" if big else ""}" role="img" aria-label="{escape(label)}">{parts}</div>'


def legend(meta, s=None):
    return '<p class="legend">' + "".join(f'<span><i style="background:{COLORS[o]}"></i>{escape(meta["short"][o])}{" " + pct(s[o]) if s else ""}</span>'
                                          for o in ORDER if s is None or s.get(o, 0) > .0005) + "</p>"


def mean_profile(ms):
    return {o: statistics.fmean(m["profile"][o] for m in ms) for o in ORDER} if ms else {o: 0 for o in ORDER}


def main():
    data = json.loads((HERE / "wladza.json").read_text())
    meta, C = data["meta"], data["countries"]
    for code, m in C.items():
        m["name"] = name_pl(code, code)
    ranked = {k: m for k, m in C.items() if m["ranked"]}
    world, eu = mean_profile(list(ranked.values())), mean_profile([m for k, m in ranked.items() if k in EU27])
    pl = C.get("PL")

    # compact client data (no quotes: publisher rights)
    client = {"meta": {**meta, "ind": IND}, "countries": {
        k: {"name": m["name"], "type": m["type"], "eu": k in EU27, "ranked": m["ranked"], "profile": m["profile"], "hhi": m["hhi"],
            "control": m["control"], "ind": m["indicators"], "cap": m["przejecie"], "jud": m["sady"], "rr": m.get("rank_range"),
            "decisions": {d: {"shares": x["shares"], "veto": x["veto"], "b": x["blokujaca_mniejszosc"], "bh": x["blokujaca_mniejszosc_bez_HS"],
                              "flags": x["flags"], "sources": {t: {"a": s["articles"], "k": bool(s["korekty"])} for t, s in x["sources"].items()}}
                          for d, x in m["decisions"].items()}}
        for k, m in sorted(C.items(), key=lambda kv: kv[1]["name"])}}

    types = Counter(m["type"] for m in ranked.values())
    by_type = {t: mean_profile([m for m in ranked.values() if m["type"] == t]) for t in meta["types"] if types.get(t)}
    hs_med = statistics.median(m["profile"]["HS"] for m in ranked.values())
    parl = lambda m: m["profile"]["L1"] + m["profile"]["L2"]

    # aggregate control / veto matrices (share of ranked countries)
    ctl = Counter()
    for m in ranked.values():
        for k in m["control"]:
            for b in k["by"]:
                if b != k["target"]:
                    ctl[(b, k["decision"])] += 1
    veto = Counter()
    for m in ranked.values():
        for a, bs in m["blocks"].items():
            for b in bs:
                veto[(a, b)] += 1
    n = len(ranked)

    def heat(v):
        a = min(1, v / max(1, n) * 1.4)
        return f'<span class="cell" style="background:rgba(180,83,42,{a:.2f});color:{"#fff" if a > .55 else "inherit"}">{round(v / n * 100)}%</span>'
    organs_m = [o for o in ORDER if any(veto[(o, b)] for b in ORDER) or any(veto[(a, o)] for a in ORDER)]
    veto_tbl = ('<table class="w mx"><thead><tr><th>blokuje ↓ / kogo →</th>' + "".join(f'<th>{escape(meta["short"][b])}</th>' for b in organs_m) + "</tr></thead><tbody>"
                + "".join(f'<tr><td class="h">{escape(meta["short"][a])}</td>' + "".join(f'<td class="n">{heat(veto[(a, b)]) if a != b else ""}</td>' for b in organs_m) + "</tr>" for a in organs_m)
                + "</tbody></table>")
    ctl_rows = [("HS", "rozwiazanie", "Głowa państwa może rozwiązać parlament"), ("G", "rozwiazanie", "Rząd może rozwiązać parlament (lub głowa państwa na jego wniosek)"),
                ("L1", "odwolanie_rzadu", "Parlament może odwołać rząd"), ("HS", "odwolanie_rzadu", "Głowa państwa może odwołać rząd"),
                ("L1", "usuniecie_glowy", "Parlament uczestniczy w usunięciu głowy państwa"), ("CC", "usuniecie_glowy", "Sąd konstytucyjny orzeka o usunięciu głowy państwa"),
                ("HS", "sedziowie_tk", "Głowa państwa wybiera (część) sędziów TK"), ("L1", "sedziowie_tk", "Parlament wybiera (część) sędziów TK"),
                ("J", "sedziowie_tk", "Sądy lub rada sądownictwa wybierają (część) sędziów TK")]

    def pl_has(o, d):
        return pl and any(o in k["by"] and k["decision"] == d for k in pl["control"])
    ctl_tbl = ('<table class="w"><thead><tr><th>Mechanizm</th><th>państw</th><th>%</th><th>Polska</th></tr></thead><tbody>'
               + "".join(f'<tr><td>{t}</td><td class="n">{ctl[(o, d)]}</td><td class="n">{round(ctl[(o, d)] / n * 100)}%</td><td>{"tak" if pl_has(o, d) else "–"}</td></tr>' for o, d, t in ctl_rows)
               + "</tbody></table>")
    ind_cnt = Counter(k for m in ranked.values() for k, v in m["indicators"].items() if v)
    ind_tbl = ('<table class="w"><thead><tr><th>Mechanizm</th><th>państw</th><th>%</th><th>Polska</th></tr></thead><tbody>'
               + "".join(f'<tr><td>{escape(t)}</td><td class="n">{ind_cnt[k]}</td><td class="n">{round(ind_cnt[k] / n * 100)}%</td><td>{"tak" if pl and pl["indicators"].get(k) else "–"}</td></tr>' for k, t in IND.items())
               + "</tbody></table>")

    type_rows = "".join(f'<tr><td>{escape(meta["types"][t])}</td><td class="n">{types[t]}</td><td style="min-width:200px">{stack(p)}</td><td class="n">{pct(p["HS"])}</td><td class="n">{pct(p["L1"] + p["L2"])}</td></tr>'
                        for t, p in sorted(by_type.items(), key=lambda kv: -types[kv[0]]))
    cmp_rows = "".join(f'<tr{" class=\"pl\"" if lbl.startswith("Polska") else ""}><td>{lbl}</td><td style="min-width:200px">{stack(p)}</td><td class="n">{pct(p["HS"])}</td><td class="n">{pct(p["G"])}</td><td class="n">{pct(p["L1"] + p["L2"])}</td></tr>'
                       for lbl, p in [("Polska", pl["profile"] if pl else world), (f"Unia Europejska (średnia, {sum(1 for k in ranked if k in EU27)})", eu), (f"Świat (średnia, {n})", world)])
    rank_rows = "".join(
        f'<tr{" class=\"pl\"" if k == "PL" else ""}><td data-v="{escape(m["name"])}"><a class="cty" href="#{k}" data-k="{k}">{escape(m["name"])}</a></td>'
        f'<td data-v="{escape(meta["types"][m["type"]])}">{escape(meta["types"][m["type"]])}</td><td style="min-width:180px" data-v="{m["profile"]["HS"]:.4f}">{stack(m["profile"])}</td>'
        f'<td class="n" data-v="{m["profile"]["HS"]:.4f}">{pct(m["profile"]["HS"])}</td><td class="n" data-v="{m["profile"]["G"]:.4f}">{pct(m["profile"]["G"])}</td>'
        f'<td class="n" data-v="{parl(m):.4f}">{pct(parl(m))}</td><td class="n" data-v="{m["hhi"]:.4f}">{f"{m['hhi']:.2f}".replace(".", ",")}</td><td class="n" data-v="{len(m["decisions"])}">{len(m["decisions"])}</td></tr>'
        for k, m in sorted(ranked.items(), key=lambda kv: -kv[1]["profile"]["HS"]))
    top_hs = sorted(ranked.items(), key=lambda kv: -kv[1]["profile"]["HS"])[:5]
    pl_rank = sorted(ranked, key=lambda k: -ranked[k]["profile"]["HS"]).index("PL") + 1 if pl and pl["ranked"] else None

    # ---- capture of institutions ----
    LV = {"S1": "większość w izbie", "S2": "większość + głowa państwa", "S3": "3/5 mandatów", "S4": "2/3 mandatów",
          "poza_polityka": "poza zasięgiem samej polityki", "ustawa": "decyduje ustawa"}
    LV_ORDER = ["S1", "ustawa", "S2", "S3", "S4", "poza_polityka"]
    cap_rows = ""
    for inst, label in meta["institutions"].items():
        lv = Counter(m["przejecie"][inst]["level"] for m in ranked.values() if inst in m["przejecie"])
        tot = sum(lv.values())
        if not tot:
            continue
        cells = "".join(f'<td class="n">{round(lv[l] / tot * 100)}%</td>' for l in LV_ORDER)
        plv = pl["przejecie"].get(inst, {}).get("level") if pl else None
        cap_rows += f'<tr><td>{escape(label)}</td><td class="n">{tot}</td>{cells}<td>{escape(LV.get(plv, "nie ma w konstytucji"))}</td></tr>'
    cap_tbl = ('<table class="w"><thead><tr><th>Instytucja</th><th>państw</th>' + "".join(f"<th>{escape(LV[l])}</th>" for l in LV_ORDER)
               + "<th>Polska</th></tr></thead><tbody>" + cap_rows + "</tbody></table>")

    def resil(m):
        xs = [x["level"] for k, x in m["przejecie"].items() if k != "konstytucja"]
        return sum(l in ("S3", "S4", "poza_polityka") for l in xs) / len(xs) if len(xs) >= 3 else None
    res = {k: resil(m) for k, m in ranked.items() if resil(m) is not None}
    res_eu = [v for k, v in res.items() if k in EU27]
    res_top = sorted(res, key=lambda k: (-res[k], C[k]["name"]))[:12]
    res_low = [k for k in sorted(res, key=lambda k: (res[k], C[k]["name"])) if res[k] == 0]
    # ---- judicial independence ----
    js = {k: m["sady"]["score"] for k, m in ranked.items() if m["sady"]["score"] is not None}
    jcomp = "".join(f'<tr><td>{escape(t)}</td><td class="n">{round(sum(1 for m in ranked.values() if m["sady"]["components"].get(k)) / max(1, sum(1 for m in ranked.values() if m["sady"]["components"].get(k) is not None)) * 100)}%</td>'
                    f'<td>{"tak" if pl and pl["sady"]["components"].get(k) else ("nie dotyczy" if pl and pl["sady"]["components"].get(k) is None else "nie")}</td></tr>' for k, t in meta["judicial"].items())
    j_eu = sorted((k for k in js if k in EU27), key=lambda k: -js[k])
    j_eu_rows = "".join(f'<tr{" class=\"pl\"" if k == "PL" else ""}><td>{escape(C[k]["name"])}</td><td class="n">{js[k]:.0f}</td></tr>' for k in j_eu)
    # ---- trust: validation and robustness ----
    W = json.loads((HERE / "walidacja.json").read_text()) if (HERE / "walidacja.json").exists() else {}
    trust = ""
    if W.get("pola"):
        frow = "".join(f'<tr><td>{escape(r["pole"])}</td><td class="n">{r["n"]}</td><td class="n">{pct(r["zgodnosc"])}</td><td class="n">{"–" if r["kappa"] is None else str(r["kappa"]).replace(".", ",")}</td></tr>' for r in W["pola"])
        ty, wy, sd = W["typologia"], W["wykonawcza"], W["sady"]
        f3 = lambda v: str(v).replace(".", ",")
        trust += f'''<div class="box"><h3>Zgodność odczytów z ekspertami CCP: {pct(W["pola_przed_rozstrzygnieciem"]["zgodnosc"])}, po przeglądzie rozbieżności {pct(W["pola_razem"]["zgodnosc"])}</h3>
<p class="note">Nasze odczyty (model językowy, cytat sprawdzany w kodzie) porównane z ręcznym kodowaniem Comparative Constitutions Project (wersja 5, stan na 2023 r.) w {W["pola_razem"]["n"]} parach państwo × pole. Kappa poprawia zgodność o przypadek; przy polach, w których prawie wszystkie konstytucje mają tę samą odpowiedź (weto, dekrety), kappa jest bliska zera mimo wysokiej zgodności. Najsłabiej wypada odwołanie rządu: CCP liczy formalne odwołanie ministrów przez głowę państwa, a my tylko rzeczywiste.
Każdą z {W["rozstrzygniecia"]["rozbieznosci"]} rozbieżności rozstrzygnęliśmy osobno: model dostał pytanie w naszej definicji i szerszy fragment konstytucji, bez informacji, która odpowiedź jest czyja, i musiał podać dosłowny cytat. {W["rozstrzygniecia"]["poprawki"]} odczytów poprawiliśmy (korekty z cytatem w danych), w pozostałych tekst potwierdził nasz odczyt albo nie rozstrzygnął sprawy. Tabela pokazuje stan po poprawkach.</p>
<div class="tablewrap"><table class="w"><thead><tr><th>Pole</th><th>par</th><th>zgodność</th><th>kappa</th></tr></thead><tbody>{frow}</tbody></table></div></div>
<div class="two"><div class="box"><h3>Typ ustroju: zgodność {pct(ty["zgodnosc"])}</h3><p class="note">Nasz typ (prezydencki, półprezydencki, parlamentarny) porównany z klasyfikacją Cheibuba, Elkinsa i Ginsburga (2014) dla {ty["n"]} konstytucji, które opisali w tej samej wersji (kappa {f3(ty["kappa"])}). Udział głowy państwa w naszym modelu maleje zgodnie z ich typem: prezydenckie {pct(ty["hs_wg_typu_cheibub"]["prezydencki"])}, półprezydenckie {pct(ty["hs_wg_typu_cheibub"]["polprezydencki"])}, parlamentarne {pct(ty["hs_wg_typu_cheibub"]["parlamentarny"])}.</p></div>
<div class="box"><h3>Indeksy zewnętrzne</h3><p class="note">Niezależność sądów: korelacja rang z indeksem Meltona i Ginsburga (2014) ρ = {f3(sd["indeks_vs_melton_ginsburg"]["rho"])} (95%: {f3(sd["indeks_vs_melton_ginsburg"]["ci95"][0])}–{f3(sd["indeks_vs_melton_ginsburg"]["ci95"][1])}, {sd["indeks_vs_melton_ginsburg"]["n"]} konstytucji): umiarkowana, bo ich indeks dotyczy sądu najwyższego, a nasz głównie TK i rady sądownictwa.
Siła władzy wykonawczej: z indeksem CCP (7 uprawnień) nasz udział głowy państwa i rządu koreluje słabo, ρ = {f3(wy["udzial_wykonawczej_vs_indeks"]["rho"])}. Ten indeks liczy uprawnienia całej władzy wykonawczej (także premiera) i prawie nie różnicuje typów ustroju (średnio {f3(wy["srednia_indeksu_wg_typu"].get("prezydencki"))} w prezydenckich, {f3(wy["srednia_indeksu_wg_typu"].get("monarchia_parlamentarna"))} w monarchiach parlamentarnych), więc mierzy co innego niż podział siły między organy.</p></div></div>'''
    if W.get("wrazliwosc"):
        wr = W["wrazliwosc"]
        vrows = "".join(f'<tr><td>{escape(meta["variants"][v])}</td><td class="n">{str(x["spearman_z_bazowym"]["rho"]).replace(".", ",")}</td><td class="n">{pl["warianty"][v]["rank"] if pl and pl.get("warianty", {}).get(v) else "–"}</td></tr>' for v, x in wr["warianty"].items())
        trust += f'''<div class="box"><h3>Wrażliwość na założenia</h3><p class="note">Ranking siły głowy państwa policzony przy innych założeniach. Korelacja rang z modelem bazowym jest wysoka, ale pojedyncze miejsce przesuwa się zwykle o {wr["mediana_rozpietosci_miejsca"]:.0f} pozycji, więc podajemy przedział. Polska: {pl["rank_range"][0]}.–{pl["rank_range"][1]}. miejsce z {n}.</p>
<div class="tablewrap"><table class="w"><thead><tr><th>Wariant</th><th>korelacja z bazowym</th><th>miejsce Polski</th></tr></thead><tbody><tr class="pl"><td>Model bazowy</td><td class="n">1</td><td class="n">{pl["warianty"]["bazowy"]["rank"] if pl else "–"}</td></tr>{vrows}</tbody></table></div></div>'''

    opts = "".join(f'<option value="{k}"{" selected" if k == "PL" else ""}>{escape(m["name"])}{"" if m["ranked"] else " (niepełne)"}</option>' for k, m in client["countries"].items())
    dec_opts = "".join(f'<option value="{d}">{escape(t)}</option>' for d, t in meta["decisions"].items())
    grp_opts = '<option value="all">wszystkie</option><option value="eu">Unia Europejska</option>' + "".join(f'<option value="{t}">{escape(l)}</option>' for t, l in meta["types"].items() if types.get(t))
    rr_txt = f"{pl['rank_range'][0]}–{pl['rank_range'][1]}" if pl and pl.get("rank_range") else "–"
    hero = (f'<div class="w-hero"><div><b>{len(C)}</b><span>konstytucji z modelem decyzji; {n} z co najmniej {meta["min_decisions"]} kompletnymi decyzjami w rankingach</span></div>'
            f'<div><b>{pct(pl["profile"]["HS"]) if pl else "–"}</b><span>średni udział Prezydenta RP w 11 decyzjach{f"; {pl_rank}. miejsce z {n}" if pl_rank else ""}</span></div>'
            f'<div><b>{pct(hs_med)}</b><span>mediana udziału głowy państwa na świecie</span></div>'
            f'<div><b>{rr_txt}</b><span>miejsce Prezydenta RP przy różnych założeniach modelu (z {n})</span></div></div>')

    body = f'''<p class="crumbs">Władza</p><h1>Kto rządzi, kto blokuje</h1>
<p class="sub">Jak konstytucje dzielą decyzje między parlament, głowę państwa, rząd, naród i sądy. Każdą z 11 kluczowych decyzji (ustawa, budżet, zmiana konstytucji, powołanie i odwołanie rządu, rozwiązanie parlamentu, sędziowie TK, stan nadzwyczajny, wojna, umowy, usunięcie głowy państwa) opisujemy jako grę: kto musi się zgodzić i jaką większością. Z tego liczymy udział siły każdego organu (indeks Shapleya-Shubika), kto ma weto i jaka mniejszość w parlamencie wystarczy do blokady.</p>
{hero}
<p><a class="button" href="symulator.html">Symulator reform dla Polski →</a> <a href="en.html" lang="en">English summary</a> · Zmień jedną regułę (weto, Senat, wybór TK, KRS…) i zobacz, jak przesuwa się siła i kto mógłby przejąć instytucje.</p>
<h2 id="panstwo">Państwo</h2>
<div class="controls"><label>Państwo<select id="kraj">{opts}</select></label></div>
<div class="box" id="kraj-out"></div>
<h2>Porównanie</h2>
<div class="box"><h3>Polska, Unia i świat</h3><p class="note">Średni udział organów w decyzjach; tylko państwa w rankingach.</p>
<div class="tablewrap"><table class="w"><thead><tr><th></th><th>Podział siły</th><th>Głowa państwa</th><th>Rząd</th><th>Parlament</th></tr></thead><tbody>{cmp_rows}</tbody></table></div>{legend(meta)}</div>
<div class="box"><h3>Typy ustroju</h3><p class="note">Typ wynika z tekstu (kto kieruje rządem i przed kim rząd odpowiada) oraz z kodowania CCP, czy głowę państwa wybierają obywatele. Półprezydencki „premierowski”: rząd odpowiada tylko przed parlamentem (Polska, Francja); „prezydencko-parlamentarny”: także przed prezydentem (Rosja).</p>
<div class="tablewrap"><table class="w"><thead><tr><th>Typ</th><th>państw</th><th>Średni podział siły</th><th>Głowa państwa</th><th>Parlament</th></tr></thead><tbody>{type_rows}</tbody></table></div></div>
<div class="box"><h3>Ranking: od najsilniejszej głowy państwa</h3><p class="note">Kliknij nagłówek, aby sortować; nazwa państwa otwiera jego profil. Najsilniejsze: {", ".join(escape(m["name"]) + " " + pct(m["profile"]["HS"]) for _, m in top_hs)}.</p>
<div class="tablewrap"><table class="w" id="rank"><thead><tr><th data-s="0">Państwo</th><th data-s="1">Typ</th><th data-s="2">Podział siły</th><th data-s="3">Głowa państwa</th><th data-s="4">Rząd</th><th data-s="5">Parlament</th><th data-s="6">HHI</th><th data-s="7">decyzji</th></tr></thead><tbody>{rank_rows}</tbody></table></div></div>
<h2>Decyzja po decyzji</h2>
<div class="controls"><label>Decyzja<select id="decyzja">{dec_opts}</select></label><label>Grupa państw<select id="grupa">{grp_opts}</select></label></div>
<div class="box" id="decyzja-out"></div>
<h2>Kto kogo blokuje i kontroluje</h2>
<div class="two"><div class="box"><h3>Weto</h3><p class="note">Odsetek państw, w których organ z wiersza jest niezbędny (ma weto) w co najmniej jednej decyzji, w której uczestniczy organ z kolumny.</p><div class="tablewrap">{veto_tbl}</div></div>
<div class="box"><h3>Powoływanie i odwoływanie</h3><p class="note">Kto może usunąć lub wybrać inny organ; odsetek państw w rankingach.</p>{ctl_tbl}</div></div>
<div class="box"><h3>Hamulce i wzmocnienia</h3>{ind_tbl}</div>
<h2 id="przejecie">Odporność na przejęcie</h2>
<div class="box"><h3>Jaki obóz sam obsadzi instytucję</h3><p class="note">Dla każdej instytucji opisanej w konstytucji: najsłabszy układ polityczny, który sam wybiera wszystkich jej członków (przy 3/5 i 2/3 mandatów razem z głową państwa, jeśli ona współdecyduje). „Decyduje ustawa”: konstytucja nie mówi, kto wybiera, więc wystarczy większość ustawodawcza. „Poza zasięgiem samej polityki”: współdecydują sędziowie, naród w referendum albo opozycja. Odsetek państw w rankingach, które mają daną instytucję w konstytucji.</p>
<div class="tablewrap">{cap_tbl}</div></div>
<div class="two"><div class="box"><h3>Najbardziej odporne</h3><p class="note">Udział instytucji (bez zmiany konstytucji), których nie przejmie zwykła większość nawet z głową państwa. Polska: {pct(res["PL"]) if "PL" in res else "–"}, średnia UE: {pct(statistics.fmean(res_eu)) if res_eu else "–"}.</p>
<table class="w"><tbody>{"".join(f'<tr><td><a class="cty" href="#{k}" data-k="{k}">{escape(C[k]["name"])}</a></td><td class="n">{pct(res[k])}</td></tr>' for k in res_top)}</tbody></table></div>
<div class="box"><h3>Wszystko w zasięgu zwykłej większości</h3><p class="note">Państwa (co najmniej 3 instytucje w konstytucji), w których żadnej z nich nie chroni większość kwalifikowana ani udział sędziów: {len(res_low)}.</p><p class="src">{", ".join(f'<a class="cty" href="#{k}" data-k="{k}">{escape(C[k]["name"])}</a>' for k in res_low)}</p></div></div>
<h2 id="sady">Niezależność sądów w tekście konstytucji</h2>
<div class="two"><div class="box"><h3>10 gwarancji: jak często i czy ma je Polska</h3><p class="note">Indeks to odsetek gwarancji zapisanych w konstytucji (spośród tych, które jej dotyczą, np. bez TK nie liczymy gwarancji TK). Polska: {js.get("PL", 0):.0f} na 100, mediana świata {statistics.median(js.values()):.0f}, średnia UE {statistics.fmean(js[k] for k in j_eu):.0f}.</p>
<table class="w"><thead><tr><th>Gwarancja</th><th>konstytucji</th><th>Polska</th></tr></thead><tbody>{jcomp}</tbody></table></div>
<div class="box"><h3>Unia Europejska</h3><div class="tablewrap" style="max-height:420px"><table class="w"><thead><tr><th>Państwo</th><th>indeks</th></tr></thead><tbody>{j_eu_rows}</tbody></table></div></div></div>
<h2 id="zaufanie">Na ile ufać tym liczbom</h2>
{trust}
<h2>Metoda i ograniczenia</h2>
<div class="box"><ul class="flags" style="color:inherit;font-size:14px">
<li><b>Dane.</b> Wartości pochodzą z 49 tematów wariantów (ekstrakcja modelem językowym z angielskich wydań Constitute, cytat sprawdzany w kodzie, ręczne korekty opisane w <code>korekty.json</code>). Tylko tekst konstytucji: bez ustaw, regulaminów i praktyki.</li>
<li><b>Gra decyzyjna.</b> Organy jednoosobowe (głowa państwa, rząd, naród w referendum, sądy) są graczami. Izba to duża grupa równych posłów: weto, które izba odrzuca większością 3/5, daje głowie państwa „okno” między 50% a 60% mandatów, czyli 10% siły w tej decyzji. Udziały sumują się do 100% w każdej decyzji; profil państwa to średnia z decyzji.</li>
<li><b>Uproszczenia.</b> Organy traktujemy jako jednolite: model nie zna składu partyjnego, koalicji ani kohabitacji. Obie izby głosują tą samą większością. Gdy sędziów TK wybiera kilka organów, każdy dostaje równy udział (tak samo przy wspólnym wyborze i przy podziale puli). Gdy głowa państwa działa „na wniosek rządu”, decyzję przypisujemy rządowi; kontrasygnata dodaje rząd jako drugi niezbędny organ.</li>
<li><b>Uzupełnienia z CCP.</b> Gdy z tekstu nie odczytaliśmy liczby izb albo progu odrzucenia weta, bierzemy je z kodowania ekspertów CCP (wersja 5) i zaznaczamy to przy decyzji. Sposób wyboru głowy państwa do typologii też pochodzi z CCP. Źródło: Elkins i Ginsburg, Characteristics of National Constitutions v5 (2025).</li>
<li><b>Braki.</b> „Nie wynika z tekstu” nie znaczy „nie ma”. Przyjęte założenia są wypisane przy każdej decyzji. Do rankingów trafiają państwa z co najmniej {meta["min_decisions"]} decyzjami bez niewiadomych w strukturze.</li>
<li><b>Mniejszość blokująca</b> to najmniejszy odsetek mandatów pierwszej izby, który zatrzyma decyzję, gdy wszystkie inne organy są za. „Gdy głowa państwa przeciw”: ile potrzeba do odrzucenia jej sprzeciwu.</li>
</ul><p class="note">Dane: <code>dane/wladza_kraje.csv</code>, <code>dane/wladza_decyzje.csv</code>, <code>dane/wladza_przejecie.csv</code>, <code>dane/wladza_sady.csv</code>, <code>dane/wladza_warianty.csv</code>, <code>dane/wladza_walidacja_pola.csv</code> w repozytorium. Stan danych: {DATA_DATE}.</p></div>
<script type="application/json" id="wdata">{json.dumps(client, ensure_ascii=False, separators=(",", ":")).replace("<", "\\u003c")}</script>
<script>{JS.replace("__ORDER__", json.dumps(ORDER)).replace("__COLORS__", json.dumps(COLORS)).replace("__TOPICS__", json.dumps(TOPIC_PAGE))}</script>'''
    html = page("Władza: kto rządzi, kto blokuje", body, description="Podział decyzji między parlament, głowę państwa, rząd, naród i sądy w 188 konstytucjach: udział siły, weto, mniejszość blokująca.",
                css="../panstwa/style.css", current="wladza").replace("</head>", f"<style>{CSS}</style></head>")
    (HERE / "index.html").write_text(html, encoding="utf-8")
    sim = page("Symulator reform: władza w Konstytucji RP", symulator.body(meta, COLORS), description="Zmień regułę Konstytucji RP (weto, Senat, wybór TK, KRS) i zobacz, jak zmienia się podział siły i odporność instytucji.",
               css="../panstwa/style.css", current="wladza").replace("</head>", f"<style>{CSS}{symulator.SIM_CSS}</style></head>")
    (HERE / "symulator.html").write_text(sim, encoding="utf-8")
    print(json.dumps({"countries": len(C), "ranked": n, "types": types, "pl": pl and pl["profile"]}, ensure_ascii=False))


if __name__ == "__main__":
    main()
