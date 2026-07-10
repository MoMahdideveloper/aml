/**
 * Global CRM search autocomplete — race-safe, keyboard accessible, no HTML injection.
 */
(function () {
  const MIN = 2;
  const DEBOUNCE_MS = 220;

  function esc(s) {
    return String(s == null ? '' : s)
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;');
  }

  function initRoot(root) {
    const input = root.querySelector('.ph-search-input');
    const listbox = root.querySelector('.ph-search-listbox');
    const clearBtn = root.querySelector('.ph-search-clear');
    const status = root.querySelector('.ph-search-status');
    const api = root.getAttribute('data-api');
    const resultsUrl = root.getAttribute('data-results');
    if (!input || !listbox || !api) return;

    let timer = null;
    let seq = 0;
    let controller = null;
    let activeIdx = -1;
    let flat = [];

    const setOpen = (open) => {
      listbox.classList.toggle('hidden', !open);
      input.setAttribute('aria-expanded', open ? 'true' : 'false');
    };

    const setStatus = (msg) => {
      if (status) status.textContent = msg || '';
    };

    const render = (groups, counts) => {
      flat = [];
      const order = ['customers', 'properties', 'deals', 'agents', 'tasks'];
      let html = '';
      let any = false;
      order.forEach((key) => {
        const items = (groups && groups[key]) || [];
        if (!items.length) return;
        any = true;
        html += `<div class="px-3 py-1.5 text-[10px] font-semibold uppercase tracking-wide text-on-surface-variant bg-surface-container">${esc(key)}</div>`;
        items.forEach((hit) => {
          const i = flat.length;
          flat.push(hit);
          html += `<a href="${esc(hit.url)}" role="option" data-idx="${i}" class="ph-search-opt block px-3 py-2 text-sm hover:bg-surface-container focus:bg-surface-container focus:outline-none" id="ph-opt-${root.dataset.uid}-${i}">
            <span class="font-medium">${esc(hit.title)}</span>
            <span class="block text-xs text-on-surface-variant">${esc(hit.subtitle || '')}</span>
          </a>`;
        });
      });
      if (!any) {
        html = `<p class="px-3 py-4 text-xs text-on-surface-variant">No results</p>`;
        setStatus('No results');
      } else {
        setStatus(`${flat.length} suggestions`);
      }
      listbox.innerHTML = html;
      setOpen(true);
      activeIdx = -1;
    };

    const fetchQ = (q) => {
      if (controller) controller.abort();
      controller = new AbortController();
      const my = ++seq;
      setStatus('Loading…');
      const url = `${api}?q=${encodeURIComponent(q)}&limit=5`;
      fetch(url, {
        signal: controller.signal,
        headers: { Accept: 'application/json', 'X-Requested-With': 'XMLHttpRequest' },
        credentials: 'same-origin',
      })
        .then((r) => {
          if (!r.ok) throw new Error('fail');
          return r.json();
        })
        .then((data) => {
          if (my !== seq) return; // stale
          render(data.groups || {}, data.counts || {});
        })
        .catch((err) => {
          if (err.name === 'AbortError') return;
          if (my !== seq) return;
          listbox.innerHTML = `<p class="px-3 py-4 text-xs text-error">Search failed</p>`;
          setOpen(true);
          setStatus('Search failed');
        });
    };

    const onInput = () => {
      const q = (input.value || '').trim();
      clearBtn.classList.toggle('hidden', !q);
      if (timer) clearTimeout(timer);
      if (q.length < MIN) {
        setOpen(false);
        listbox.innerHTML = '';
        setStatus('');
        return;
      }
      timer = setTimeout(() => fetchQ(q), DEBOUNCE_MS);
    };

    input.addEventListener('input', onInput);
    input.addEventListener('keydown', (e) => {
      if (e.key === 'Escape') {
        setOpen(false);
        input.blur();
        e.preventDefault();
        return;
      }
      if (e.key === 'Enter') {
        if (activeIdx >= 0 && flat[activeIdx]) {
          e.preventDefault();
          window.location.href = flat[activeIdx].url;
          return;
        }
        const q = (input.value || '').trim();
        if (q.length >= MIN) {
          e.preventDefault();
          window.location.href = `${resultsUrl}?q=${encodeURIComponent(q)}`;
        }
        return;
      }
      if (e.key === 'ArrowDown' || e.key === 'ArrowUp') {
        if (listbox.classList.contains('hidden') || !flat.length) return;
        e.preventDefault();
        if (e.key === 'ArrowDown') activeIdx = Math.min(flat.length - 1, activeIdx + 1);
        else activeIdx = Math.max(0, activeIdx - 1);
        listbox.querySelectorAll('.ph-search-opt').forEach((el, i) => {
          el.classList.toggle('bg-surface-container', i === activeIdx);
        });
        const opt = listbox.querySelector(`[data-idx="${activeIdx}"]`);
        if (opt) {
          input.setAttribute('aria-activedescendant', opt.id);
          opt.scrollIntoView({ block: 'nearest' });
        }
      }
    });

    clearBtn.addEventListener('click', () => {
      input.value = '';
      clearBtn.classList.add('hidden');
      setOpen(false);
      listbox.innerHTML = '';
      input.focus();
    });

    document.addEventListener('click', (e) => {
      if (!root.contains(e.target)) setOpen(false);
    });
  }

  function init() {
    document.querySelectorAll('[data-search-root]').forEach((root, i) => {
      root.dataset.uid = String(i);
      initRoot(root);
    });

    // "/" focuses first desktop search when not typing in a field
    document.addEventListener('keydown', (e) => {
      if (e.key !== '/' || e.ctrlKey || e.metaKey || e.altKey) return;
      const t = e.target;
      if (t && (t.tagName === 'INPUT' || t.tagName === 'TEXTAREA' || t.isContentEditable)) return;
      const input = document.querySelector('.ph-search-input');
      if (input) {
        e.preventDefault();
        input.focus();
      }
    });

    const mobileOpen = document.getElementById('ph-search-mobile-open');
    const mobileDlg = document.getElementById('ph-search-mobile-dialog');
    if (mobileOpen && mobileDlg) {
      const open = () => {
        mobileDlg.classList.remove('hidden');
        const inp = mobileDlg.querySelector('.ph-search-input');
        if (inp) setTimeout(() => inp.focus(), 50);
      };
      const close = () => mobileDlg.classList.add('hidden');
      mobileOpen.addEventListener('click', open);
      mobileDlg.querySelectorAll('[data-search-mobile-close], [data-search-mobile-backdrop]').forEach((el) => {
        el.addEventListener('click', close);
      });
    }
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }
})();
