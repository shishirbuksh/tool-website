/* ── StoryBrain AI: tools.js (Alpine.js Tools Directory Component) ── */
(function () {
  'use strict';

  const STORAGE_KEY = 'sbr_tools_recent_search';
  const MAX_RECENT = 5;

  const store = {
    get(k) { try { return localStorage.getItem(k); } catch { return null; } },
    set(k, v) { try { localStorage.setItem(k, v); } catch {} },
    del(k) { try { localStorage.removeItem(k); } catch {} }
  };

  function normTx(s) {
    s = String(s == null ? '' : s);
    try { s = s.normalize('NFC'); } catch (e) {}
    s = s.toLowerCase();
    try { s = s.normalize('NFD').replace(/[\u0300-\u036f]/g, ''); } catch (e) {}
    return s;
  }

  function toolsDirectory() {
    return {
      searchQuery: '',
      activeCategory: 'all',
      showSuggestions: false,
      focusedSuggestionIdx: -1,
      suggestions: [],
      suggestionHeaderTitle: 'Popular Tools',
      recentSearches: [],
      cachedTools: [],
      canScrollLeft: false,
      canScrollRight: false,
      totalVisibleCount: 128,
      categoryMatchCounts: {},

      init() {
        this.loadRecentSearches();
        this.buildToolsCache();
        this.initFromQuery();

        this.$watch('searchQuery', (val) => {
          this.handleQueryChange(val);
        });

        this.$watch('activeCategory', () => {
          this.filterTools();
          this.scrollActiveCategoryTabIntoView();
        });

        // Set up touch move dismiss for search input on mobile
        let touchStartY = 0;
        window.addEventListener('touchstart', (e) => {
          if (e.touches && e.touches[0]) touchStartY = e.touches[0].clientY;
        }, { passive: true });

        window.addEventListener('touchmove', (e) => {
          if (!e.touches || !e.touches[0]) return;
          const diffY = Math.abs(e.touches[0].clientY - touchStartY);
          const tsi = document.getElementById('toolSearchInput');
          if (diffY > 15 && document.activeElement === tsi && tsi) {
            tsi.blur();
          }
        }, { passive: true });

        // Connect global search triggers (mobile navbar / bottom nav search button)
        const setupMobileSearchTrigger = (id) => {
          const btn = document.getElementById(id);
          if (btn) {
            btn.addEventListener('click', (e) => {
              e.preventDefault();
              e.stopPropagation();
              this.focusSearchInput();
            });
          }
        };
        setupMobileSearchTrigger('searchToggleMobileNav');
        setupMobileSearchTrigger('searchToggleMobile');

        // Quick action launch pills
        document.querySelectorAll('[data-quick-search]').forEach((pill) => {
          pill.addEventListener('click', (e) => {
            e.preventDefault();
            const q = pill.getAttribute('data-quick-search') || '';
            this.searchQuery = q;
            this.focusSearchInput();
            const toolsSec = document.getElementById('tools');
            if (toolsSec) toolsSec.scrollIntoView({ behavior: 'smooth', block: 'start' });
          });
        });

        // Initial scroll button state
        this.$nextTick(() => {
          this.updateScrollButtons();
          window.addEventListener('resize', () => this.updateScrollButtons(), { passive: true });
        });
      },

      buildToolsCache() {
        const cards = Array.from(document.querySelectorAll('.tool-card'));
        this.cachedTools = cards.map((c) => {
          const nameEl = c.querySelector('.tool-card-name');
          const descEl = c.querySelector('.tool-card-desc');
          const linkEl = c.closest('a') || c.querySelector('a');
          const sec = c.closest('.category-section');
          const cat = sec ? sec.getAttribute('data-category') : '';
          return {
            el: c,
            name: nameEl ? nameEl.textContent.trim() : '',
            desc: descEl ? descEl.textContent.trim() : '',
            url: linkEl ? linkEl.getAttribute('href') : '',
            category: cat || '',
            nameNorm: normTx(nameEl ? nameEl.textContent : ''),
            descNorm: normTx(descEl ? descEl.textContent : '')
          };
        }).filter((t) => t.name);

        this.filterTools();
      },

      loadRecentSearches() {
        try {
          this.recentSearches = JSON.parse(store.get(STORAGE_KEY) || '[]').slice(0, MAX_RECENT);
        } catch {
          this.recentSearches = [];
        }
      },

      addRecentSearch(q) {
        const ql = q.trim();
        if (!ql) return;
        let recents = this.recentSearches.filter((r) => r.toLowerCase() !== ql.toLowerCase());
        recents.unshift(ql);
        if (recents.length > MAX_RECENT) recents = recents.slice(0, MAX_RECENT);
        this.recentSearches = recents;
        store.set(STORAGE_KEY, JSON.stringify(recents));
      },

      clearRecentSearches() {
        store.del(STORAGE_KEY);
        this.recentSearches = [];
        this.renderSuggestions(this.searchQuery);
      },

      initFromQuery() {
        try {
          const params = new URLSearchParams(window.location.search);
          const catParam = params.get('category');
          const qParam = params.get('q');
          if (catParam) {
            this.activeCategory = catParam;
          }
          if (qParam) {
            this.searchQuery = qParam.trim();
          }
        } catch {}
      },

      handleQueryChange(val) {
        const q = normTx(val);
        // Cross-category convenience check: if active category has 0 matches but other categories do, switch to 'all'
        if (q.length > 0 && this.activeCategory !== 'all') {
          const hasMatchInCurrentCat = this.cachedTools.some(
            (t) => t.category === this.activeCategory && (t.nameNorm.includes(q) || t.descNorm.includes(q))
          );
          if (!hasMatchInCurrentCat) {
            this.activeCategory = 'all';
          }
        }
        this.filterTools();
        if (this.showSuggestions) {
          this.renderSuggestions(val);
        }
      },

      filterTools() {
        const q = normTx(this.searchQuery);
        let visibleCount = 0;
        const counts = {};

        this.cachedTools.forEach((t) => {
          const catMatch = this.activeCategory === 'all' || this.activeCategory === t.category;
          const textMatch = q === '' || t.nameNorm.includes(q) || t.descNorm.includes(q);
          const isVisible = catMatch && textMatch;

          t.el.style.display = isVisible ? '' : 'none';
          if (isVisible) {
            visibleCount++;
            counts[t.category] = (counts[t.category] || 0) + 1;
          }
        });

        this.totalVisibleCount = visibleCount;
        this.categoryMatchCounts = counts;

        // Show/hide category sections
        document.querySelectorAll('.category-section').forEach((sec) => {
          const slug = sec.getAttribute('data-category');
          const secMatch = (this.activeCategory === 'all' || this.activeCategory === slug) && (counts[slug] || 0) > 0;
          sec.style.display = secMatch ? '' : 'none';
        });

        // Sync empty state
        const emptyState = document.getElementById('emptyState');
        if (emptyState) {
          emptyState.classList.toggle('hidden', visibleCount > 0);
          emptyState.classList.toggle('flex', visibleCount === 0);
          emptyState.classList.toggle('show', visibleCount === 0);
        }
      },

      setCategory(slug) {
        this.activeCategory = slug;
      },

      clearSearch() {
        this.searchQuery = '';
        this.closeSuggestions();
        this.focusSearchInput();
      },

      clearAllFilters() {
        this.searchQuery = '';
        this.activeCategory = 'all';
        this.closeSuggestions();
      },

      focusSearchInput() {
        const tsi = document.getElementById('toolSearchInput');
        if (tsi) {
          tsi.scrollIntoView({ behavior: 'smooth', block: 'center' });
          setTimeout(() => tsi.focus({ preventScroll: true }), 150);
        }
      },

      onSearchFocus() {
        this.renderSuggestions(this.searchQuery);
      },

      onSearchBlur() {
        setTimeout(() => this.closeSuggestions(), 220);
      },

      renderSuggestions(query) {
        const q = normTx(query);
        let items = [];

        if (q.length > 0) {
          const matches = this.cachedTools.filter(
            (t) => t.nameNorm.includes(q) || t.descNorm.includes(q)
          ).slice(0, 8);

          items = matches.map((t) => ({
            label: t.name,
            url: t.url,
            type: 'match',
            iconSvg: '<svg class="w-3.5 h-3.5 suggestion-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="11" cy="11" r="8"/><path d="m21 21-4.3-4.3"/></svg>'
          }));

          if (items.length === 0) {
            items = [{
              label: 'No matching tools',
              url: '',
              type: 'empty',
              iconSvg: '<svg class="w-3.5 h-3.5 suggestion-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="10"/><line x1="15" y1="9" x2="9" y2="15"/><line x1="9" y1="9" x2="15" y2="15"/></svg>'
            }];
          }
          this.suggestionHeaderTitle = 'Matching Tools';
        } else {
          if (this.recentSearches.length > 0) {
            items = this.recentSearches.map((r) => {
              const match = this.cachedTools.find((t) => normTx(t.name) === normTx(r));
              return {
                label: r,
                url: match ? match.url : '',
                type: 'recent',
                meta: 'Recent',
                iconSvg: '<svg class="w-3.5 h-3.5 suggestion-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="10"/><polyline points="12 6 12 12 16 14"/></svg>'
              };
            });
            items.push({
              label: 'Clear recent searches',
              url: '',
              type: 'clear',
              iconSvg: '<svg class="w-3.5 h-3.5 suggestion-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M3 6h18"/><path d="M19 6v14c0 1-1 2-2 2H7c-1 0-2-1-2-2V6"/><path d="M8 6V4c0-1 1-2 2-2h4c1 0 2 1 2 2v2"/></svg>'
            });
            this.suggestionHeaderTitle = 'Recent Searches';
          } else {
            const popularSlugs = ['crypto-price-prediction', 'emi-calculator', 'sip-calculator', 'pdf-converter', 'image-background-remover', 'qr-generator'];
            const popular = this.cachedTools.filter((t) => popularSlugs.some((s) => t.url && t.url.includes(s))).slice(0, 6);
            const fallback = popular.length > 0 ? popular : this.cachedTools.slice(0, 6);
            items = fallback.map((t) => ({
              label: t.name,
              url: t.url,
              type: 'popular',
              meta: 'Popular',
              iconSvg: '<svg class="w-3.5 h-3.5 suggestion-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="11" cy="11" r="8"/><path d="m21 21-4.3-4.3"/></svg>'
            }));
            this.suggestionHeaderTitle = 'Popular Tools';
          }
        }

        this.suggestions = items;
        this.focusedSuggestionIdx = -1;
        this.showSuggestions = items.length > 0 && items[0].type !== 'empty';
      },

      selectSuggestion(item, event) {
        if (!item) return;
        if (item.type === 'clear') {
          if (event) { event.preventDefault(); event.stopPropagation(); }
          this.clearRecentSearches();
          return;
        }
        if (item.type === 'empty') {
          if (event) event.preventDefault();
          return;
        }
        if (item.url) {
          this.addRecentSearch(item.label);
          window.location.href = item.url;
          return;
        }
        if (event) event.preventDefault();
        this.searchQuery = item.label;
        this.addRecentSearch(item.label);
        this.closeSuggestions();
      },

      navigateSuggestions(dir) {
        if (!this.showSuggestions || this.suggestions.length === 0) {
          this.renderSuggestions(this.searchQuery);
          return;
        }
        const len = this.suggestions.length;
        this.focusedSuggestionIdx = (this.focusedSuggestionIdx + dir + len) % len;
      },

      onSearchEnter(event) {
        if (this.showSuggestions && this.focusedSuggestionIdx >= 0 && this.suggestions[this.focusedSuggestionIdx]) {
          event.preventDefault();
          this.selectSuggestion(this.suggestions[this.focusedSuggestionIdx], event);
          return;
        }
        const q = normTx(this.searchQuery);
        if (q) {
          const top = this.cachedTools.find((t) => t.nameNorm === q || t.nameNorm.startsWith(q)) ||
                      this.cachedTools.find((t) => t.nameNorm.includes(q));
          if (top && top.url) {
            event.preventDefault();
            this.addRecentSearch(top.name);
            window.location.href = top.url;
          }
        }
      },

      closeSuggestions() {
        this.showSuggestions = false;
        this.focusedSuggestionIdx = -1;
      },

      scrollCategories(delta) {
        const c = document.getElementById('categoryScrollContainer');
        if (c) c.scrollBy({ left: delta, behavior: 'smooth' });
      },

      updateScrollButtons() {
        const c = document.getElementById('categoryScrollContainer');
        if (!c) return;
        const scrollLeft = c.scrollLeft;
        const maxScroll = c.scrollWidth - c.clientWidth;
        const hasOverflow = maxScroll > 8;

        if (!hasOverflow) {
          this.canScrollLeft = false;
          this.canScrollRight = false;
          c.classList.remove('has-left-fade', 'has-right-fade');
          return;
        }

        this.canScrollLeft = scrollLeft > 8;
        this.canScrollRight = scrollLeft < maxScroll - 8;
        c.classList.toggle('has-left-fade', this.canScrollLeft);
        c.classList.toggle('has-right-fade', this.canScrollRight);
      },

      scrollActiveCategoryTabIntoView() {
        const activeTab = document.querySelector(`.category-card[data-filter="${this.activeCategory}"]`);
        if (activeTab) {
          activeTab.scrollIntoView({ inline: 'center', behavior: 'smooth', block: 'nearest' });
        }
      }
    };
  }

  // Expose component function globally
  window.toolsDirectory = toolsDirectory;

  // Register with Alpine when available
  if (window.Alpine) {
    window.Alpine.data('toolsDirectory', toolsDirectory);
  } else {
    document.addEventListener('alpine:init', () => {
      window.Alpine.data('toolsDirectory', toolsDirectory);
    });
  }
})();
