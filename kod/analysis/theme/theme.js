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
  const ready = () => { addButton(); addMenu(); };
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
