/* Filters and local comparison of editorial proposals. */
(() => {
  'use strict';
  const { items, labels } = JSON.parse(document.querySelector('#proposal-data').textContent);
  const cards = new Map([...document.querySelectorAll('.proposal')].map(card => [card.dataset.id, card]));
  const ids = new Set(items.map(item => item.id));
  const storageKey = 'konstytucja-polska-comparison-v1';
  let stored = [];
  try { stored = JSON.parse(localStorage.getItem(storageKey) || '[]'); } catch { /* Storage is optional. */ }
  const selected = new Set((Array.isArray(stored) ? stored : []).filter(id => ids.has(id)).slice(0, 3));
  const normalize = text => String(text).toLocaleLowerCase('pl').replace(/ł/g, 'l').normalize('NFD').replace(/[\u0300-\u036f]/g, '');
  const fields = ['domain', 'verdict', 'change', 'level'];
  const searchText = new Map(items.map(item => [item.id, normalize(JSON.stringify(item))]));
  const count = document.querySelector('#count');
  const compareStatus = document.querySelector('#compare-status');

  function filter() {
    const query = normalize(document.querySelector('#query').value).trim();
    const values = Object.fromEntries(fields.map(field => [field, document.getElementById(field).value]));
    const starter = document.querySelector('#starter').checked;
    let visible = 0;
    items.forEach(item => {
      const match = (!query || searchText.get(item.id).includes(query)) &&
        fields.every(field => !values[field] || item[field] === values[field]) && (!starter || item.starter);
      cards.get(item.id).hidden = !match;
      visible += Number(match);
    });
    count.textContent = `Widoczne: ${visible} z ${items.length} propozycji`;
    document.querySelector('#empty').hidden = visible !== 0;
    // filters in the address (#q=…&area=…&starter=1) so a filtered list can be linked; anchors like #p04 are left alone
    try {
      const p = new URLSearchParams();
      if (query) p.set('q', document.querySelector('#query').value.trim());
      fields.forEach(field => { if (values[field]) p.set(field, values[field]); });
      if (starter) p.set('starter', '1');
      if (p.toString() || location.hash.includes('=')) history.replaceState(null, '', p.toString() ? '#' + p : location.pathname);
    } catch (e) { /* history unavailable */ }
  }
  try {
    const h = new URLSearchParams(location.hash.slice(1));
    if (location.hash.includes('=')) {
      if (h.get('q')) document.querySelector('#query').value = h.get('q');
      fields.forEach(field => { const el = document.getElementById(field); if (h.get(field) && [...el.options].some(o => o.value === h.get(field))) el.value = h.get(field); });
      if (h.get('starter') === '1') document.querySelector('#starter').checked = true;
    }
  } catch (e) { /* bad hash */ }

  function cell(tag, text) {
    const node = document.createElement(tag);
    node.textContent = text;
    return node;
  }

  function comparison() {
    const picked = items.filter(item => selected.has(item.id));
    document.querySelectorAll('[data-compare]').forEach(input => { input.checked = selected.has(input.dataset.compare); });
    document.querySelector('#selection-count').textContent = `${selected.size}/3`;
    document.querySelector('#print-comparison').disabled = picked.length === 0;
    compareStatus.textContent = picked.length ? `Wybrano ${picked.length} z maksymalnie 3 propozycji. Wybór pozostaje w tej przeglądarce.` : 'Zaznacz do trzech kart. Wybór pozostaje w tej przeglądarce.';
    try { localStorage.setItem(storageKey, JSON.stringify([...selected])); } catch { /* Keep working without persistence. */ }
    const host = document.querySelector('#compare-table');
    host.replaceChildren();
    if (!picked.length) return;
    const table = document.createElement('table');
    const caption = document.createElement('caption');
    caption.textContent = 'Porównanie propozycji dla Polski';
    table.append(caption);
    const head = document.createElement('thead');
    const heading = document.createElement('tr');
    heading.append(cell('th', 'Aspekt'));
    picked.forEach(item => {
      const th = cell('th', '');
      th.scope = 'col';
      const link = document.createElement('a');
      link.href = `#${item.id.toLowerCase()}`;
      link.textContent = `${item.id}. ${item.title}`;
      th.append(link);
      heading.append(th);
    });
    head.append(heading);
    table.append(head);
    const body = document.createElement('tbody');
    const rows = [['verdict', 'Ocena'], ['change', 'Co zmienia'], ['level', 'Droga wdrożenia'], ['poland', 'W Polsce dziś'], ['draft', 'Szkic autorski'], ['benefit', 'Możliwa korzyść'], ['risk', 'Ryzyko'], ['safeguards', 'Zabezpieczenia'], ['implementation', 'Wdrożenie']];
    rows.forEach(([field, title]) => {
      const row = document.createElement('tr');
      const th = cell('th', title);
      th.scope = 'row';
      row.append(th);
      picked.forEach(item => row.append(cell('td', labels[field] ? labels[field][item[field]] : item[field])));
      body.append(row);
    });
    table.append(body);
    host.append(table);
  }

  document.querySelector('#filters').addEventListener('submit', event => event.preventDefault());
  document.querySelector('#filters').addEventListener('input', filter);
  document.querySelector('#filters').addEventListener('change', filter);
  document.querySelector('#filters').addEventListener('reset', () => setTimeout(filter, 0));
  document.querySelectorAll('[data-compare]').forEach(input => input.addEventListener('change', () => {
    const id = input.dataset.compare;
    if (input.checked && selected.size === 3) {
      input.checked = false;
      compareStatus.textContent = 'Możesz porównać maksymalnie trzy propozycje. Usuń jedną z wybranych.';
      document.querySelector('#porownanie').scrollIntoView();
      return;
    }
    if (input.checked) selected.add(id); else selected.delete(id);
    comparison();
  }));
  document.querySelector('#show-compare').addEventListener('click', () => document.querySelector('#porownanie').scrollIntoView());
  document.querySelector('#clear-selection').addEventListener('click', () => { selected.clear(); comparison(); });
  document.querySelector('#print').addEventListener('click', () => window.print());
  document.querySelector('#print-comparison').addEventListener('click', () => {
    document.body.classList.add('comparison-only');
    window.print();
    document.body.classList.remove('comparison-only');
  });
  let closedBeforePrint = [];
  window.addEventListener('beforeprint', () => {
    closedBeforePrint = [...document.querySelectorAll('details:not([open])')];
    closedBeforePrint.forEach(details => { details.open = true; });
  });
  window.addEventListener('afterprint', () => {
    document.body.classList.remove('comparison-only');
    closedBeforePrint.forEach(details => { details.open = false; });
    closedBeforePrint = [];
  });
  document.querySelectorAll('.starter-grid a').forEach(link => link.addEventListener('click', () => {
    document.querySelector('#filters').reset();
    filter();
  }));
  filter();
  comparison();
})();
