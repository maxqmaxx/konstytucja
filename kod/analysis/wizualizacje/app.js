/* Offline visual exploration of editorial relationships and lexical measurements. */
(() => {
  'use strict';
  const D = JSON.parse(document.querySelector('#gallery-data').textContent);
  const $ = selector => document.querySelector(selector);
  const NS = 'http://www.w3.org/2000/svg';
  const colors = ['#156a56', '#ab603e', '#436b88', '#856b8a', '#bd913c', '#638354', '#637e82', '#966c69', '#436756'];
  const cats = Object.keys(D.categories);
  const clauses = new Map(D.clauses.map(c => [c.id, c]));
  const docs = D.corpus.documents;
  const docMap = new Map(docs.map(d => [d.id, d]));
  const countryNames = new Map(D.clauses.map(c => [c.country_code, c.country]));
  const countries = [...countryNames].sort((a, b) => a[1].localeCompare(b[1], 'pl'));
  const shortCats = ['Ciekawe', 'Oryginalność', 'Kontrowersje', 'Rola w ustroju', 'Ryzyka', 'Zaskoczenie', 'Potencjał państwa', 'Władza przywódcy', 'Trudna interpretacja'];
  const catColor = key => colors[cats.indexOf(key)];
  const views = [
    {id:'konstelacja', name:'Konstelacja przepisów', title:'Jeden przepis. Wiele powiązań.', description:'Państwo prowadzi do konkretnego przepisu, a przepis do kategorii redakcyjnych. Wybierz węzeł, by zobaczyć jego kontekst.', badge:'RELACJE Z ATLASU', note:'Krawędzie oznaczają przypisanie przepisu do państwa lub kategorii. Układ nie przedstawia odległości geograficznej ani wpływu historycznego.'},
    {id:'portrety', name:'Portrety państw', title:'Co opisaliśmy dla danego państwa?', description:'Macierz pokazuje liczbę wybranych przepisów w każdej kategorii. Kliknij komórkę, aby przeczytać odpowiadające jej opisy.', badge:'WYBÓR REDAKCYJNY', note:'Wartości dotyczą wyłącznie 130 wybranych przepisów, a nie wszystkich rozwiązań w konstytucjach. Jeden przepis może należeć do kilku kategorii. Zero oznacza brak pozycji w wyborze.'},
    {id:'splot', name:'Splot kategorii', title:'Które kategorie spotykają się w przepisach?', description:'Dziewięć kategorii i ich przecięcia. Grubszy łuk oznacza więcej opisów przypisanych jednocześnie do obu kategorii.', badge:'WSPÓŁWYSTĘPOWANIE', note:'Każdy łuk liczy wspólne przepisy, nie kraje. Kategorie nakładają się, więc sumowanie połączeń nie daje liczby wszystkich opisów.'},
    {id:'mechanizmy', name:'Państwo a przywódca', title:'Zdolność działania i koncentracja władzy', description:'Dwie osobne kategorie redakcyjne tworzą cztery pola. Każdy punkt to opisany przepis, a nie ocena całego państwa.', badge:'DWIE OSOBNE KATEGORIE', note:'Pola oznaczają wyłącznie obecność kategorii „Potencjał państwa i społeczeństwa” oraz „Koncentracja władzy przywódcy”. Położenie punktu wewnątrz pola nie jest wynikiem punktowym.'},
    {id:'czas', name:'Oś czasu wydań', title:'Dokument ma datę. Przepis ma kontekst.', description:'Daty przyjęcia i rewizji dokumentów, z których pochodzą opisy atlasu. Wybierz dokument, aby zobaczyć przypisane mu przepisy.', badge:'METADANE WYDAWCÓW', note:'Oś dotyczy dokumentów, nie dat wejścia w życie poszczególnych przepisów. Linia do znacznika rewizji nie oznacza ciągłości obowiązywania. Nieznane daty są pokazane osobno.'},
    {id:'polska', name:'Inspiracje dla Polski', title:'Od zagranicznego przepisu do polskiej propozycji', description:'Śledź zapisane odniesienia: państwo → przepis → propozycja → artykuł Konstytucji RP użyty w porównaniu.', badge:'24 AUTORSKIE PROPOZYCJE', note:'Połączenie oznacza odniesienie redakcyjne. Nie dowodzi historycznego zapożyczenia ani prawnej równoważności. Polski artykuł to punkt porównania, a propozycja jest autorskim szkicem.'},
    {id:'sasiedztwo', name:'Sąsiedztwo tekstów', title:'Blisko w słowach. Czy blisko w rozwiązaniach?', description:'Mapa angielskich tekstów Constitute. Wybierz dokument, poznaj jego pięciu najbliższych sąsiadów i porównaj wspólne terminy oraz fragmenty.', badge:'ANALIZA AUTOMATYCZNA', auto:true, note:'Pozycje są dwuwymiarowym przybliżeniem podobieństwa TF-IDF. Sąsiedzi i wyniki są liczeni w pełnej przestrzeni, na całym korpusie. Filtry ograniczają widoczność, nie zmieniają obliczeń. Grupy opisują słownictwo, a nie rodziny prawne.'},
    {id:'tematy', name:'Profile tematów', title:'Te same słowniki. Różne profile tekstu.', description:'Porównaj do trzech tekstów według siedmiu zestawów wyrażeń. Wybierz słupek, aby sprawdzić dopasowania w kontekście.', badge:'ANALIZA AUTOMATYCZNA', auto:true, note:'Trafienia słownikowe nie mierzą siły ochrony ani skuteczności regulacji. Wartość na 10 tys. słów uwzględnia długość tekstu. Brak trafienia nie oznacza braku tematu.'}
  ];
  let current = 0;
  let state = {};
  let tableRows = [];
  let tableHeaders = [];
  let tableActions = [];
  let rowKind = 'clause';
  const svg = $('#chart');
  const fmt = value => Number(value).toLocaleString('pl-PL', {maximumFractionDigits:2});
  const esc = value => String(value ?? '').replace(/[&<>"']/g, char => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[char]));
  const norm = value => String(value).toLowerCase().replace(/ł/g,'l').normalize('NFD').replace(/[\u0300-\u036f]/g,'');
  const rootLink = path => '../../' + path;
  const statusLabel = status => ({source_in_force:'Według wydawcy: w mocy', historical_or_replaced:'Historyczne / zastąpione', draft:'Projekt'}[status] || status);
  const isHistorical = c => c.period.startsWith('historyczny');
  const statusMatch = (item, status) => !status || (status === 'history' ? (item.period ? isHistorical(item) : item.status === 'historical_or_replaced') : status === 'draft' ? (item.period === 'projekt' || item.status === 'draft') : item.period ? item.period === 'wydanie z archiwum' : item.status === 'source_in_force');
  const catLabel = key => shortCats[cats.indexOf(key)];

  function el(tag, attrs = {}, text, parent = svg) {
    const node = document.createElementNS(NS, tag);
    const presentation = {};
    if (tag === 'text') {
      presentation['font-family'] = 'Arial, sans-serif';
      presentation['font-size'] = attrs.class === 'small' ? 9 : attrs.class === 'minor' ? 10 : 11;
      presentation.fill = attrs.class === 'minor' ? '#5c706f' : '#19343d';
    }
    if (attrs.class === 'link') Object.assign(presentation, {fill:'none',stroke:'#bfd0be','stroke-opacity':.65});
    if (attrs.class === 'tick') Object.assign(presentation, {stroke:'#d9ded4','stroke-width':1});
    for (const [key,value] of Object.entries({...presentation,...attrs})) node.setAttribute(key,value);
    if (attrs.style) {
      for (const declaration of attrs.style.split(';')) {
        const separator=declaration.indexOf(':');if(separator<0)continue;
        const key=declaration.slice(0,separator).trim(),value=declaration.slice(separator+1).trim();
        if(['fill','stroke','stroke-width','stroke-opacity','fill-opacity','font-size','font-family'].includes(key))node.setAttribute(key,value);
        if(key==='font'){const font=value.match(/(\d+)px\s+(.+)/);if(font){node.setAttribute('font-size',font[1]);node.setAttribute('font-family',font[2]);}}
      }
    }
    if (text !== undefined) node.textContent = text;
    parent.append(node);
    return node;
  }
  function text(x,y,value,attrs={},parent=svg) { return el('text',{x,y,...attrs},value,parent); }
  const scroller = svg.closest('.chart-scroll');
  function stickyColumn(width,height='100%') { const g=el('g',{class:'sticky-col'}); el('rect',{x:-4,y:0,width:width+4,height,fill:'#fffefa','fill-opacity':.96},undefined,g); return g; }
  function syncSticky() { const g=svg.querySelector('.sticky-col'); if(!g||!scroller)return; svg.appendChild(g); const k=svg.viewBox.baseVal.width/Math.max(1,svg.getBoundingClientRect().width); g.setAttribute('transform',`translate(${(scroller.scrollLeft*k).toFixed(1)},0)`); }
  if(scroller) scroller.addEventListener('scroll',syncSticky,{passive:true});
  function interactive(node, label, handler) {
    node.classList.add('node');
    node.setAttribute('role','button'); node.setAttribute('tabindex','0'); node.setAttribute('aria-label',label);
    el('title',{},label,node);
    node.addEventListener('click',handler);
    node.addEventListener('keydown',event => { if (event.key === 'Enter' || event.key === ' ') { event.preventDefault(); handler(); } });
    return node;
  }
  function point(x,y,r,color,label,handler,shape='circle') {
    const g = el('g');
    if (shape === 'diamond') el('path',{d:`M${x} ${y-r-1}l${r+1} ${r+1}l${-r-1} ${r+1}l${-r-1} ${-r-1}Z`,fill:color,stroke:'#fffefa','stroke-width':1},undefined,g);
    else if (shape === 'square') el('rect',{x:x-r,y:y-r,width:r*2,height:r*2,rx:1,fill:color,stroke:'#fffefa','stroke-width':1},undefined,g);
    else el('circle',{cx:x,cy:y,r,fill:color,stroke:'#fffefa','stroke-width':1},undefined,g);
    return interactive(g,label,handler);
  }
  function line(x1,y1,x2,y2,attrs={}) { return el('line',{x1,y1,x2,y2,class:'link',...attrs}); }
  function truncate(value,n=34) { return value.length > n ? value.slice(0,n-1)+'…' : value; }
  function setup(width=920,height=540) { svg.replaceChildren(); svg.setAttribute('viewBox',`0 0 ${width} ${height}`); svg.style.minWidth = `${width}px`; }
  function legend(values) { $('#legend').innerHTML = values.map(([label,color])=>`<span><i class="swatch" style="--swatch:${color}"></i>${esc(label)}</span>`).join(''); }
  function empty(message='Brak wyników. Zmień ustawienia lub zresetuj widok.') { text(460,250,message,{'text-anchor':'middle',class:'label'}); }
  function panel(html) { $('#details').innerHTML = html; }
  function initialPanel(title,body,number) {
    panel(`<p class="eyebrow">OD CZEGO ZACZĄĆ</p>${number === undefined ? '' : `<p class="big">${esc(number)}</p>`}<h3>${esc(title)}</h3><p>${esc(body)}</p><h4>Sprawdź kontekst</h4><p>Wybierz element wykresu albo wiersz w tabeli poniżej. Opis i odsyłacze pojawią się tutaj.</p>`);
  }
  function clauseButtons(items) { return items.map(c=>`<button type="button" data-clause="${esc(c.id)}">${esc(c.id)} · ${esc(c.country)}<br>${esc(c.title)}</button>`).join(''); }
  function clausePanel(id) {
    const c = clauses.get(id);
    panel(`<p class="eyebrow">${esc(c.id)} / ${esc(c.country)}</p><h3>${esc(c.title)}</h3><p class="meta">${esc(c.provision)} · ${esc(c.document_title)}<br>${esc(c.period)}</p><p>${esc(c.meaning)}</p><h4>Dlaczego to istotne</h4><p>${esc(c.why)}</p><h4>Kontekst i ograniczenie</h4><p>${esc(c.caveat)}</p><div>${c.categories.map(k=>`<span class="tag">${esc(D.categories[k])}</span>`).join('')}</div><h4>Przeczytaj źródło</h4><div class="links"><a href="../ATLAS.html#${c.id.toLowerCase()}">Pełny opis w atlasie ↗</a><a href="${esc(rootLink(c.source_text_path))}">Tekst w archiwum, wiersz ${c.source_line} ↗</a><a href="${esc(c.source_url)}">Wydawca: wskazany przepis ↗</a>${c.archive_assets.map(a=>`<a href="${esc(rootLink(a.path))}">Oryginał ${esc(a.format.toUpperCase())} ↗</a>`).join('')}</div>`);
  }
  function listPanel(title,items,note='Wybrane opisy atlasu. Kategorie nie są oceną całego państwa.') {
    panel(`<p class="eyebrow">PRZEPISY Z ATLASU</p><h3>${esc(title)}</h3><p class="meta">${items.length} opisów. ${esc(note)}</p>${clauseButtons(items) || '<p>Brak opisów w tej komórce.</p>'}`);
  }
  function proposalPanel(id) {
    const p = D.proposals.find(p=>p.id===id);
    panel(`<p class="eyebrow">${esc(p.id)} / POLSKA</p><h3>${esc(p.title)}</h3><p class="meta">${esc(D.labels.verdict[p.verdict])} · ${esc(D.labels.change[p.change])}</p><h4>W Polsce dziś</h4><p>${esc(p.poland)}</p><h4>Autorski szkic</h4><p>${esc(p.draft)}</p><h4>Ryzyko</h4><p>${esc(p.risk)}</p><h4>Zabezpieczenia</h4><p>${esc(p.safeguards)}</p><h4>Inspiracje</h4>${clauseButtons(p.inspirations.map(id=>clauses.get(id)))}<div class="links"><a href="../polska/index.html#${p.id.toLowerCase()}">Pełna propozycja i uzasadnienie ↗</a>${p.polish_articles.map(n=>`<a href="../polska/sources/konstytucja-rp.html#art-${n}">Konstytucja RP: art. ${n} ↗</a>`).join('')}</div>`);
  }
  function setTable(headers,rows,actions=[],kind='clause') {
    tableHeaders=headers;tableRows=rows;tableActions=actions;rowKind=kind;
    $('#table-count').textContent=`${rows.length} wierszy`;
    const table=document.createElement('table');
    const caption=document.createElement('caption');caption.textContent=views[current].name;table.append(caption);
    const head=document.createElement('thead'),tr=document.createElement('tr');
    [...headers,...(actions.length?['Szczegóły']:[])].forEach(h=>{const th=document.createElement('th');th.scope='col';th.textContent=h;tr.append(th);});head.append(tr);table.append(head);
    const body=document.createElement('tbody');
    rows.forEach((row,i)=>{const tr=document.createElement('tr');row.forEach(value=>{const td=document.createElement('td');td.textContent=String(value??'');tr.append(td);});
      if(actions.length){const td=document.createElement('td');const button=document.createElement('button');button.type='button';button.textContent='Zobacz';button.dataset.tableRow=String(i);td.append(button);tr.append(td);}body.append(tr);});
    table.append(body);$('#table').replaceChildren(table);
    $('#result-status').textContent=`${views[current].name}: ${rows.length} wierszy danych.`;
  }
  function selectControl(key,label,options,wide=false) {
    const wrapper=document.createElement('label');wrapper.textContent=label;if(wide)wrapper.className='wide';
    const select=document.createElement('select');select.id=`control-${key}`;select.dataset.key=key;
    options.forEach(([value,name])=>{const option=document.createElement('option');option.value=value;option.textContent=name;select.append(option);});
    select.value=state[key]??'';wrapper.append(select);$('#controls').append(wrapper);
  }
  function inputControl(key,label,type='search') {
    const wrapper=document.createElement('label');wrapper.textContent=label;
    const input=document.createElement('input');input.id=`control-${key}`;input.dataset.key=key;input.type=type;input.value=state[key]??'';
    if(type==='number'){input.min='0';input.max='2100';input.step='1';}wrapper.append(input);$('#controls').append(wrapper);
  }
  const countryControl=()=>selectControl('country','Państwo lub dawny porządek',[['','Wszystkie'],...countries]);
  const statusControl=(corpus=false)=>selectControl('status','Rodzaj wydania',[['','Wszystkie wydania'],['archive',corpus?'Według wydawcy: w mocy':'Wydanie z archiwum'],['history','Historyczne / fragmenty'],['draft','Projekty']]);
  function documentOptions(blank=false) {
    return [...(blank?[['','Bez porównania']]:[]),...docs.slice().sort((a,b)=>a.title.localeCompare(b.title,'en')).map(d=>[d.id,d.title])];
  }
  function defaults(index) {
    const poland=docs.find(d=>d.country_code==='PL'&&d.status==='source_in_force')||docs[0];
    const germany=docs.find(d=>d.country_code==='DE'&&d.status==='source_in_force')||docs[1];
    const ecuador=docs.find(d=>d.country_code==='EC'&&d.status==='source_in_force')||docs[2];
    return {category:'panstwo',country:'',status:'',query:'',sort:'count',from:'',to:'',proposal:'starter',domain:'',document:poland.id,group:'',doc1:poland.id,doc2:germany.id,doc3:ecuador.id,measure:'rate'};
  }
  function controls() {
    $('#controls').replaceChildren();
    if(current===0){selectControl('category','Kategoria',[['','Wszystkie kategorie'],...cats.map(c=>[c,D.categories[c]])],true);countryControl();statusControl();}
    if(current===1){inputControl('query','Szukaj państwa');selectControl('sort','Kolejność',[['count','Najwięcej wybranych opisów'],['alpha','Alfabetycznie']]);statusControl();}
    if(current===2||current===3){countryControl();statusControl();}
    if(current===4){countryControl();inputControl('from','Przyjęcie: od roku','number');inputControl('to','Przyjęcie: do roku','number');statusControl();}
    if(current===5){selectControl('proposal','Propozycje',[['starter','Sześć na początek'],['all','Wszystkie 24'],...D.proposals.map(p=>[p.id,p.id+' · '+p.title])],true);selectControl('domain','Obszar',[['','Wszystkie obszary'],...Object.entries(D.labels.domain)]);}
    if(current===6){selectControl('document','Wybierz dokument',documentOptions(),true);inputControl('query','Szukaj na mapie');statusControl(true);selectControl('group','Grupa słownictwa',[['','Wszystkie grupy'],...Object.entries(D.corpus.groups).map(([k,words])=>[k,`G${k} · ${words.slice(0,2).join(', ')}`])]);}
    if(current===7){selectControl('doc1','Dokument 1',documentOptions());selectControl('doc2','Dokument 2',documentOptions(true));selectControl('doc3','Dokument 3',documentOptions(true));selectControl('measure','Miara',[['rate','Na 10 tys. słów'],['count','Liczba trafień']]);}
  }
  function filteredClauses(useCategory=false) {return D.clauses.filter(c=>(!state.country||c.country_code===state.country)&&statusMatch(c,state.status)&&(!useCategory||!state.category||c.categories.includes(state.category)));}

  function constellation() {
    const items=filteredClauses(true);setup(920,600);
    if(!items.length){empty();setTable(['ID','Państwo','Przepis','Tytuł'],[]);initialPanel('Brak opisów','Zmień kategorię, państwo lub rodzaj wydania.');return;}
    const usedCountries=[...new Set(items.map(c=>c.country_code))].sort((a,b)=>countryNames.get(a).localeCompare(countryNames.get(b),'pl'));
    const usedCats=cats.filter(key=>items.some(c=>c.categories.includes(key)));
    const positions=new Map();
    usedCountries.forEach((key,i)=>positions.set('country:'+key,{x:115,y:60+i*480/Math.max(1,usedCountries.length-1)}));
    usedCats.forEach((key,i)=>positions.set('category:'+key,{x:725,y:65+i*475/Math.max(1,usedCats.length-1)}));
    items.forEach((c,i)=>positions.set(c.id,{x:385+(i%3)*45,y:45+i*510/Math.max(1,items.length-1)}));
    items.forEach(c=>{const p=positions.get(c.id),left=positions.get('country:'+c.country_code);el('path',{d:`M${left.x},${left.y}C250,${left.y} 265,${p.y} ${p.x},${p.y}`,class:'link'});c.categories.forEach(key=>{const right=positions.get('category:'+key);el('path',{d:`M${p.x},${p.y}C570,${p.y} 580,${right.y} ${right.x},${right.y}`,class:'link',style:`stroke:${catColor(key)};stroke-opacity:.24`});});});
    text(115,20,'PAŃSTWO',{'text-anchor':'middle',class:'minor'});text(430,20,'PRZEPIS',{'text-anchor':'middle',class:'minor'});text(725,20,'KATEGORIA',{'text-anchor':'middle',class:'minor'});
    usedCountries.forEach(key=>{const p=positions.get('country:'+key);point(p.x,p.y,5,'#436b88',countryNames.get(key),()=>listPanel(countryNames.get(key),items.filter(c=>c.country_code===key)));text(p.x-12,p.y+3,truncate(countryNames.get(key),20),{'text-anchor':'end',class:'small'});});
    usedCats.forEach(key=>{const p=positions.get('category:'+key);point(p.x,p.y,9,catColor(key),D.categories[key],()=>listPanel(D.categories[key],items.filter(c=>c.categories.includes(key))));text(p.x+17,p.y+4,catLabel(key),{class:'label'});});
    items.forEach(c=>{const p=positions.get(c.id);point(p.x,p.y,items.length>70?3.4:5,'#156a56',`${c.id}: ${c.country}, ${c.title}`,()=>clausePanel(c.id));if(items.length<=45)text(p.x+10,p.y+3,c.id,{class:'small'});});
    legend([['Państwo / dawny porządek','#436b88'],['Wybrany przepis','#156a56'],['Kategoria redakcyjna','#ab603e']]);
    setTable(['ID','Państwo','Przepis','Tytuł','Kategorie'],items.map(c=>[c.id,c.country,c.provision,c.title,c.categories.map(k=>D.categories[k]).join('; ')]),items.map(c=>c.id));
    initialPanel(state.category?D.categories[state.category]:'Cała konstelacja','Węzeł państwa lub kategorii pokaże listę przepisów. Wybór punktu w środku otworzy jeden opis.',items.length);
  }

  function portraits() {
    const items=filteredClauses();
    let rows=countries.filter(([code,name])=>items.some(c=>c.country_code===code)&&norm(name).includes(norm(state.query)));
    if(state.sort==='count')rows.sort((a,b)=>items.filter(c=>c.country_code===b[0]).length-items.filter(c=>c.country_code===a[0]).length||a[1].localeCompare(b[1],'pl'));
    const height=Math.max(460,190+rows.length*25);setup(920,height);
    const max=Math.max(1,...rows.flatMap(([code])=>cats.map(k=>items.filter(c=>c.country_code===code&&c.categories.includes(k)).length)));
    const cell=68,x0=242,y0=145;
    cats.forEach((key,j)=>{const g=el('g',{transform:`translate(${x0+j*cell+20},125) rotate(-35)`});text(0,0,catLabel(key),{class:'small'},g);});
    const narrow=scroller&&scroller.clientWidth<600,lx=narrow?136:212;const stick=stickyColumn(lx+10);rows.forEach(([code,name],i)=>{const y=y0+i*25;const own=items.filter(c=>c.country_code===code);text(lx,y+15,`${narrow?truncate(name,15):name} (${own.length})`,{'text-anchor':'end',class:'label'},stick);cats.forEach((key,j)=>{const matches=own.filter(c=>c.categories.includes(key));const x=x0+j*cell;const rect=el('rect',{x,y,width:60,height:21,rx:2,fill:matches.length?'#156a56':'#e9eee3','fill-opacity':matches.length?.2+.8*matches.length/max:1});interactive(rect,`${name}, ${D.categories[key]}: ${matches.length}`,()=>listPanel(`${name}: ${D.categories[key]}`,matches));text(x+30,y+15,matches.length,{'text-anchor':'middle',class:'small',style:`fill:${matches.length/max>.6?'#fff':'#19343d'};pointer-events:none`});});});
    if(!rows.length)empty();
    legend([['Brak opisów w wyborze','#e9eee3'],['Więcej opisów: ciemniejsza komórka','#156a56']]);
    setTable(['Państwo','Opisy ogółem',...cats.map(k=>D.categories[k])],rows.map(([code,name])=>[name,items.filter(c=>c.country_code===code).length,...cats.map(k=>items.filter(c=>c.country_code===code&&c.categories.includes(k)).length)]),rows.map(([code])=>code),'country');
    initialPanel('Portret redakcyjnego wyboru','Wiersze nie porównują jakości konstytucji. Pokazują, które z wybranych przepisów opisano w poszczególnych kategoriach.',rows.length);
  }

  function categoryWeave() {
    setup(920,530);const items=filteredClauses(),positions=cats.map((k,i)=>({x:70+i*97,y:402}));
    const pairs=[];
    cats.forEach((a,i)=>cats.slice(i+1).forEach(b=>{const matches=items.filter(c=>c.categories.includes(a)&&c.categories.includes(b));if(matches.length)pairs.push({a,b,i,j:cats.indexOf(b),items:matches});}));
    pairs.sort((a,b)=>b.items.length-a.items.length);
    pairs.forEach(p=>{const x1=positions[p.i].x,x2=positions[p.j].x;const path=el('path',{d:`M${x1},390 Q${(x1+x2)/2},${390-(x2-x1)*.85} ${x2},390`,fill:'none',stroke:catColor(p.a),'stroke-width':1+p.items.length*.32,'stroke-opacity':.25});interactive(path,`${D.categories[p.a]} i ${D.categories[p.b]}: ${p.items.length}`,()=>listPanel(`${catLabel(p.a)} + ${catLabel(p.b)}`,p.items));path.addEventListener('mouseenter',()=>path.setAttribute('stroke-opacity','.85'));path.addEventListener('mouseleave',()=>path.setAttribute('stroke-opacity','.25'));});
    cats.forEach((key,i)=>{const p=positions[i],matches=items.filter(c=>c.categories.includes(key));point(p.x,p.y,10+Math.sqrt(matches.length),catColor(key),`${D.categories[key]}: ${matches.length}`,()=>listPanel(D.categories[key],matches));text(p.x,p.y+5,matches.length,{'text-anchor':'middle',style:'fill:#fff;font-size:11px;pointer-events:none'});const words=catLabel(key).split(' ');words.forEach((word,j)=>text(p.x,446+j*14,word,{'text-anchor':'middle',class:'small'}));});
    legend(cats.map(k=>[D.categories[k],catColor(k)]));
    setTable(['Kategoria 1','Kategoria 2','Wspólne opisy'],pairs.map(p=>[D.categories[p.a],D.categories[p.b],p.items.length]),pairs.map(p=>p.a+'|'+p.b),'pair');
    initialPanel('Grubszy łuk, więcej wspólnych opisów','Wybierz połączenie lub kategorię. Liczby przy węzłach pokazują wszystkie opisy tej kategorii w bieżącym wyborze.',pairs.length);
  }

  function mechanisms() {
    setup(920,570);const items=filteredClauses();
    const boxes=[{x:45,y:55,p:true,w:false,title:'Potencjał państwa',subtitle:'bez kategorii koncentracji władzy',color:'#156a56'},
      {x:473,y:55,p:true,w:true,title:'Obie kategorie',subtitle:'potencjał państwa i władza przywódcy',color:'#ab603e'},
      {x:45,y:315,p:false,w:false,title:'Inne mechanizmy',subtitle:'żadna z dwóch kategorii',color:'#637e82'},
      {x:473,y:315,p:false,w:true,title:'Władza przywódcy',subtitle:'bez kategorii potencjału państwa',color:'#856b8a'}];
    boxes.forEach(box=>{const matches=items.filter(c=>c.categories.includes('panstwo')===box.p&&c.categories.includes('wladca')===box.w);el('rect',{x:box.x,y:box.y,width:402,height:225,rx:5,fill:box.color,'fill-opacity':.06,stroke:'#cbd6c7'});text(box.x+18,box.y+27,box.title,{style:`font:21px Georgia,serif;fill:${box.color}`});text(box.x+18,box.y+47,box.subtitle,{class:'small'});text(box.x+375,box.y+30,matches.length,{'text-anchor':'end',style:`font:26px Georgia,serif;fill:${box.color}`});matches.forEach((c,i)=>{const cols=11,x=box.x+25+(i%cols)*34,y=box.y+83+Math.floor(i/cols)*23;point(x,y,6,box.color,`${c.id}: ${c.title}`,()=>clausePanel(c.id));});});
    legend([['Punkt: jeden przepis','#156a56'],['Liczba w polu: wszystkie pasujące opisy','#637e82']]);
    setTable(['ID','Państwo','Tytuł','Potencjał państwa','Władza przywódcy'],items.map(c=>[c.id,c.country,c.title,c.categories.includes('panstwo')?'tak':'nie',c.categories.includes('wladca')?'tak':'nie']),items.map(c=>c.id));
    initialPanel('Dwie niezależne perspektywy','Zdolność do działania i koncentracja władzy nie są tym samym. Jednoczesne przypisanie obu kategorii wynika z konkretnego opisu przepisu.',items.length);
  }

  function timeline() {
    const items=filteredClauses();const grouped=new Map();items.forEach(c=>{if(!grouped.has(c.document_id))grouped.set(c.document_id,[]);grouped.get(c.document_id).push(c);});
    const all=[...grouped.values()].filter(group=>!group[0].year||((!state.from||group[0].year>=Number(state.from))&&(!state.to||group[0].year<=Number(state.to))));
    const known=all.filter(g=>g[0].year).sort((a,b)=>a[0].year-b[0].year||a[0].country.localeCompare(b[0].country,'pl'));
    const unknown=all.filter(g=>!g[0].year);const height=Math.max(430,120+known.length*24+unknown.length*30+70);setup(920,height);
    const min=Math.min(...known.map(g=>g[0].year),2000)-5,max=Math.max(...known.map(g=>g[0].revised||g[0].year),2025)+3;
    const scale=year=>310+(year-min)/(max-min)*560;const narrow=scroller&&scroller.clientWidth<600,lx=narrow?150:287;const stick=stickyColumn(lx+9,90+known.length*24);
    const step=max-min>150?50:20;for(let year=Math.ceil(min/step)*step;year<=max;year+=step){line(scale(year),50,scale(year),80+known.length*24,{class:'tick'});text(scale(year),35,year,{'text-anchor':'middle',class:'minor'});}
    known.forEach((group,i)=>{const c=group[0],y=68+i*24,color=c.period==='projekt'?'#ab603e':isHistorical(c)?'#856b8a':'#156a56';text(lx,y+4,narrow?truncate(c.country,13)+' · '+c.year:truncate(c.country+' · '+c.year,36),{'text-anchor':'end',class:'label'},stick);if(c.revised&&c.revised!==c.year){line(scale(c.year),y,scale(c.revised),y,{style:`stroke:${color};stroke-opacity:.55;stroke-width:2`});point(scale(c.revised),y,3.5,color,`${c.document_title}: rewizja ${c.revised}`,()=>listPanel(c.document_title,group),'square');}point(scale(c.year),y,5.5,color,`${c.document_title}: ${group.length} opisów`,()=>listPanel(c.document_title,group),c.period==='projekt'?'diamond':isHistorical(c)?'square':'circle');text(887,y+4,group.length,{class:'small'});});
    if(unknown.length){const y0=115+known.length*24;text(40,y0,'DATA PRZYJĘCIA NIEZNANA W METADANYCH',{class:'minor'});unknown.forEach((group,i)=>{const c=group[0];point(55,y0+28+i*28,5,'#ab603e',c.document_title,()=>listPanel(c.document_title,group),'diamond');text(74,y0+32+i*28,`${c.document_title} · ${group.length} opisów`,{class:'label'});});}
    if(!all.length)empty();legend([['● Wydanie z archiwum','#156a56'],['■ Historyczne / fragment','#856b8a'],['◆ Projekt','#ab603e'],['Mały kwadrat na linii: rewizja','#637e82']]);
    setTable(['Dokument','Państwo','Przyjęcie','Rewizja','Rodzaj','Opisy'],[...known,...unknown].map(g=>{const c=g[0];return[c.document_title,c.country,c.year||'nieznane',c.revised||'nieznana',c.period,g.length];}),[...known,...unknown].map(g=>g[0].document_id),'edition');
    initialPanel('Czytaj wydanie, nie samą datę','Wiersz reprezentuje jeden dokument z atlasu. Liczba po prawej pokazuje przypisane mu opisy. Nieznane daty pozostają widoczne niezależnie od zakresu lat.',all.length);
  }

  function polandFlow() {
    const proposals=D.proposals.filter(p=>(state.proposal==='all'||(state.proposal==='starter'?p.starter:p.id===state.proposal))&&(!state.domain||p.domain===state.domain));
    const sources=[...new Set(proposals.flatMap(p=>p.inspirations))].map(id=>clauses.get(id));
    const codes=[...new Set(sources.map(c=>c.country_code))].sort((a,b)=>countryNames.get(a).localeCompare(countryNames.get(b),'pl'));
    const articles=[...new Set(proposals.flatMap(p=>p.polish_articles))].sort((a,b)=>a-b);
    const height=Math.max(570,90+Math.max(sources.length,articles.length,proposals.length)*24);setup(1100,height);
    const positions=new Map();const arrange=(keys,x,prefix)=>keys.forEach((key,i)=>positions.set(prefix+key,{x,y:85+i*(height-135)/Math.max(1,keys.length-1)}));
    arrange(codes,140,'c');arrange(sources.map(c=>c.id),390,'a');arrange(proposals.map(p=>p.id),710,'p');arrange(articles,1015,'r');
    const edge=(from,to,color)=>{const a=positions.get(from),b=positions.get(to);el('path',{d:`M${a.x},${a.y}C${(a.x+b.x)/2},${a.y} ${(a.x+b.x)/2},${b.y} ${b.x},${b.y}`,class:'link',style:`stroke:${color};stroke-opacity:.32;stroke-width:1.5`});};
    sources.forEach(c=>edge('c'+c.country_code,'a'+c.id,'#638354'));proposals.forEach(p=>{p.inspirations.forEach(id=>edge('a'+id,'p'+p.id,'#156a56'));p.polish_articles.forEach(n=>edge('p'+p.id,'r'+n,'#ab603e'));});
    [[140,'PAŃSTWO'],[390,'ZAGRANICZNY PRZEPIS'],[710,'PROPOZYCJA'],[1015,'KONSTYTUCJA RP']].forEach(([x,label])=>text(x,29,label,{'text-anchor':'middle',class:'minor'}));
    codes.forEach(code=>{const p=positions.get('c'+code);point(p.x,p.y,6,'#436b88',countryNames.get(code),()=>listPanel(countryNames.get(code),sources.filter(c=>c.country_code===code)));text(p.x-13,p.y+4,truncate(countryNames.get(code),19),{'text-anchor':'end',class:'small'});});
    sources.forEach(c=>{const p=positions.get('a'+c.id);point(p.x,p.y,5,'#156a56',`${c.id}: ${c.title}`,()=>clausePanel(c.id));text(p.x+10,p.y+3,`${c.id} · ${truncate(c.provision,20)}`,{class:'small'});});
    proposals.forEach(proposal=>{const p=positions.get('p'+proposal.id);point(p.x,p.y,8,'#156a56',`${proposal.id}: ${proposal.title}`,()=>proposalPanel(proposal.id));text(p.x+14,p.y+4,proposal.id,{class:'label'});});
    articles.forEach(n=>{const p=positions.get('r'+n);point(p.x,p.y,4,'#ab603e',`Konstytucja RP, art. ${n}`,()=>panel(`<p class="eyebrow">POLSKI PUNKT PORÓWNANIA</p><h3>Art. ${n} Konstytucji RP</h3><p>Artykuł wskazano w porównaniu do następujących propozycji. To odniesienie redakcyjne, nie ocena równoważności.</p>${proposals.filter(p=>p.polish_articles.includes(n)).map(p=>`<button type="button" data-proposal="${p.id}">${esc(p.id+' · '+p.title)}</button>`).join('')}<a href="../polska/sources/konstytucja-rp.html#art-${n}">Przeczytaj art. ${n} ↗</a>`));text(p.x+10,p.y+3,`art. ${n}`,{class:'small'});});
    if(!proposals.length)empty();legend([['Państwo źródła','#436b88'],['Zapisana inspiracja / propozycja','#156a56'],['Polski artykuł porównania','#ab603e']]);
    const rows=[],actions=[];proposals.forEach(p=>p.inspirations.forEach(id=>{const c=clauses.get(id);rows.push([c.country,id,c.provision,p.id,p.title,p.polish_articles.map(n=>'art. '+n).join('; ')]);actions.push(p.id);}));
    setTable(['Państwo','Inspiracja','Przepis','Propozycja','Tytuł propozycji','Polskie artykuły'],rows,actions,'proposal');
    initialPanel('Inspiracja potrzebuje adaptacji','Wybierz propozycję, aby zobaczyć obecny polski punkt odniesienia, autorski szkic i zabezpieczenia. Zagraniczny przepis prowadzi do opisu atlasu.',proposals.length);
  }

  function documentPanel(id) {
    const d=docMap.get(id);
    panel(`<p class="eyebrow">CONSTITUTE EN / GRUPA ${d.group}</p><h3>${esc(d.title)}</h3><p class="meta">${esc(statusLabel(d.status))}<br>${fmt(d.words)} słów · ${d.aliases.length} rekordów źródłowych</p><p>Pięciu najbliższych sąsiadów według podobieństwa słownictwa w pełnej przestrzeni TF-IDF.</p><div>${d.terms.map(term=>`<span class="tag">${esc(term)}</span>`).join('')}</div><h4>Najbliższe teksty</h4>${d.neighbors.map(n=>{const neighbor=docMap.get(n.id);return `<details><summary>${esc(neighbor.title)}<br><b>${fmt(n.similarity*100)}% podobieństwa cosinusowego</b></summary><p>Wspólne terminy: ${esc(n.terms.join(', '))}.</p>${n.snippets.map(s=>`<p class="meta">${esc(docMap.get(s.id).title)}</p><blockquote>${esc(truncate(s.text,440))}</blockquote><p><a href="${esc(s.url)}">Fragment, wiersz ${s.line} ↗</a></p>`).join('')}<button type="button" data-document="${esc(n.id)}">Wybierz ten dokument</button></details>`;}).join('')}<h4>Źródła</h4><div class="links"><a href="${esc(d.text_url)}">Tekst użyty do analizy ↗</a><a href="${esc(d.source_url)}">Wydawca ↗</a></div><p class="meta">Procent jest podobieństwem wektorów, nie udziałem identycznych zdań. Grupa G${d.group}: ${esc(D.corpus.groups[d.group].join(', '))}.</p>`);
  }
  function neighborhood() {
    setup(920,650);const selected=docMap.get(state.document);
    const filtered=docs.filter(d=>statusMatch(d,state.status)&&(!state.group||d.group===Number(state.group))&&norm(d.title+' '+d.country).includes(norm(state.query)));
    const xs=docs.map(d=>d.x),ys=docs.map(d=>d.y),minX=Math.min(...xs),maxX=Math.max(...xs),minY=Math.min(...ys),maxY=Math.max(...ys);
    const project=d=>({x:75+(d.x-minX)/(maxX-minX)*770,y:65+(maxY-d.y)/(maxY-minY)*505});
    const visible=new Set(filtered.map(d=>d.id)),near=new Set(selected.neighbors.map(n=>n.id));
    for(let i=0;i<5;i++){const x=75+i*770/4;line(x,50,x,585,{class:'tick'});}for(let i=0;i<4;i++){const y=65+i*505/3;line(55,y,865,y,{class:'tick'});}
    text(460,625,'Projekcja słownictwa na dwa wymiary; osie nie oznaczają cech ustroju.',{'text-anchor':'middle',class:'minor'});
    if(visible.has(selected.id)){const p=project(selected);selected.neighbors.filter(n=>visible.has(n.id)).forEach(n=>{const q=project(docMap.get(n.id));line(p.x,p.y,q.x,q.y,{style:'stroke:#ab603e;stroke-opacity:.6;stroke-dasharray:4 4'});});}
    filtered.slice().sort((a,b)=>(a.id===selected.id)-(b.id===selected.id)).forEach(d=>{const p=project(d),active=d.id===selected.id,neighbor=near.has(d.id);const g=point(p.x,p.y,active?10:neighbor?6:4.5,colors[d.group-1],`${d.title}; G${d.group}; ${statusLabel(d.status)}`,()=>{state.document=d.id;$('#control-document').value=d.id;render();},d.status==='draft'?'diamond':d.status==='historical_or_replaced'?'square':'circle');if(active){el('circle',{cx:p.x,cy:p.y,r:15,fill:'none',stroke:'#ab603e','stroke-width':2},undefined,g);g.setAttribute('aria-pressed','true');}});
    const labels=[];
    [selected,...selected.neighbors.map(n=>docMap.get(n.id))].filter(d=>visible.has(d.id)).forEach(d=>{
      const p=project(d),value=truncate(d.title,32),width=value.length*4.7+10;
      const candidates=[];
      for(const dy of [-18,16,-36,34,-54,52,-72,70,-90,88])for(const dx of [17,-width-17])candidates.push({x:p.x+dx,y:p.y+dy,w:width,h:17});
      const fits=box=>box.x>=55&&box.x+box.w<=880&&box.y>=43&&box.y+box.h<=585&&!labels.some(other=>box.x<other.x+other.w+5&&box.x+box.w+5>other.x&&box.y<other.y+other.h+4&&box.y+box.h+4>other.y);
      const box=candidates.find(fits)||candidates[0];labels.push(box);
      line(p.x,p.y,Math.max(box.x,Math.min(box.x+box.w,p.x)),box.y+8,{stroke:'#8ca18a','stroke-opacity':.6});
      el('rect',{x:box.x,y:box.y,width:box.w,height:box.h,rx:2,fill:'#fffefa','fill-opacity':.96,'pointer-events':'none'});
      text(box.x+5,box.y+12,value,{class:'small','pointer-events':'none'});
    });
    if(!filtered.length)empty();
    legend([...Object.entries(D.corpus.groups).map(([g,terms])=>[`G${g}: ${terms.slice(0,3).join(', ')}`,colors[Number(g)-1]]),['● W mocy według wydawcy / ■ historyczne / ◆ projekt','#19343d']]);
    const i=docs.indexOf(selected);
    setTable(['Dokument','Status','Grupa','Słowa','Podobieństwo do wybranego'],filtered.map(d=>[d.title,statusLabel(d.status),'G'+d.group,d.words,fmt(D.corpus.similarities[i][docs.indexOf(d)]*100)+'%']),filtered.map(d=>d.id),'document');
    documentPanel(selected.id);
    if(!visible.has(selected.id))$('#details').insertAdjacentHTML('afterbegin','<p class="meta"><b>Wybrany dokument jest poza filtrami mapy.</b> Jego sąsiedzi nadal dotyczą pełnego korpusu.</p>');
  }

  function topicPanel(documentId,topic) {
    const d=docMap.get(documentId),profile=d.topics[topic];
    panel(`<p class="eyebrow">TRAFIENIA SŁOWNIKOWE</p><h3>${esc(D.topics[topic])}</h3><p>${esc(d.title)}</p><p class="big">${profile.count}</p><p>${fmt(profile.rate)} trafień na 10 tys. słów<br>${fmt(d.words)} słów w oczyszczonym tekście</p><p class="meta">To dopasowania wyrażeń, nie ocena ochrony lub skuteczności prawa. Fragment może zawierać kilka dopasowań.</p>${profile.hits.length?profile.hits.map(hit=>`<blockquote>${esc(truncate(hit.text,480))}</blockquote><p><a href="${esc(d.text_url)}#l${hit.line}">Wiersz ${hit.line} · ${hit.count} trafień ↗</a></p>`).join(''):'<p>Brak trafień wybranego słownika. Nie oznacza to braku regulacji tego tematu.</p>'}`);
  }
  function topics() {
    const ids=[...new Set([state.doc1,state.doc2,state.doc3].filter(Boolean))],selected=ids.map(id=>docMap.get(id));
    setup(1040,690);const keys=Object.keys(D.topics),measure=state.measure;
    const maximum=Math.max(1,...selected.flatMap(d=>keys.map(k=>d.topics[k][measure])));
    const scale=value=>value/maximum*520;
    for(let i=0;i<=4;i++){const x=375+i*130;line(x,40,x,610,{class:'tick'});text(x,25,fmt(maximum*i/4),{'text-anchor':'middle',class:'minor'});}
    keys.forEach((key,index)=>{const y=65+index*80;const label=D.topics[key];const cut=label.lastIndexOf(' ',29);const parts=label.length>33?[label.slice(0,cut),label.slice(cut+1)]:[label];parts.forEach((part,j)=>text(350,y+12+j*15,part,{'text-anchor':'end',class:'label'}));selected.forEach((d,j)=>{const value=d.topics[key][measure],barY=y+j*18;const bar=el('rect',{x:375,y:barY,width:Math.max(3,scale(value)),height:13,rx:2,fill:colors[j]});interactive(bar,`${d.title}, ${D.topics[key]}: ${fmt(value)} ${measure==='rate'?'na 10 tysięcy słów':'trafień'}`,()=>topicPanel(d.id,key));text(384+scale(value),barY+11,fmt(value),{class:'small'});});});
    text(635,652,measure==='rate'?'Liczba trafień na 10 tys. słów':'Liczba dopasowań słownika',{'text-anchor':'middle',class:'minor'});
    legend(selected.map((d,i)=>[d.title,colors[i]]));
    const rows=[],actions=[];keys.forEach(k=>selected.forEach(d=>{const p=d.topics[k];rows.push([d.title,D.topics[k],d.words,p.count,p.rate]);actions.push(d.id+'|'+k);}));
    setTable(['Dokument','Temat','Słowa','Trafienia','Na 10 tys. słów'],rows,actions,'topic');
    initialPanel('Porównaj miarę z fragmentem','Wyższy słupek oznacza częstsze dopasowanie słownika. Kliknij dowolny słupek, również o wartości zero, aby sprawdzić jego źródło.',selected.length);
  }

  const renderers=[constellation,portraits,categoryWeave,mechanisms,timeline,polandFlow,neighborhood,topics];
  function render() {
    $('#legend').replaceChildren();renderers[current]();syncSticky();$('#chart-caption').textContent=views[current].note;
  }
  function activate(index,updateHash=true) {
    current=index;state=defaults(index);const v=views[index];
    $('#view-title').textContent=v.title;$('#view-description').textContent=v.description;$('#view-kicker').textContent=String(index+1).padStart(2,'0')+' / '+v.name.toLocaleUpperCase('pl');$('#view-badge').textContent=v.badge;$('#view-badge').className='badge'+(v.auto?' auto':'');
    $('#view-nav').querySelectorAll('button').forEach((button,i)=>button.setAttribute('aria-current',String(i===index)));
    if(updateHash){try{history.replaceState(null,'','#'+v.id);}catch{/* File browsing may restrict history updates. */}}
    controls();render();
  }

  function hero() {
    const host=$('#hero-chart');const cx=228,cy=180;
    el('circle',{cx,cy,r:115,fill:'none',stroke:'#d5ddd0','stroke-dasharray':'2 6'},undefined,host);
    el('circle',{cx,cy,r:155,fill:'none',stroke:'#e0e5d9'},undefined,host);
    const pos=cats.map((k,i)=>{const a=-Math.PI/2+i*2*Math.PI/cats.length;return{x:cx+Math.cos(a)*140,y:cy+Math.sin(a)*140};});
    cats.forEach((a,i)=>cats.slice(i+1).forEach(b=>{const n=D.clauses.filter(c=>c.categories.includes(a)&&c.categories.includes(b)).length;if(n>10){const p=pos[i],q=pos[cats.indexOf(b)];el('path',{d:`M${p.x},${p.y} Q${cx},${cy} ${q.x},${q.y}`,fill:'none',stroke:catColor(a),'stroke-opacity':.25,'stroke-width':1+n*.05},undefined,host);}}));
    cats.forEach((key,i)=>{const p=pos[i],count=D.clauses.filter(c=>c.categories.includes(key)).length;const g=el('g',{},undefined,host);el('circle',{cx:p.x,cy:p.y,r:9+Math.sqrt(count)*1.1,fill:catColor(key),stroke:'#f5f3eb','stroke-width':3},undefined,g);text(p.x,p.y+4,count,{'text-anchor':'middle',style:'fill:#fff;font-size:11px'},g);const anchor=p.x<cx-30?'end':p.x>cx+30?'start':'middle';const offset=anchor==='end'?-23:anchor==='start'?23:0;text(p.x+offset,p.y+(i===0?-30:4),catLabel(key),{'text-anchor':anchor,class:'small'},g);});
    el('circle',{cx,cy,r:51,fill:'#f5f3eb'},undefined,host);text(cx,cy+3,'130',{'text-anchor':'middle',style:'font:42px Georgia,serif;fill:#19343d'},host);text(cx,cy+23,'ZAPISÓW',{'text-anchor':'middle',style:'font-size:8px;letter-spacing:.18em;fill:#5c706f'},host);
  }
  function context() {
    const s=D.summary,sc=D.screening;
    const rows=[['Rekordy katalogu',s.manifest_records],['Rekordy z plikami',s.downloaded_records],['Rekordy z tekstem',sc.text_records],['Wyszukiwanie w 7 językach',sc.keyword_screened_records],['Dokumenty z opisami atlasu',new Set(D.clauses.map(c=>c.document_id)).size]];
    $('#coverage').innerHTML=rows.map(([name,count])=>`<div class="coverage-row"><span>${esc(name)}</span><div class="bar-track"><div class="bar-fill" style="width:${count/s.manifest_records*100}%"></div></div><b>${fmt(count)}</b></div>`).join('');
    const changes=Object.keys(D.labels.change),counts=changes.map(k=>D.proposals.filter(p=>p.change===k).length);
    $('#proposal-structure').innerHTML=`<div class="structure-row" role="img" aria-label="${esc(changes.map((k,i)=>D.labels.change[k]+': '+counts[i]).join('; '))}">${changes.map((k,i)=>`<span style="flex:${counts[i]};--swatch:${colors[i]}">${counts[i]}</span>`).join('')}</div><div class="structure-legend">${changes.map((k,i)=>`<span><i class="swatch" style="--swatch:${colors[i]}"></i>${esc(D.labels.change[k])}</span>`).join('')}</div><div class="domains">${Object.entries(D.labels.domain).map(([key,label])=>`<span>${esc(label)}<b>${D.proposals.filter(p=>p.domain===key).length}</b></span>`).join('')}</div>`;
    $('#projection-note').textContent=`Dwa wymiary zachowują ${fmt(D.corpus.projection_explained*100)}% dodatniej wariancji przestrzeni słownictwa. Obliczenia obejmują ${docs.length} unikalnych oczyszczonych tekstów i ${fmt(D.corpus.features)} cech. Pominięto ${D.corpus.excluded.length} rekordów.`;
    $('#stat-clauses').textContent=D.clauses.length;$('#stat-countries').textContent=countries.length;$('#stat-proposals').textContent=D.proposals.length;$('#stat-texts').textContent=D.corpus.records;
  }
  function download(content,mime,name) {
    const blob=new Blob([content],{type:mime});const url=URL.createObjectURL(blob),a=document.createElement('a');a.href=url;a.download=name;document.body.append(a);a.click();a.remove();setTimeout(()=>URL.revokeObjectURL(url),1000);
  }
  $('#export-csv').addEventListener('click',()=>{const quote=value=>'"'+String(value??'').replace(/"/g,'""')+'"';download('\ufeff'+[tableHeaders,...tableRows].map(row=>row.map(quote).join(',')).join('\r\n'),'text/csv;charset=utf-8',views[current].id+'.csv');});
  $('#export-svg').addEventListener('click',()=>{
    const clone=svg.cloneNode(true),width=svg.viewBox.baseVal.width,height=svg.viewBox.baseVal.height;clone.querySelectorAll('.sticky-col').forEach(g=>{g.removeAttribute('transform');g.querySelector('rect')?.remove();});
    clone.setAttributeNS('http://www.w3.org/2000/xmlns/','xmlns',NS);clone.setAttribute('width',width);clone.setAttribute('height',height+210);clone.setAttribute('viewBox',`0 0 ${width} ${height+210}`);clone.removeAttribute('style');clone.setAttribute('role','img');clone.removeAttribute('aria-labelledby');
    const contents=document.createElementNS(NS,'g');contents.setAttribute('transform','translate(0 55)');while(clone.firstChild)contents.append(clone.firstChild);clone.append(contents);
    const title=document.createElementNS(NS,'title');title.textContent=views[current].title;clone.prepend(title);
    const style=document.createElementNS(NS,'style');style.textContent='text{font-family:Arial,sans-serif;fill:#19343d}.minor{fill:#5c706f;font-size:10px}.label{font-size:11px}.small{font-size:9px}.link{fill:none;stroke:#bfd0be;stroke-opacity:.65}.tick{stroke:#d9ded4;stroke-width:1}.frame{fill:#f5f6ee;stroke:#d5ddd1}';clone.prepend(style);
    const background=document.createElementNS(NS,'rect');background.setAttribute('width','100%');background.setAttribute('height','100%');background.setAttribute('fill','#fffefa');clone.insertBefore(background,contents);
    text(25,30,views[current].title,{style:'font:24px Georgia,serif;fill:#19343d'},clone);
    let lx=25,ly=height+83;
    $('#legend').querySelectorAll('span').forEach(item=>{const label=item.textContent,color=item.querySelector('i').style.getPropertyValue('--swatch'),space=label.length*5.3+28;if(lx+space>width-20){lx=25;ly+=18;}el('circle',{cx:lx+4,cy:ly-3,r:4,fill:color},undefined,clone);text(lx+14,ly,label,{class:'small'},clone);lx+=space;});
    const words=views[current].note.split(' '),lines=[];let sentence='';
    words.forEach(word=>{if((sentence+' '+word).length>Math.floor(width/5.5)){lines.push(sentence);sentence=word;}else sentence+=(sentence?' ':'')+word;});if(sentence)lines.push(sentence);
    lines.forEach((value,i)=>text(25,ly+28+i*15,value,{class:'small'},clone));
    clone.querySelectorAll('[tabindex]').forEach(n=>{n.removeAttribute('tabindex');n.removeAttribute('role');});
    download(new XMLSerializer().serializeToString(clone),'image/svg+xml;charset=utf-8',views[current].id+'.svg');
  });
  $('#reset').addEventListener('click',()=>activate(current));
  $('#controls').addEventListener('submit',event=>event.preventDefault());
  $('#controls').addEventListener('input',event=>{if(event.target.dataset.key){state[event.target.dataset.key]=event.target.value;render();}});
  $('#details').addEventListener('click',event=>{const button=event.target.closest('button');if(!button)return;if(button.dataset.clause)clausePanel(button.dataset.clause);if(button.dataset.proposal)proposalPanel(button.dataset.proposal);if(button.dataset.document){state.document=button.dataset.document;$('#control-document').value=state.document;render();}});
  $('#table').addEventListener('click',event=>{const button=event.target.closest('[data-table-row]');if(!button)return;const id=tableActions[Number(button.dataset.tableRow)];
    if(rowKind==='clause')clausePanel(id);
    if(rowKind==='country')listPanel(countryNames.get(id),filteredClauses().filter(c=>c.country_code===id));
    if(rowKind==='pair'){const[a,b]=id.split('|');listPanel(`${catLabel(a)} + ${catLabel(b)}`,filteredClauses().filter(c=>c.categories.includes(a)&&c.categories.includes(b)));}
    if(rowKind==='edition')listPanel(clauses.get(D.clauses.find(c=>c.document_id===id).id).document_title,filteredClauses().filter(c=>c.document_id===id));
    if(rowKind==='proposal')proposalPanel(id);
    if(rowKind==='document'){state.document=id;$('#control-document').value=id;render();}
    if(rowKind==='topic'){const[documentId,topic]=id.split('|');topicPanel(documentId,topic);}
  });
  views.forEach((view,index)=>{const button=document.createElement('button');button.type='button';button.innerHTML=`<span>${String(index+1).padStart(2,'0')}</span>${esc(view.name)}`;button.dataset.view=view.id;button.addEventListener('click',()=>activate(index));$('#view-nav').append(button);});
  window.addEventListener('hashchange',()=>{const index=views.findIndex(v=>location.hash==='#'+v.id);if(index>=0&&index!==current)activate(index,false);});
  hero();context();const initial=views.findIndex(v=>location.hash==='#'+v.id);activate(initial>=0?initial:0,false);
})();
