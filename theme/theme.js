// Theme switch: follows the system setting until the reader picks one; choice remembered in this browser.
(() => {
  const KEY = 'konstytucja.theme';
  const root = document.documentElement;
  let saved = null;
  try { saved = localStorage.getItem(KEY); } catch (e) { /* storage blocked */ }
  if (saved === 'dark' || saved === 'light') root.dataset.theme = saved;
  const isDark = () => root.dataset.theme ? root.dataset.theme === 'dark' : matchMedia('(prefers-color-scheme: dark)').matches;
  function addButton() {
    if (document.querySelector('.theme-toggle')) return;
    const nav = document.querySelector('.site-nav');
    const b = document.createElement('button');
    b.type = 'button';
    b.className = 'theme-toggle';
    const sync = () => {
      const d = isDark();
      b.textContent = d ? '☀ Jasny' : '☾ Ciemny';
      b.setAttribute('aria-label', d ? 'Włącz jasny motyw' : 'Włącz ciemny motyw');
    };
    b.addEventListener('click', () => {
      root.dataset.theme = isDark() ? 'light' : 'dark';
      try { localStorage.setItem(KEY, root.dataset.theme); } catch (e) { /* storage blocked */ }
      sync();
      document.dispatchEvent(new CustomEvent('themechange'));
    });
    sync();
    if (nav) nav.appendChild(b);
    else { b.classList.add('floating'); document.body.appendChild(b); }
  }
  // Phone menu: one button instead of a sideways-scrolling strip; shows the current section.
  function addMenu() {
    const nav = document.querySelector('.site-nav'), links = nav && nav.querySelector('.nav-links');
    if (!links || nav.querySelector('.nav-menu-btn')) return;
    links.id = links.id || 'nav-links';
    const cur = links.querySelector('[aria-current=page]');
    const b = document.createElement('button');
    b.type = 'button';
    b.className = 'nav-menu-btn';
    b.setAttribute('aria-controls', links.id);
    b.setAttribute('aria-expanded', 'false');
    b.textContent = '☰ ' + (cur ? cur.textContent : 'Menu');
    b.setAttribute('aria-label', 'Menu serwisu' + (cur ? ', teraz: ' + cur.textContent : ''));
    const set = open => { nav.classList.toggle('open', open); b.setAttribute('aria-expanded', String(open)); };
    b.addEventListener('click', () => set(!nav.classList.contains('open')));
    document.addEventListener('keydown', e => { if (e.key === 'Escape' && nav.classList.contains('open')) { set(false); b.focus(); } });
    nav.insertBefore(b, links);
    nav.classList.add('js-menu');
  }
  // Long pages: "Spis treści" panel built from the h2 headings (skipped where the page has its own .toc) and "do góry".
  function addToc() {
    const main = document.querySelector('main') || document.body;
    const heads = [...main.querySelectorAll('h2')].filter(h => h.offsetParent !== null && h.textContent.trim());
    const own = document.querySelector('.toc, nav.toc, #toc');
    const long = document.documentElement.scrollHeight > innerHeight * 3;
    if (!long) return;
    const bar = document.createElement('div');
    bar.className = 'page-tools';
    const up = document.createElement('button');
    up.type = 'button'; up.className = 'pt-btn pt-up'; up.textContent = '↑'; up.title = 'Do góry'; up.setAttribute('aria-label', 'Przewiń do góry');
    up.addEventListener('click', () => scrollTo({ top: 0, behavior: 'smooth' }));
    if (!own && heads.length >= 4) {
      const used = new Set();
      heads.forEach(h => {
        if (!h.id) {
          let id = h.textContent.trim().toLowerCase().normalize('NFD').replace(/[\u0300-\u036f]/g, '').replace(/ł/g, 'l').replace(/[^a-z0-9]+/g, '-').replace(/^-|-$/g, '').slice(0, 40) || 'sekcja';
          while (used.has(id) || document.getElementById(id)) id += '-2';
          h.id = id;
        }
        used.add(h.id);
      });
      const panel = document.createElement('nav');
      panel.className = 'pt-panel'; panel.id = 'spis-tresci'; panel.hidden = true; panel.setAttribute('aria-label', 'Spis treści');
      panel.innerHTML = '<b>Spis treści</b><ol>' + heads.map(h => `<li><a href="#${h.id}">${h.textContent.trim().replace(/[<>&]/g, '')}</a></li>`).join('') + '</ol>';
      const b = document.createElement('button');
      b.type = 'button'; b.className = 'pt-btn pt-toc'; b.textContent = '≡ Spis treści';
      b.setAttribute('aria-controls', panel.id); b.setAttribute('aria-expanded', 'false');
      const set = open => { panel.hidden = !open; b.setAttribute('aria-expanded', String(open)); };
      b.addEventListener('click', () => set(panel.hidden));
      panel.addEventListener('click', e => { if (e.target.closest('a')) set(false); });
      document.addEventListener('keydown', e => { if (e.key === 'Escape' && !panel.hidden) { set(false); b.focus(); } });
      document.addEventListener('click', e => { if (!panel.hidden && !e.target.closest('.page-tools')) set(false); });
      const links = [...panel.querySelectorAll('a')];
      if ('IntersectionObserver' in window) {
        const io = new IntersectionObserver(es => es.forEach(en => { if (en.isIntersecting) links.forEach(a => a.classList.toggle('on', a.hash === '#' + en.target.id)); }), { rootMargin: '0px 0px -70% 0px' });
        heads.forEach(h => io.observe(h));
      }
      bar.append(panel, b);
    }
    bar.append(up);
    document.body.append(bar);
    const vis = () => bar.classList.toggle('scrolled', scrollY > innerHeight);
    addEventListener('scroll', vis, { passive: true }); vis();
  }
  const ready = () => { addButton(); addMenu(); addToc(); };
  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', ready); else ready();
  // 'Zgłoś błąd': prefilled GitHub issue built from data-where / data-current at click time
  document.addEventListener('click', e => {
    const a = e.target.closest && e.target.closest('a.report[data-where]');
    if (!a) return;
    const where = a.dataset.where, cur = a.dataset.current || '';
    const page = location.protocol === 'file:' ? '' : `\n**Strona:** ${location.href.split('#')[0]}`;
    const body = `**Gdzie:** ${where}${page}\n\n${cur ? `**Obecnie:** ${cur}\n\n` : ''}**Co jest źle:**\n\n**Jak powinno być i skąd to wiesz (źródło, link do przepisu):**\n`;
    a.href = a.href.split('?')[0] + '?' + new URLSearchParams({ labels: 'dane', title: ('Błąd: ' + where).slice(0, 120), body });
  });
})();
