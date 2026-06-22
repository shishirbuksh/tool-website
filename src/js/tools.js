(function () {
  'use strict';

  const STORAGE_KEY = 'sbr_tools_recent_search';
  const MAX_RECENT = 5;
  const $ = (s, p) => (p || document).querySelector(s);
  const $$ = (s, p) => [...(p || document).querySelectorAll(s)];

  const searchInput = $('#toolSearchInput');
  const suggestions = $('#searchSuggestions');
  const suggestionHeader = $('#suggestionHeader');
  const skeletonGrid = $('#skeletonGrid');
  const toolsGrid = $('#toolsGrid');
  const emptyState = $('#emptyState');
  const clearBtn = $('#clearFiltersBtn');
  const categoryBtns = $$('.category-card');
  const sections = $$('.category-section');
  const toolCards = () => $$('.tool-card');

  let currentFocusIdx = -1;
  let suggestionItems = [];

  /* ── Recent searches (localStorage) ── */
  function getRecentSearches() {
    try { return JSON.parse(localStorage.getItem(STORAGE_KEY) || '[]').slice(0, MAX_RECENT); }
    catch { return []; }
  }
  function addRecentSearch(q) {
    const ql = q.trim().toLowerCase();
    if (!ql) return;
    let recents = getRecentSearches().filter(r => r !== ql);
    recents.unshift(ql);
    if (recents.length > MAX_RECENT) recents = recents.slice(0, MAX_RECENT);
    try { localStorage.setItem(STORAGE_KEY, JSON.stringify(recents)); } catch {}
  }
  function clearRecentSearches() {
    try { localStorage.removeItem(STORAGE_KEY); } catch {}
    renderSuggestions(searchInput ? searchInput.value.trim().toLowerCase() : '');
  }

  /* ── All tool names for suggestions ── */
  function getAllToolNames() {
    return toolCards().map(c => {
      const nameEl = c.querySelector('.tool-card-name');
      return nameEl ? nameEl.textContent.trim() : '';
    }).filter(Boolean);
  }

  /* ── Render suggestions dropdown ── */
  function renderSuggestions(query) {
    if (!suggestions || !searchInput) return;
    const q = (query || '').trim().toLowerCase();
    const recent = getRecentSearches();
    let items = [];

    if (q.length > 0) {
      const allNames = getAllToolNames();
      const matches = allNames.filter(n => n.toLowerCase().includes(q)).slice(0, 8);
      items = matches.map(n => ({ label: n, type: 'match' }));
      if (items.length === 0) {
        items = [{ label: 'No matching tools', type: 'empty' }];
      }
    } else {
      if (recent.length > 0) {
        items = recent.map(r => ({ label: r, type: 'recent' }));
        items.push({ label: 'Clear recent searches', type: 'clear' });
      } else {
        const popular = getAllToolNames().slice(0, 6);
        items = popular.map(n => ({ label: n, type: 'popular' }));
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
    if (items.length === 0 || (items.length === 1 && items[0].type === 'empty')) {
      suggestions.classList.remove('open');
      searchInput && searchInput.setAttribute('aria-expanded', 'false');
      return;
    }
    suggestions.classList.add('open');

    const firstType = items[0].type;
    if (firstType === 'recent') suggestionHeader.textContent = 'Recent Searches';
    else if (firstType === 'match') suggestionHeader.textContent = 'Matching Tools';
    else suggestionHeader.textContent = 'Popular Tools';
    suggestions.appendChild(suggestionHeader.cloneNode(true));

    items.forEach((item, i) => {
      const div = document.createElement('div');
      div.className = 'search-suggestion-item';
      div.setAttribute('role', 'option');
      div.setAttribute('id', 'sug-' + i);
      div.setAttribute('aria-selected', 'false');

      let iconSvg = '';
      if (item.type === 'recent') iconSvg = '<svg class="w-3.5 h-3.5 suggestion-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="10"/><polyline points="12 6 12 12 16 14"/></svg>';
      else if (item.type === 'clear') iconSvg = '<svg class="w-3.5 h-3.5 suggestion-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M3 6h18"/><path d="M19 6v14c0 1-1 2-2 2H7c-1 0-2-1-2-2V6"/><path d="M8 6V4c0-1 1-2 2-2h4c1 0 2 1 2 2v2"/></svg>';
      else iconSvg = '<svg class="w-3.5 h-3.5 suggestion-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="11" cy="11" r="8"/><path d="m21 21-4.3-4.3"/></svg>';

      div.innerHTML = iconSvg + '<span class="suggestion-label">' + escapeHtml(item.label) + '</span>';
      if (item.type === 'recent' || item.type === 'popular') {
        const meta = document.createElement('span');
        meta.className = 'suggestion-meta';
        meta.textContent = item.type === 'recent' ? 'Recent' : 'Popular';
        div.appendChild(meta);
      }
      div.addEventListener('mousedown', function (e) {
        e.preventDefault();
        selectSuggestion(i);
      });
      div.addEventListener('mouseenter', function () {
        setFocus(i);
      });
      suggestions.appendChild(div);
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
    if (searchInput) {
      searchInput.value = item.label;
      addRecentSearch(item.label);
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
  }

  function closeSuggestions() {
    suggestions && suggestions.classList.remove('open');
    suggestionItems = [];
    currentFocusIdx = -1;
    searchInput && searchInput.setAttribute('aria-expanded', 'false');
  }

  /* ── Filter tools ── */
  function filterTools() {
    const query = searchInput ? searchInput.value.toLowerCase().trim() : '';
    const activeBtn = document.querySelector('.category-card.active');
    const activeFilter = activeBtn ? activeBtn.getAttribute('data-filter') : 'all';
    let anyVisible = false;

    sections.forEach(function (section) {
      const cat = section.getAttribute('data-category');
      const catMatch = activeFilter === 'all' || activeFilter === cat;
      let hasVisible = false;
      const cards = section.querySelectorAll('.tool-card');

      cards.forEach(function (card) {
        const nameEl = card.querySelector('.tool-card-name');
        const descEl = card.querySelector('.tool-card-desc');
        const name = nameEl ? nameEl.textContent.toLowerCase() : '';
        const desc = descEl ? descEl.textContent.toLowerCase() : '';
        const match = name.includes(query) || desc.includes(query);
        card.style.display = match ? '' : 'none';
        if (match) hasVisible = true;
      });

      const show = catMatch && hasVisible;
      section.style.display = show ? '' : 'none';
      if (show) anyVisible = true;
    });

    if (emptyState) {
      emptyState.classList.toggle('show', !anyVisible);
    }
  }

  /* ── Show skeleton, hide after page ready ── */
  function showSkeleton(show) {
    if (!skeletonGrid || !toolsGrid) return;
    skeletonGrid.classList.toggle('hidden', !show);
    toolsGrid.classList.toggle('hidden', show);
  }

  /* ── Event handlers ── */
  if (searchInput) {
    searchInput.addEventListener('input', window.sbr.debounce(function () {
      const q = searchInput.value.trim().toLowerCase();
      filterTools();
      renderSuggestions(q);
    }, 150));

    searchInput.addEventListener('focus', function () {
      renderSuggestions(this.value.trim().toLowerCase());
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
      } else if (e.key === 'ArrowUp') {
        e.preventDefault();
        const prev = currentFocusIdx > 0 ? currentFocusIdx - 1 : items.length - 1;
        setFocus(prev);
      } else if (e.key === 'Enter' && currentFocusIdx >= 0) {
        e.preventDefault();
        selectSuggestion(currentFocusIdx);
      } else if (e.key === 'Escape') {
        closeSuggestions();
        this.blur();
      } else if (e.key === '/' && document.activeElement !== searchInput) {
        e.preventDefault();
        searchInput.focus();
      }
    });
  }

  document.addEventListener('keydown', function (e) {
    if (e.key === '/' && document.activeElement !== searchInput && document.activeElement !== document.body) return;
    if (e.key === '/' && document.activeElement !== searchInput) {
      e.preventDefault();
      if (searchInput) searchInput.focus();
    }
  });

  /* Category cards */
  if (categoryBtns.length) {
    categoryBtns.forEach(function (btn) {
      btn.addEventListener('click', function () {
        categoryBtns.forEach(function (b) {
          b.classList.remove('active');
          b.setAttribute('aria-selected', 'false');
        });
        this.classList.add('active');
        this.setAttribute('aria-selected', 'true');
        closeSuggestions();
        filterTools();
      });
    });
  }

  /* Clear filters button */
  if (clearBtn) {
    clearBtn.addEventListener('click', function () {
      const allBtn = document.querySelector('.category-card[data-filter="all"]');
      if (allBtn) {
        categoryBtns.forEach(function (b) {
          b.classList.remove('active');
          b.setAttribute('aria-selected', 'false');
        });
        allBtn.classList.add('active');
        allBtn.setAttribute('aria-selected', 'true');
      }
      if (searchInput) searchInput.value = '';
      filterTools();
      if (searchInput) searchInput.focus();
    });
  }

  /* ── Init ── */
  function init() {
    showSkeleton(true);
    requestAnimationFrame(function () {
      setTimeout(function () {
        showSkeleton(false);
        filterTools();
      }, 400);
    });
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }
})();
