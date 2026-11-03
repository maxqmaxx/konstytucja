/* Teczka robocza: per-viewer collection of provisions, proposals and search hits (localStorage only).
   Elements marked with data-teczka='{"id","type","title","cite","url"}' get a "+ Do teczki" button;
   their text is read from the first [data-teczka-text] descendant (or the element) at click time.
   window.Teczka.attach(root) wires dynamically added content (e.g. search results). */
(() => {
  'use strict';
  const KEY = 'konstytucja.teczka.v1';
  const base = (() => { const s = document.currentScript && document.currentScript.src; return s ? s.replace(/teczka\.js.*$/, '') : '../teczka/'; })();
  const load = () => { try { return JSON.parse(localStorage.getItem(KEY) || '[]'); } catch { return []; } };
  const save = items => { try { localStorage.setItem(KEY, JSON.stringify(items)); return true; } catch { return false; } };
  const has = id => load().some(i => i.id === id);

  function badge() {
    let b = document.getElementById('teczka-badge');
    if (!b) {
      b = document.createElement('a');
      b.id = 'teczka-badge'; b.href = base + 'index.html';
      b.setAttribute('style', 'position:fixed;right:16px;bottom:16px;z-index:50;background:#006858;color:#fff;padding:10px 16px;border-radius:24px;font:600 14px system-ui,sans-serif;text-decoration:none;box-shadow:0 4px 14px #0003');
      document.body.appendChild(b);
    }
    const n = load().length;
    b.textContent = `Teczka (${n})`;
    b.hidden = n === 0;
  }

  function button(el) {
    if (el.querySelector(':scope > .teczka-add')) return;
    let meta;
    try { meta = JSON.parse(el.dataset.teczka); } catch { return; }
    const btn = document.createElement('button');
    btn.type = 'button'; btn.className = 'teczka-add';
    btn.setAttribute('style', 'margin-top:8px;font:600 12px system-ui,sans-serif;border:1px solid #9fb7ac;background:#fff;color:#006858;border-radius:4px;padding:6px 10px;min-height:36px;cursor:pointer');
    const sync = () => { const inside = has(meta.id); btn.textContent = inside ? '✓ W teczce (usuń)' : '+ Do teczki'; btn.setAttribute('aria-pressed', String(inside)); };
    btn.addEventListener('click', () => {
      let items = load();
      if (items.some(i => i.id === meta.id)) items = items.filter(i => i.id !== meta.id);
      else {
        const src = el.querySelector('[data-teczka-text]') || el;
        items.push({ ...meta, text: (src.innerText || src.textContent || '').trim().slice(0, 6000), note: '', added: new Date().toISOString().slice(0, 10), page: location.href.split('#')[0] + (meta.anchor ? '#' + meta.anchor : '') });
      }
      if (!save(items)) { btn.textContent = 'Przeglądarka blokuje zapis'; return; }
      sync(); badge();
    });
    sync();
    el.appendChild(btn);
  }

  function attach(root = document) { root.querySelectorAll('[data-teczka]').forEach(button); badge(); }
  window.Teczka = { attach, load, save, KEY };
  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', () => attach()); else attach();
  window.addEventListener('storage', e => { if (e.key === KEY) { badge(); document.querySelectorAll('.teczka-add').forEach(b => b.remove()); attach(); } });
})();
