#!/usr/bin/env python3
"""Reform simulator for Poland (analysis/wladza/symulator.html): change one rule of the Constitution and see how the
Shapley-Shubik shares, veto players, blocking minorities and the capture of institutions change.

The decision games are written out in JavaScript for Poland only; with every switch at "obecnie" they reproduce the
games model.py builds for PL (checked by test_wladza.py through Node). Called from build.py.
"""
from __future__ import annotations

import json
from html import escape

# switch -> (label, [(value, label)], default). The first option is the current Constitution.
KNOBS = [
    ("weto", "Weto Prezydenta wobec ustaw", [("3/5", "Sejm odrzuca 3/5 głosów (obecnie, art. 122 ust. 5)"), ("2/3", "Sejm odrzuca 2/3 głosów"),
                                            ("1/2", "Sejm odrzuca bezwzględną większością"), ("brak", "Brak weta"), ("absolutne", "Weto nie do odrzucenia")]),
    ("senat", "Senat wobec ustaw", [("zawieszajace", "Sprzeciw, który Sejm odrzuca bezwzględną większością (obecnie, art. 121)"),
                                   ("bezwzgledne", "Senat musi się zgodzić (jak w USA czy we Włoszech)"), ("brak", "Bez Senatu")]),
    ("budzet", "Inicjatywa budżetowa", [("rzad", "Wyłącznie Rada Ministrów (obecnie, art. 221)"), ("kazdy", "Także posłowie")]),
    ("premier", "Powołanie premiera", [("obecnie", "Prezydent wskazuje, ale Sejm może wybrać sam (obecnie, art. 154–155)"),
                                       ("prezydent", "Tylko kandydat Prezydenta, Sejm zatwierdza"), ("sejm", "Sejm wybiera, Prezydent tylko powołuje")]),
    ("odwolanie", "Odwołanie rządu", [("sejm", "Tylko Sejm, wotum konstruktywne (obecnie, art. 158)"), ("takze_prezydent", "Także Prezydent może odwołać premiera")]),
    ("rozwiazanie", "Rozwiązanie Sejmu", [("obecnie", "Prezydent w dwóch przypadkach albo Sejm sam 2/3 (obecnie, art. 98, 155, 225)"),
                                         ("na_wniosek", "Prezydent tylko na wniosek premiera"), ("sam_sejm", "Tylko samorozwiązanie 2/3")]),
    ("egzekutywa", "Stan nadzwyczajny, wojna, umowy", [("razem", "Prezydent z rządem (obecnie, kontrasygnata, art. 144)"), ("rzad", "Decyduje rząd, Prezydent formalnie")]),
    ("tk", "Wybór sędziów TK", [("1/2", "Sejm zwykłą większością (obecnie, art. 194)"), ("3/5", "Sejm większością 3/5"), ("2/3", "Sejm większością 2/3"),
                               ("trzy", "Po 1/3: Sejm, Prezydent, zgromadzenie sędziów (jak we Włoszech)")]),
    ("krs", "Wybór sędziów do KRS", [("ustawa", "Konstytucja nie mówi kto: decyduje ustawa (obecnie, art. 187)"), ("sedziowie", "Wybierają sędziowie (zapis w konstytucji)"),
                                    ("3/5", "Sejm większością 3/5")]),
    ("konstytucja", "Zmiana konstytucji", [("obecnie", "Sejm 2/3 i Senat (obecnie, art. 235)"), ("referendum", "Dodatkowo zawsze referendum"), ("3/5", "Sejm i Senat 3/5")]),
    ("lud", "Obywatelskie referendum ustaw", [("nie", "Brak (obecnie)"), ("tak", "Obywatele mogą poddać ustawę pod referendum (górna granica)")]),
]
PRESETS = [("obecna", "Obecna konstytucja", {}),
           ("P04", "P04: ochrona sądów przed przejęciem", {"tk": "2/3", "krs": "sedziowie"}),
           ("P20", "P20: obywatelskie referendum ustaw", {"lud": "tak"}),
           ("P24", "P24: wariant parlamentarny", {"weto": "brak", "egzekutywa": "rzad", "rozwiazanie": "na_wniosek"}),
           ("prez", "Kierunek prezydencki", {"weto": "2/3", "premier": "prezydent", "odwolanie": "takze_prezydent", "egzekutywa": "razem"})]

JS = r"""
const SHORT=__SHORT__, DEC=__DEC__, ORDER=['L1','L2','G','HS','P','CC','J'], COL=__COL__, KNOBS=__KNOBS__, PRESETS=__PRESETS__;
const NAMES={L1:'Sejm',L2:'Senat',G:'Rada Ministrów',HS:'Prezydent',P:'Naród',CC:'TK',J:'Sądy'};
// ---- Shapley-Shubik with oceanic chambers (same mathematics as model.py) ----
const comb=(n,k)=>{let r=1;for(let i=1;i<=k;i++)r=r*(n-k+i)/i;return r;};
function tau(cls,S){let b=Infinity;for(const c of cls){if(c.req.every(a=>S.has(a))){const v=Object.values(c.ch);b=Math.min(b,v.length?Math.max(...v):0);}}return b;}
function ip(s,m,a,b){a=Math.max(0,Math.min(1,a));b=Math.max(0,Math.min(1,b));if(b<=a)return 0;let r=0;for(let j=0;j<=m;j++)r+=comb(m,j)*((j%2)?-1:1)*(b**(s+j+1)-a**(s+j+1))/(s+j+1);return r;}
function subsets(xs){const out=[];for(let m=0;m<(1<<xs.length);m++)out.push(new Set(xs.filter((_,i)=>m>>i&1)));return out;}
function shapley(cls){const units=[...new Set(cls.flatMap(c=>c.req))].sort(),chs=[...new Set(cls.flatMap(c=>Object.keys(c.ch)))].sort(),n=units.length,out={};
 units.concat(chs).forEach(a=>out[a]=0);
 for(const i of units){const others=units.filter(u=>u!==i);for(const S of subsets(others)){const hi=tau(cls,S),S2=new Set(S);S2.add(i);const lo=tau(cls,S2);out[i]+=ip(S.size,n-1-S.size,lo,Math.min(hi,1));}}
 for(const S of subsets(units)){const t=tau(cls,S);if(!(t>0&&t<=1))continue;const at=new Set();
  for(const c of cls)if(c.req.every(a=>S.has(a))){const v=Object.values(c.ch);if(v.length&&Math.max(...v)===t)for(const[k,x]of Object.entries(c.ch))if(x===t)at.add(k);}
  let bind=[...at].filter(ch=>tau(cls.filter(c=>c.ch[ch]!==t),S)>t);if(!bind.length)bind=[...at];
  const w=t**S.size*(1-t)**(n-S.size);bind.forEach(ch=>out[ch]+=w/bind.length);}
 const tot=Object.values(out).reduce((a,b)=>a+b,0);for(const k in out)out[k]/=tot;return out;}
const veto=cls=>{const sets=cls.map(c=>new Set([...c.req,...Object.keys(c.ch)]));return [...sets[0]].filter(a=>sets.every(s=>s.has(a)));};
function blocking(cls,without){const units=new Set(cls.flatMap(c=>c.req));(without||[]).forEach(a=>units.delete(a));let t=Infinity;
 for(const c of cls)if(c.req.every(a=>units.has(a)))t=Math.min(t,'L1' in c.ch?c.ch.L1:0);return t===Infinity?null:(t>0?1-t:0);}
// ---- Poland: decision games for a set of switches ----
function games(k){const D={},T=2/3;
 const base=k.senat==='bezwzgledne'?[{req:[],ch:{L1:.5,L2:.5}}]:k.senat==='brak'?[{req:[],ch:{L1:.5}}]:[{req:[],ch:{L1:.5,L2:.5}},{req:[],ch:{L1:.5}}];
 const withVeto=(b,v)=>{if(v==='brak')return b.map(c=>({req:[...c.req],ch:{...c.ch}}));const q={'3/5':.6,'2/3':T,'1/2':.5}[v];
  const out=b.map(c=>({req:[...c.req,'HS'],ch:{...c.ch}}));if(v==='absolutne')return out;
  return out.concat(b.map(c=>{const ch={};for(const[x,y]of Object.entries(c.ch))ch[x]=Math.max(y,q);return{req:[...c.req],ch};}));};
 let law=withVeto(base,k.weto);if(k.lud==='tak')law=law.map(c=>({req:[...c.req,'P'],ch:c.ch}));D.ustawa=law;
 let bud=withVeto(base,'brak');
 if(k.budzet==='rzad')bud=bud.map(c=>({req:[...c.req,'G'],ch:c.ch}));D.budzet=bud;
 const ct=k.konstytucja==='3/5'?.6:T,cch=k.senat==='brak'?{L1:ct}:{L1:ct,L2:ct};D.konstytucja=[{req:k.konstytucja==='referendum'?['P']:[],ch:cch}];
 D.powolanie_rzadu=k.premier==='sejm'?[{req:[],ch:{L1:.5}}]:k.premier==='prezydent'?[{req:['HS'],ch:{L1:.5}}]:[{req:['HS'],ch:{L1:.5}},{req:[],ch:{L1:.5}}];
 D.odwolanie_rzadu=k.odwolanie==='takze_prezydent'?[{req:[],ch:{L1:.5}},{req:['HS'],ch:{}}]:[{req:[],ch:{L1:.5}}];
 D.rozwiazanie=k.rozwiazanie==='na_wniosek'?[{req:['G','HS'],ch:{}},{req:[],ch:{L1:T}}]:k.rozwiazanie==='sam_sejm'?[{req:[],ch:{L1:T}}]:[{req:['HS'],ch:{}},{req:[],ch:{L1:T}}];
 const tk={'1/2':[{req:[],ch:{L1:.5}}],'3/5':[{req:[],ch:{L1:.6}}],'2/3':[{req:[],ch:{L1:T}}],'trzy':[{req:['HS','J'],ch:{L1:.5}}]}[k.tk];D.sedziowie_tk=tk;
 const ex=k.egzekutywa==='rzad'?['G']:['G','HS'];
 D.stan_nadzwyczajny=[{req:ex,ch:{L1:.5}}];D.wojna=[{req:ex,ch:{L1:.5}}];D.ratyfikacja=[{req:ex,ch:{L1:T}}];
 D.usuniecie_glowy=[{req:['J'],ch:{L1:T}}];return D;}
function capture(k){const L={S1:'większość w Sejmie',S2:'większość + Prezydent',S3:'3/5 w Sejmie (+ Prezydent, jeśli współdecyduje)',S4:'2/3 w Sejmie (+ Prezydent, jeśli współdecyduje)',poza:'nie przejmie sama polityka',ustawa:'większość ustawowa (zależy od weta)'};
 const lvl=(sel,thr)=>{if(sel.some(a=>a==='J'||a==='P'))return'poza';const needHS=sel.includes('HS');for(const[s,q,h]of[['S1',.5,false],['S2',.5,true],['S3',.6,true],['S4',2/3,true]])if(thr<=q+1e-9&&(!needHS||h))return s;return'poza';};
 const r=[];const tk={'1/2':[['L1'],.5],'3/5':[['L1'],.6],'2/3':[['L1'],2/3],'trzy':[['L1','HS','J'],.5]}[k.tk];
 r.push(['Trybunał Konstytucyjny',lvl(...tk)]);
 r.push(['KRS (sędziowie-członkowie)',k.krs==='ustawa'?'ustawa':k.krs==='sedziowie'?'poza':lvl(['L1'],.6)]);
 r.push(['Rzecznik Praw Obywatelskich',lvl(['L1'],.5)]);r.push(['Prezes NBP',lvl(['L1','HS'],.5)]);
 r.push(['Zmiana konstytucji',k.konstytucja==='referendum'?'poza':lvl(['L1'],k.konstytucja==='3/5'?.6:2/3)]);
 return r.map(([n,l])=>[n,l,L[l]]);}
function analyse(k){const D=games(k),res={},prof={};ORDER.forEach(o=>prof[o]=0);const n=Object.keys(D).length;
 for(const[d,cls]of Object.entries(D)){const s=shapley(cls);res[d]={s,veto:veto(cls),b:blocking(cls),bh:cls.some(c=>c.req.includes('HS'))?blocking(cls,['HS']):null};for(const[o,v]of Object.entries(s))prof[o]+=v/n;}
 return{res,prof,cap:capture(k)};}
if(typeof module!=='undefined'){module.exports={games,analyse,shapley};}
else{
const esc=v=>String(v??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const pct=x=>(Math.round(x*1000)/10).toLocaleString('pl-PL')+'%';
const pp=x=>(x>0?'+':'')+(Math.round(x*1000)/10).toLocaleString('pl-PL')+' pp';
const stack=s=>'<div class="stack">'+ORDER.filter(o=>s[o]>0.0005).map(o=>'<i style="width:'+(s[o]*100)+'%;background:'+COL[o]+'" title="'+esc(NAMES[o]+': '+pct(s[o]))+'"></i>').join('')+'</div>';
const blk=x=>x==null?'–':x===0?'Sejm nie blokuje':'ponad '+pct(x).replace(',0%','%');
const def={};KNOBS.forEach(([k,,opts])=>def[k]=opts[0][0]);const base=analyse(def);
const form=document.getElementById('knobs'),out=document.getElementById('sim-out');
form.innerHTML='<div class="presets">'+PRESETS.map(([id,l])=>'<button type="button" class="button preset" data-p="'+id+'">'+esc(l)+'</button>').join('')+'</div>'+
 KNOBS.map(([k,l,opts])=>'<label class="knob"><span>'+esc(l)+'</span><select name="'+k+'">'+opts.map(([v,t],i)=>'<option value="'+v+'">'+esc(t)+'</option>').join('')+'</select></label>').join('');
const read=()=>{const k={};KNOBS.forEach(([n])=>k[n]=form.elements[n].value);return k;};
function render(){const k=read(),a=analyse(k);const changed=KNOBS.filter(([n,,o])=>k[n]!==o[0][0]).length;
 let h='<div class="two"><div><h3>Podział siły: obecnie</h3>'+stack(base.prof)+'<p class="legend">'+ORDER.filter(o=>base.prof[o]>0.0005).map(o=>'<span><i style="background:'+COL[o]+'"></i>'+esc(NAMES[o])+' '+pct(base.prof[o])+'</span>').join('')+'</p></div>'+
  '<div><h3>Po zmianie'+(changed?' ('+changed+')':'')+'</h3>'+stack(a.prof)+'<p class="legend">'+ORDER.filter(o=>a.prof[o]>0.0005).map(o=>'<span><i style="background:'+COL[o]+'"></i>'+esc(NAMES[o])+' '+pct(a.prof[o])+(Math.abs(a.prof[o]-base.prof[o])>0.0005?' <b>('+pp(a.prof[o]-base.prof[o])+')</b>':'')+'</span>').join('')+'</p></div></div>';
 h+='<div class="tablewrap"><table class="w"><thead><tr><th>Decyzja</th><th>Podział siły po zmianie</th><th>Weto</th><th>Mniejszość blokująca w Sejmie</th></tr></thead><tbody>';
 for(const[d,x]of Object.entries(a.res)){const b0=base.res[d];const diff=ORDER.some(o=>Math.abs((x.s[o]||0)-(b0.s[o]||0))>0.0005);
  h+='<tr'+(diff?' class="pl"':'')+'><td><b>'+esc(DEC[d])+'</b></td><td>'+stack(x.s)+'<div class="src">'+ORDER.filter(o=>x.s[o]>0.0005).map(o=>esc(NAMES[o])+' '+pct(x.s[o])).join(' · ')+'</div></td><td>'+x.veto.map(o=>'<span class="tag veto">'+esc(NAMES[o])+'</span>').join('')+'</td><td class="n">'+blk(x.b)+(x.bh!=null&&x.bh!==x.b?'<br><span class="src">gdy Prezydent przeciw: '+(x.bh===null?'nie do odrzucenia':blk(x.bh))+'</span>':'')+'</td></tr>';}
 h+='</tbody></table></div><h3 style="margin-top:16px">Kto przejmie instytucje</h3><table class="w"><thead><tr><th>Instytucja</th><th>Najsłabszy obóz, który obsadzi ją sam</th><th>Obecnie</th></tr></thead><tbody>'+
  a.cap.map((r,i)=>'<tr'+(r[1]!==base.cap[i][1]?' class="pl"':'')+'><td>'+esc(r[0])+'</td><td>'+esc(r[2])+'</td><td class="src">'+esc(base.cap[i][2])+'</td></tr>').join('')+'</tbody></table>';
 out.innerHTML=h;}
form.addEventListener('change',render);
form.addEventListener('click',e=>{const b=e.target.closest('button.preset');if(!b)return;const p=PRESETS.find(x=>x[0]===b.dataset.p);KNOBS.forEach(([n,,o])=>form.elements[n].value=(p[2][n]||o[0][0]));render();});
render();}
"""


def js(meta, colors) -> str:
    return (JS.replace("__SHORT__", json.dumps(meta["short"], ensure_ascii=False)).replace("__DEC__", json.dumps(meta["decisions"], ensure_ascii=False))
            .replace("__COL__", json.dumps(colors)).replace("__KNOBS__", json.dumps(KNOBS, ensure_ascii=False))
            .replace("__PRESETS__", json.dumps(PRESETS, ensure_ascii=False)))


def body(meta, colors) -> str:
    return f'''<p class="crumbs"><a href="index.html">Władza</a> / Symulator</p><h1>Symulator reform: co zmieni jedna reguła?</h1>
<p class="sub">Zmień zasadę Konstytucji RP i zobacz, jak przesuwa się siła Sejmu, Senatu, Prezydenta i rządu w 11 decyzjach, kto zyskuje weto i jaka mniejszość wystarczy do blokady. Na dole: kto mógłby sam obsadzić Trybunał, KRS, RPO i NBP. Gotowe zestawy odpowiadają propozycjom z widoku <a href="../polska/index.html">Dla Polski</a>.</p>
<form class="box knobs" id="knobs" onsubmit="return false"></form>
<div class="box" id="sim-out"></div>
<div class="box"><h3>Jak to liczymy</h3><ul class="flags" style="color:inherit;font-size:14px">
<li>Ten sam model co na stronie <a href="index.html">Władza</a>: indeks Shapleya-Shubika z izbami jako dużymi grupami posłów. Ustawienie „obecnie” daje dokładnie wyniki dla Polski z tej strony.</li>
<li>Model zna tylko reguły: kto musi się zgodzić i jaką większością. Nie zna partii ani praktyki. Obywatelskie referendum liczymy tak, jakby każda ustawa mogła trafić pod głosowanie, więc to górna granica.</li>
<li>„Kto przejmie instytucje”: najsłabszy obóz polityczny (większość w Sejmie, z Prezydentem lub bez, 3/5, 2/3), który sam wybiera wszystkich członków. Senat pomijamy (np. zgoda Senatu na wybór RPO).</li>
</ul></div>
<script>{js(meta, colors)}</script>'''


SIM_CSS = """.knobs{display:grid;grid-template-columns:repeat(auto-fill,minmax(260px,1fr));gap:12px 16px}
.knob{display:flex;flex-direction:column;gap:4px;font-size:13px;color:var(--muted)}.knob span{font-weight:600;color:var(--ink)}
.knob select{font:inherit;padding:6px 8px;width:100%}
.presets{grid-column:1/-1;display:flex;flex-wrap:wrap;gap:8px}.presets .button{font-size:13px;padding:6px 10px;cursor:pointer}"""
