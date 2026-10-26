(function () {
  'use strict';

  /* SCHEMA localStorage keys: sb-theme ('light'|'night'), cookieConsent ('accepted'|'rejected'), sbr_tools_recent_search (JSON array) */
  const store = {
    get(k) { try { return localStorage.getItem(k); } catch { return null; } },
    set(k, v) { try { localStorage.setItem(k, v); } catch {} },
    del(k) { try { localStorage.removeItem(k); } catch {} }
  };

  const STORAGE_KEY = 'sbr_tools_recent_search';
  const MAX_RECENT = 5;
  const $ = (s, p) => (p || document).querySelector(s);
  const $$ = (s, p) => [...(p || document).querySelectorAll(s)];

  const searchInput = $('#toolSearchInput');
  const searchClearBtn = $('#toolSearchClear');
  const suggestions = $('#searchSuggestions');
  const suggestionHeader = $('#suggestionHeader');
  const skeletonGrid = $('#skeletonGrid');
  const toolsGrid = $('#toolsGrid');
  const emptyState = $('#emptyState');
  const clearBtn = $('#clearFiltersBtn');
  const categoryBtns = () => $$('.category-card');
  const sections = () => $$('.category-section');
  const toolCards = () => $$('.tool-card');

  let currentFocusIdx = -1;
  let suggestionItems = [];
  let toolsCache = null;

  /* ── In-memory Tools Cache for Sub-millisecond Search ── */
  function getCachedTools() {
    if (toolsCache && toolsCache.length > 0) return toolsCache;
    const cards = toolCards();
    if (cards.length === 0) return [];
    toolsCache = cards.map(c => {
      const nameEl = c.querySelector('.tool-card-name');
      const descEl = c.querySelector('.tool-card-desc');
      const linkEl = c.querySelector('a');
      return {
        card: c,
        name: nameEl ? nameEl.textContent.trim() : '',
        desc: descEl ? descEl.textContent.trim() : '',
        url: linkEl ? linkEl.getAttribute('href') : '',
        nameNorm: normTx(nameEl ? nameEl.textContent : ''),
        descNorm: normTx(descEl ? descEl.textContent : '')
      };
    }).filter(t => t.name);
    return toolsCache;
  }

  /* ── Recent searches ── */
  function getRecentSearches() {
    try { return JSON.parse(store.get(STORAGE_KEY) || '[]').slice(0, MAX_RECENT); }
    catch { return []; }
  }
  function addRecentSearch(q) {
    const ql = q.trim();
    if (!ql) return;
    let recents = getRecentSearches().filter(r => r.toLowerCase() !== ql.toLowerCase());
    recents.unshift(ql);
    if (recents.length > MAX_RECENT) recents = recents.slice(0, MAX_RECENT);
    store.set(STORAGE_KEY, JSON.stringify(recents));
  }
  function clearRecentSearches() {
    store.del(STORAGE_KEY);
    renderSuggestions(searchInput ? searchInput.value.trim() : '');
  }

  /* ── Search Clear Button State ("✕") ── */
  function updateClearButtonState() {
    if (!searchClearBtn || !searchInput) return;
    const hasValue = searchInput.value.length > 0;
    searchClearBtn.classList.toggle('hidden', !hasValue);
    searchClearBtn.classList.toggle('flex', hasValue);
  }

  /* ── Render suggestions dropdown ── */
  function renderSuggestions(query) {
    if (!suggestions || !searchInput) return;
    const q = normTx(query || '');
    const recent = getRecentSearches();
    const allTools = getCachedTools();
    let items = [];

    if (q.length > 0) {
      const matches = allTools.filter(t => t.nameNorm.includes(q) || t.descNorm.includes(q)).slice(0, 8);
      items = matches.map(t => ({ label: t.name, url: t.url, type: 'match' }));
      if (items.length === 0) {
        items = [{ label: 'No matching tools', url: '', type: 'empty' }];
      }
    } else {
      if (recent.length > 0) {
        items = recent.map(r => {
          const matchTool = allTools.find(t => normTx(t.name) === normTx(r));
          return { label: r, url: matchTool ? matchTool.url : '', type: 'recent' };
        });
        items.push({ label: 'Clear recent searches', url: '', type: 'clear' });
      } else {
        const popularSlugs = ['crypto-price-prediction', 'emi-calculator', 'sip-calculator', 'pdf-converter', 'image-background-remover', 'qr-generator'];
        const popular = allTools.filter(t => popularSlugs.some(slug => t.url && t.url.includes(slug))).slice(0, 6);
        const fallback = popular.length > 0 ? popular : allTools.slice(0, 6);
        items = fallback.map(t => ({ label: t.name, url: t.url, type: 'popular' }));
      }
    }

    suggestionItems = items;
    currentFocusIdx = -1;
    buildSuggestionList(items);
    searchInput.setAttribute('aria-expanded', items.length > 0 && items[0].type !== 'empty' ? 'true' : 'false');
  }

  function buildSuggestionList(items) {
    if (!suggestions || !suggestionHeader) return;
    suggestions.innerHTML = '';
    if (searchInput) searchInput.removeAttribute('aria-activedescendant');

    if (items.length === 0 || (items.length === 1 && items[0].type === 'empty')) {
      suggestions.classList.remove('open');
      suggestions.classList.add('hidden');
      if (searchInput) searchInput.setAttribute('aria-expanded', 'false');
      return;
    }

    suggestions.classList.remove('hidden');
    suggestions.classList.add('open');

    const firstType = items[0].type;
    const headerClone = suggestionHeader.cloneNode(true);
    headerClone.removeAttribute('id');
    if (firstType === 'recent') headerClone.textContent = 'Recent Searches';
    else if (firstType === 'match') headerClone.textContent = 'Matching Tools';
    else headerClone.textContent = 'Popular Tools';
    suggestions.appendChild(headerClone);

    items.forEach((item, i) => {
      const el = item.url ? document.createElement('a') : document.createElement('div');
      if (item.url) el.setAttribute('href', item.url);
      el.className = 'search-suggestion-item' + (item.url ? ' group' : '');
      el.setAttribute('role', 'option');
      el.setAttribute('id', 'sug-' + i);
      el.setAttribute('aria-selected', 'false');

      let iconSvg = '';
      if (item.type === 'recent') iconSvg = '<svg class="w-3.5 h-3.5 suggestion-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="10"/><polyline points="12 6 12 12 16 14"/></svg>';
      else if (item.type === 'clear') iconSvg = '<svg class="w-3.5 h-3.5 suggestion-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M3 6h18"/><path d="M19 6v14c0 1-1 2-2 2H7c-1 0-2-1-2-2V6"/><path d="M8 6V4c0-1 1-2 2-2h4c1 0 2 1 2 2v2"/></svg>';
      else iconSvg = '<svg class="w-3.5 h-3.5 suggestion-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="11" cy="11" r="8"/><path d="m21 21-4.3-4.3"/></svg>';

      el.innerHTML = iconSvg + '<span class="suggestion-label">' + escapeHtml(item.label) + '</span>';
      if (item.type === 'recent' || item.type === 'popular') {
        const meta = document.createElement('span');
        meta.className = 'suggestion-meta';
        meta.textContent = item.type === 'recent' ? 'Recent' : 'Popular';
        el.appendChild(meta);
      } else if (item.url) {
        const arrow = document.createElement('span');
        arrow.className = 'text-primary/70 text-xs font-semibold';
        arrow.textContent = '→';
        el.appendChild(arrow);
      }

      el.addEventListener('pointerdown', function (e) {
        if (item.url) {
          addRecentSearch(item.label);
          return;
        }
        e.preventDefault();
        selectSuggestion(i);
      });

      el.addEventListener('mouseenter', function () {
        setFocus(i);
      });
      suggestions.appendChild(el);
    });
  }

  function escapeHtml(s) {
    const d = document.createElement('div');
    d.textContent = s;
    return d.innerHTML;
  }

  function selectSuggestion(idx) {
    if (idx < 0 || idx >= suggestionItems.length) return;
    const item = suggestionItems[idx];
    if (item.type === 'clear') { clearRecentSearches(); return; }
    if (item.type === 'empty') return;
    if (item.url) {
      addRecentSearch(item.label);
      window.location.href = item.url;
      return;
    }
    if (searchInput) {
      searchInput.value = item.label;
      addRecentSearch(item.label);
      updateClearButtonState();
    }
    closeSuggestions();
    filterTools();
  }

  function setFocus(idx) {
    $$('.search-suggestion-item').forEach((el, i) => {
      el.classList.toggle('active', i === idx);
      el.setAttribute('aria-selected', i === idx ? 'true' : 'false');
    });
    currentFocusIdx = idx;
    if (searchInput) {
      if (idx >= 0) searchInput.setAttribute('aria-activedescendant', 'sug-' + idx);
      else searchInput.removeAttribute('aria-activedescendant');
    }
  }

  function closeSuggestions() {
    if (suggestions) {
      suggestions.classList.remove('open');
      suggestions.classList.add('hidden');
    }
    suggestionItems = [];
    currentFocusIdx = -1;
    if (searchInput) {
      searchInput.setAttribute('aria-expanded', 'false');
      searchInput.removeAttribute('aria-activedescendant');
    }
  }

  /* ── Filter tools ── */
  function normTx(s) {
    s = String(s == null ? '' : s);
    try { s = s.normalize('NFC'); } catch (e) {}
    s = s.toLowerCase();
    try { s = s.normalize('NFD').replace(/[\u0300-\u036f]/g, ''); } catch (e) {}
    return s;
  }

  function filterTools() {
    const query = searchInput ? normTx(searchInput.value.trim()) : '';
    const activeBtn = document.querySelector('.category-card.active');
    let activeFilter = activeBtn ? activeBtn.getAttribute('data-filter') : 'all';
    let anyVisible = false;

    // Cross-category search convenience
    if (query.length > 0 && activeFilter !== 'all') {
      const currentCatMatches = getCachedTools().some(t => {
        const cat = t.card.closest('.category-section')?.getAttribute('data-category');
        return cat === activeFilter && (t.nameNorm.includes(query) || t.descNorm.includes(query));
      });
      if (!currentCatMatches) {
        activeFilter = 'all';
      }
    }

    sections().forEach(function (section) {
      const cat = section.getAttribute('data-category');
      const catMatch = activeFilter === 'all' || activeFilter === cat;
      let hasVisible = false;
      const cards = section.querySelectorAll('.tool-card');

      cards.forEach(function (card) {
        const nameEl = card.querySelector('.tool-card-name');
        const descEl = card.querySelector('.tool-card-desc');
        const name = nameEl ? normTx(nameEl.textContent) : '';
        const desc = descEl ? normTx(descEl.textContent) : '';
        const match = query === '' || name.includes(query) || desc.includes(query);
        card.style.display = match ? '' : 'none';
        if (match) hasVisible = true;
      });

      const show = catMatch && hasVisible;
      section.style.display = show ? '' : 'none';
      if (show) anyVisible = true;
    });

    if (emptyState) {
      emptyState.classList.toggle('show', !anyVisible);
      emptyState.classList.toggle('hidden', anyVisible);
      emptyState.classList.toggle('flex', !anyVisible);
    }
  }

  /* ── Event handlers ── */
  if (searchInput) {
    searchInput.addEventListener('input', window.sbr.debounce(function () {
      const q = normTx(searchInput.value.trim());
      updateClearButtonState();
      filterTools();
      renderSuggestions(q);
    }, 60));

    searchInput.addEventListener('focus', function () {
      renderSuggestions(this.value.trim());
    });

    searchInput.addEventListener('blur', function () {
      setTimeout(closeSuggestions, 200);
    });

    searchInput.addEventListener('keydown', function (e) {
      const items = $$('.search-suggestion-item');
      if (e.key === 'ArrowDown') {
        e.preventDefault();
        const next = currentFocusIdx < items.length - 1 ? currentFocusIdx + 1 : 0;
        setFocus(next);
        if (items[next]) items[next].scrollIntoView({ block: 'nearest' });
      } else if (e.key === 'ArrowUp') {
        e.preventDefault();
        const prev = currentFocusIdx > 0 ? currentFocusIdx - 1 : items.length - 1;
        setFocus(prev);
        if (items[prev]) items[prev].scrollIntoView({ block: 'nearest' });
      } else if (e.key === 'Enter') {
        if (currentFocusIdx >= 0 && items[currentFocusIdx]) {
          e.preventDefault();
          selectSuggestion(currentFocusIdx);
        } else {
          const q = normTx(searchInput.value.trim());
          if (q) {
            const allTools = getCachedTools();
            const top = allTools.find(t => t.nameNorm === q || t.nameNorm.startsWith(q)) || allTools.find(t => t.nameNorm.includes(q));
            if (top && top.url) {
              e.preventDefault();
              addRecentSearch(top.name);
              window.location.href = top.url;
            }
          }
        }
      } else if (e.key === 'Escape') {
        closeSuggestions();
      }
    });
  }

  // Clear button ("✕") listener
  if (searchClearBtn) {
    searchClearBtn.addEventListener('click', function (e) {
      e.preventDefault();
      if (!searchInput) return;
      searchInput.value = '';
      updateClearButtonState();
      filterTools();
      closeSuggestions();
      searchInput.focus();
    });
  }

  // Touch-Scroll Keyboard Dismissal
  let touchStartY = 0;
  window.addEventListener('touchstart', function (e) {
    if (e.touches && e.touches[0]) touchStartY = e.touches[0].clientY;
  }, { passive: true });

  window.addEventListener('touchmove', function (e) {
    if (!e.touches || !e.touches[0] || !searchInput) return;
    const currentY = e.touches[0].clientY;
    const diffY = Math.abs(currentY - touchStartY);
    if (diffY > 15 && document.activeElement === searchInput) {
      searchInput.blur();
    }
  }, { passive: true });

  // Quick Action Launch Pills
  $$('[data-quick-search]').forEach(pill => {
    pill.addEventListener('click', function (e) {
      const query = this.getAttribute('data-quick-search');
      if (searchInput) {
        searchInput.value = query;
        updateClearButtonState();
        filterTools();
        searchInput.focus();
        const toolsSection = document.getElementById('tools');
        if (toolsSection) {
          toolsSection.scrollIntoView({ behavior: 'smooth', block: 'start' });
        }
      }
    });
  });

  // Category Tab Switching (Hybrid <a href> and <button>)
  document.addEventListener('click', function (e) {
    const btn = e.target.closest('.category-card');
    if (!btn) return;
    e.preventDefault(); // Intercept link click for smooth in-page filter
    const filter = btn.getAttribute('data-filter');

    categoryBtns().forEach(b => {
      b.classList.remove('active', 'bg-base-content', 'text-base-100', 'border-base-content', 'shadow-md');
      b.classList.add('bg-base-100/80', 'border-base-content/10');
      b.setAttribute('aria-selected', 'false');
      b.setAttribute('tabindex', '-1');
      const icon = b.querySelector('.category-card-icon');
      if (icon) { icon.classList.remove('text-base-100'); icon.classList.add('text-base-content/60'); }
      const count = b.querySelector('.category-card-count');
      if (count) { count.classList.remove('bg-base-100/20', 'text-base-100'); count.classList.add('bg-base-content/10', 'text-base-content/60'); }
    });

    btn.classList.add('active', 'bg-base-content', 'text-base-100', 'border-base-content', 'shadow-md');
    btn.classList.remove('bg-base-100/80', 'border-base-content/10');
    btn.setAttribute('aria-selected', 'true');
    btn.setAttribute('tabindex', '0');
    const bIcon = btn.querySelector('.category-card-icon');
    if (bIcon) { bIcon.classList.add('text-base-100'); bIcon.classList.remove('text-base-content/60'); }
    const bCount = btn.querySelector('.category-card-count');
    if (bCount) { bCount.classList.add('bg-base-100/20', 'text-base-100'); bCount.classList.remove('bg-base-content/10', 'text-base-content/60'); }

    // Auto-scroll selected tab to center on mobile
    btn.scrollIntoView({ inline: 'center', behavior: 'smooth', block: 'nearest' });

    filterTools();
  });

  // Mobile navbar & bottom nav search click redirection to in-page search
  const mobileNavSearch = $('#searchToggleMobileNav');
  const mobileHeaderSearch = $('#searchToggleMobile');

  function focusInPageSearch(e) {
    if (!searchInput) return;
    e.preventDefault();
    e.stopPropagation();
    searchInput.scrollIntoView({ behavior: 'smooth', block: 'center' });
    setTimeout(() => {
      searchInput.focus({ preventScroll: true });
    }, 200);
  }

  if (mobileNavSearch) mobileNavSearch.addEventListener('click', focusInPageSearch);
  if (mobileHeaderSearch) mobileHeaderSearch.addEventListener('click', focusInPageSearch);

  // Clear filters button in empty state
  if (clearBtn) {
    clearBtn.addEventListener('click', function () {
      if (searchInput) {
        searchInput.value = '';
        updateClearButtonState();
      }
      const allTab = document.querySelector('.category-card[data-filter="all"]');
      if (allTab) allTab.click();
      else filterTools();
    });
  }

  // Initialize tool cache on DOMContentLoaded
  document.addEventListener('DOMContentLoaded', function () {
    getCachedTools();
    updateClearButtonState();
  });

})();
