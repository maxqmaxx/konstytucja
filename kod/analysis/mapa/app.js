(() => {
  'use strict';
  const $ = s => document.querySelector(s);
  const D = JSON.parse($('#map-data').textContent);
  const esc = v => String(v ?? '').replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
  const COLORS = {has:'var(--c-0f6e5c,#0f6e5c)', lacks:'var(--c-e2d8c4,#e2d8c4)', none:'var(--c-f1efe9,#f1efe9)'};
  const BINS = [[0,1949,'przed 1950','var(--c-e3eee8,#e3eee8)'],[1950,1974,'1950–1974','var(--c-b9d6c9,#b9d6c9)'],[1975,1989,'1975–1989','var(--c-86bba6,#86bba6)'],
                [1990,1999,'1990–1999','var(--c-539c84,#539c84)'],[2000,2009,'2000–2009','var(--c-2a7a65,#2a7a65)'],[2010,9999,'od 2010','var(--c-0e5244,#0e5244)']];
  const shapes = [...document.querySelectorAll('#map [data-code]')];
  const codes = Object.keys(D.countries).sort((a,b)=>D.countries[a].name.localeCompare(D.countries[b].name,'pl'));
  const state = {topic: D.featured[0], mode: 'topic', country: ''};
  const read = () => { try { return new URLSearchParams(location.hash.slice(1)); } catch { return new URLSearchParams(); } };

  $('#country').insertAdjacentHTML('beforeend', codes.map(c=>`<option value="${c}">${esc(D.countries[c].name)}</option>`).join(''));
  const p = read();
  if (p.get('t') && D.topics.some(t=>t[0]===p.get('t'))) state.topic = D.topics.findIndex(t=>t[0]===p.get('t'));
  if (p.get('m') === 'year') state.mode = 'year';
  if (p.get('c') && D.countries[p.get('c')]) state.country = p.get('c');

  const year = c => parseInt(String(D.countries[c].year || '').slice(0,4), 10) || null;
  const has = (c, t=state.topic) => Object.prototype.hasOwnProperty.call(D.countries[c].topics, t);

  function colour(code) {
    if (!D.countries[code]) return COLORS.none;
    if (state.mode === 'year') { const y = year(code); const bin = y && BINS.find(b=>y>=b[0]&&y<=b[1]); return bin ? bin[3] : COLORS.none; }
    return has(code) ? COLORS.has : COLORS.lacks;
  }

  function legend() {
    const items = state.mode === 'year'
      ? BINS.map(b=>[b[2], b[3], codes.filter(c=>{const y=year(c);return y&&y>=b[0]&&y<=b[1];}).length])
      : [['ma oznaczony temat', COLORS.has, codes.filter(c=>has(c)).length], ['brak tagu CCP', COLORS.lacks, codes.filter(c=>!has(c)).length]];
    items.push(['poza próbą', COLORS.none, null]);
    $('#legend').innerHTML = items.map(([l,c,n])=>`<span><i style="background:${c}"></i>${esc(l)}${n===null?'':` <b>${n}</b>`}</span>`).join('');
  }

  function summary() {
    const t = D.topics[state.topic], n = codes.filter(c=>has(c)).length;
    const eu = codes.filter(c=>D.countries[c].eu&&has(c)).length;
    const pl = D.countries.PL && has('PL') ? 'Polska: tak.' : 'Polska: brak tagu CCP.';
    $('#summary').innerHTML = state.mode === 'year'
      ? `Rok uchwalenia ${D.sample} obowiązujących konstytucji. Kolor nie zależy od wybranego rozwiązania.`
      : `<b>${esc(t[1])}</b>: ${n} z ${D.sample} konstytucji (${Math.round(100*n/D.sample)}%), w UE ${eu} z 27. ${pl}`;
  }

  function lists() {
    if (state.mode === 'year') { $('#lists').innerHTML = BINS.map(b=>`<div><h3>${b[2]}</h3><p>${codes.filter(c=>{const y=year(c);return y&&y>=b[0]&&y<=b[1];}).map(c=>btn(c)).join(', ')||'—'}</p></div>`).join(''); return; }
    const yes = codes.filter(c=>has(c)), no = codes.filter(c=>!has(c));
    $('#lists').innerHTML = `<div><h3>Ma oznaczony temat (${yes.length})</h3><p>${yes.map(btn).join(', ')||'—'}</p></div><div><h3>Brak tagu CCP (${no.length})</h3><p>${no.map(btn).join(', ')||'—'}</p></div>`;
  }
  const btn = c => `<button type="button" class="link" data-pick="${c}">${esc(D.countries[c].name)}</button>`;

  function panel() {
    const c = state.country;
    if (!c) {
      const t = D.topics[state.topic];
      $('#panel').innerHTML = `<p class="eyebrow">Wybrane rozwiązanie</p><h2>${esc(t[1])}</h2><p class="en">CCP: ${esc(t[2])}</p><p class="big">${Math.round(100*t[3]/D.sample)}%</p><p>${t[3]} z ${D.sample} obowiązujących konstytucji, ${t[4]} z 27 w UE.</p><p><a href="../tematy/${esc(t[0])}.html">Zobacz, jak zapisały to poszczególne konstytucje →</a></p><p class="hint">Kliknij państwo na mapie albo wybierz je z listy, aby zobaczyć przepis i źródło.</p>`;
      return;
    }
    const d = D.countries[c], hit = d.topics[state.topic], t = D.topics[state.topic];
    const n = Object.keys(d.topics).length;
    const atlas = d.atlas.length ? `<h3>W atlasie zapisów</h3><ul>${d.atlas.map(([id,title])=>`<li><a href="../ATLAS.html#${esc(id)}">${esc(title)}</a></li>`).join('')}</ul>` : '';
    const where = hit
      ? `<p class="state yes">Tak: <a href="${esc(d.url)}#s${esc(hit[1])}">${esc(hit[0])}</a> <span>(Constitute)</span> · <a href="../../${esc(d.local)}#s${esc(hit[1])}">kopia w archiwum</a></p>`
      : `<p class="state no">Brak tagu CCP. Nie musi to oznaczać braku przepisu.</p>`;
    $('#panel').innerHTML = `<p class="eyebrow">${d.eu?'Państwo UE · ':''}${esc(d.title)}</p><h2>${esc(d.name)}</h2><p class="meta">Uchwalona ${esc(d.year||'—')}${d.revised&&d.revised!==d.year?`, ostatnia zmiana w wydaniu ${esc(d.revised)}`:''}. ${n} z 331 tematów CCP.${d.stale?' Wydawca sygnalizuje późniejsze zmiany.':''}</p><h3><a href="../tematy/${esc(t[0])}.html">${esc(t[1])}</a></h3>${where}${atlas}<p><a href="../panstwa/${c.toLowerCase()}.html">Wszystkie wersje i języki</a> · <a href="${esc(d.url)}">Pełny tekst w Constitute</a></p><button type="button" id="clear">Zamknij państwo</button>`;
    $('#clear').addEventListener('click', ()=>select(''));
  }

  function paint() {
    shapes.forEach(s=>{ const c=s.dataset.code; s.style.fill=colour(c); s.classList.toggle('selected', !!c && c===state.country); });
    legend(); summary(); lists(); panel();
    $('#topic').value = String(state.topic); $('#mode').value = state.mode; $('#country').value = state.country;
    $('#topic').disabled = state.mode === 'year';
    const params = new URLSearchParams({t:D.topics[state.topic][0]}); if (state.mode==='year') params.set('m','year'); if (state.country) params.set('c',state.country);
    try { history.replaceState(null,'','#'+params.toString()); } catch {}
  }
  function select(code) { state.country = D.countries[code] ? code : ''; paint(); }

  $('#topic').addEventListener('change', e=>{state.topic=Number(e.target.value);paint();});
  $('#mode').addEventListener('change', e=>{state.mode=e.target.value;paint();});
  $('#country').addEventListener('change', e=>select(e.target.value));
  $('#map').addEventListener('click', e=>{ const s=e.target.closest('[data-code]'); if(s&&D.countries[s.dataset.code]) select(s.dataset.code); });
  $('#lists').addEventListener('click', e=>{ const b=e.target.closest('[data-pick]'); if(b){ select(b.dataset.pick); $('#mapa').scrollIntoView({block:'start'}); } });
  paint();
})();
