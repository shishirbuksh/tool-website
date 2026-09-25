(() => {
  // src/js/tools.js
  (function() {
    "use strict";
    const store = { get(k) {
      try {
        return localStorage.getItem(k);
      } catch {
        return null;
      }
    }, set(k, v) {
      try {
        localStorage.setItem(k, v);
      } catch {
      }
    }, del(k) {
      try {
        localStorage.removeItem(k);
      } catch {
      }
    } };
    const STORAGE_KEY = "sbr_tools_recent_search";
    const MAX_RECENT = 5;
    const $ = (s, p) => (p || document).querySelector(s);
    const $$ = (s, p) => [...(p || document).querySelectorAll(s)];
    const searchInput = $("#toolSearchInput");
    const suggestions = $("#searchSuggestions");
    const suggestionHeader = $("#suggestionHeader");
    const skeletonGrid = $("#skeletonGrid");
    const toolsGrid = $("#toolsGrid");
    const emptyState = $("#emptyState");
    const clearBtn = $("#clearFiltersBtn");
    const categoryBtns = $$(".category-card");
    const sections = $$(".category-section");
    const toolCards = () => $$(".tool-card");
    let currentFocusIdx = -1;
    let suggestionItems = [];
    function getRecentSearches() {
      try {
        return JSON.parse(store.get(STORAGE_KEY) || "[]").slice(0, MAX_RECENT);
      } catch {
        return [];
      }
    }
    function addRecentSearch(q) {
      const ql = q.trim().toLowerCase();
      if (!ql) return;
      let recents = getRecentSearches().filter((r) => r !== ql);
      recents.unshift(ql);
      if (recents.length > MAX_RECENT) recents = recents.slice(0, MAX_RECENT);
      store.set(STORAGE_KEY, JSON.stringify(recents));
    }
    function clearRecentSearches() {
      store.del(STORAGE_KEY);
      renderSuggestions(searchInput ? searchInput.value.trim().toLowerCase() : "");
    }
    function getAllToolNames() {
      return toolCards().map((c) => {
        const nameEl = c.querySelector(".tool-card-name");
        return nameEl ? nameEl.textContent.trim() : "";
      }).filter(Boolean);
    }
    function renderSuggestions(query) {
      if (!suggestions || !searchInput) return;
      const q = (query || "").trim().toLowerCase();
      const recent = getRecentSearches();
      let items = [];
      if (q.length > 0) {
        const allNames = getAllToolNames();
        const matches = allNames.filter((n) => n.toLowerCase().includes(q)).slice(0, 8);
        items = matches.map((n) => ({ label: n, type: "match" }));
        if (items.length === 0) {
          items = [{ label: "No matching tools", type: "empty" }];
        }
      } else {
        if (recent.length > 0) {
          items = recent.map((r) => ({ label: r, type: "recent" }));
          items.push({ label: "Clear recent searches", type: "clear" });
        } else {
          const popular = getAllToolNames().slice(0, 6);
          items = popular.map((n) => ({ label: n, type: "popular" }));
        }
      }
      suggestionItems = items;
      currentFocusIdx = -1;
      buildSuggestionList(items);
      searchInput.setAttribute("aria-expanded", items.length > 0 && items[0].type !== "empty" ? "true" : "false");
    }
    function buildSuggestionList(items) {
      if (!suggestions || !suggestionHeader) return;
      suggestions.innerHTML = "";
      if (searchInput) searchInput.removeAttribute("aria-activedescendant");
      if (items.length === 0 || items.length === 1 && items[0].type === "empty") {
        suggestions.classList.remove("open");
        searchInput && searchInput.setAttribute("aria-expanded", "false");
        return;
      }
      suggestions.classList.add("open");
      const firstType = items[0].type;
      const headerClone = suggestionHeader.cloneNode(true);
      headerClone.removeAttribute("id");
      if (firstType === "recent") headerClone.textContent = "Recent Searches";
      else if (firstType === "match") headerClone.textContent = "Matching Tools";
      else headerClone.textContent = "Popular Tools";
      suggestions.appendChild(headerClone);
      items.forEach((item, i) => {
        const div = document.createElement("div");
        div.className = "search-suggestion-item";
        div.setAttribute("role", "option");
        div.setAttribute("id", "sug-" + i);
        div.setAttribute("aria-selected", "false");
        let iconSvg = "";
        if (item.type === "recent") iconSvg = '<svg class="w-3.5 h-3.5 suggestion-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="10"/><polyline points="12 6 12 12 16 14"/></svg>';
        else if (item.type === "clear") iconSvg = '<svg class="w-3.5 h-3.5 suggestion-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M3 6h18"/><path d="M19 6v14c0 1-1 2-2 2H7c-1 0-2-1-2-2V6"/><path d="M8 6V4c0-1 1-2 2-2h4c1 0 2 1 2 2v2"/></svg>';
        else iconSvg = '<svg class="w-3.5 h-3.5 suggestion-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="11" cy="11" r="8"/><path d="m21 21-4.3-4.3"/></svg>';
        div.innerHTML = iconSvg + '<span class="suggestion-label">' + escapeHtml(item.label) + "</span>";
        if (item.type === "recent" || item.type === "popular") {
          const meta = document.createElement("span");
          meta.className = "suggestion-meta";
          meta.textContent = item.type === "recent" ? "Recent" : "Popular";
          div.appendChild(meta);
        }
        div.addEventListener("mousedown", function(e) {
          e.preventDefault();
          selectSuggestion(i);
        });
        div.addEventListener("mouseenter", function() {
          setFocus(i);
        });
        suggestions.appendChild(div);
      });
    }
    function escapeHtml(s) {
      const d = document.createElement("div");
      d.textContent = s;
      return d.innerHTML;
    }
    function selectSuggestion(idx) {
      if (idx < 0 || idx >= suggestionItems.length) return;
      const item = suggestionItems[idx];
      if (item.type === "clear") {
        clearRecentSearches();
        return;
      }
      if (item.type === "empty") return;
      if (searchInput) {
        searchInput.value = item.label;
        addRecentSearch(item.label);
      }
      closeSuggestions();
      filterTools();
    }
    function setFocus(idx) {
      $$(".search-suggestion-item").forEach((el, i) => {
        el.classList.toggle("active", i === idx);
        el.setAttribute("aria-selected", i === idx ? "true" : "false");
      });
      currentFocusIdx = idx;
      if (searchInput) {
        if (idx >= 0) searchInput.setAttribute("aria-activedescendant", "sug-" + idx);
        else searchInput.removeAttribute("aria-activedescendant");
      }
    }
    function closeSuggestions() {
      suggestions && suggestions.classList.remove("open");
      suggestionItems = [];
      currentFocusIdx = -1;
      if (searchInput) {
        searchInput.setAttribute("aria-expanded", "false");
        searchInput.removeAttribute("aria-activedescendant");
      }
    }
    function filterTools() {
      const query = searchInput ? searchInput.value.toLowerCase().trim() : "";
      const activeBtn = document.querySelector(".category-card.active");
      const activeFilter = activeBtn ? activeBtn.getAttribute("data-filter") : "all";
      let anyVisible = false;
      sections.forEach(function(section) {
        const cat = section.getAttribute("data-category");
        const catMatch = activeFilter === "all" || activeFilter === cat;
        let hasVisible = false;
        const cards = section.querySelectorAll(".tool-card");
        cards.forEach(function(card) {
          const nameEl = card.querySelector(".tool-card-name");
          const descEl = card.querySelector(".tool-card-desc");
          const name = nameEl ? nameEl.textContent.toLowerCase() : "";
          const desc = descEl ? descEl.textContent.toLowerCase() : "";
          const match = name.includes(query) || desc.includes(query);
          card.style.display = match ? "" : "none";
          if (match) hasVisible = true;
        });
        const show = catMatch && hasVisible;
        section.style.display = show ? "" : "none";
        if (show) anyVisible = true;
      });
      if (emptyState) {
        emptyState.classList.toggle("show", !anyVisible);
      }
    }
    function showSkeleton(show) {
      if (!skeletonGrid || !toolsGrid) return;
      skeletonGrid.classList.toggle("hidden", !show);
      toolsGrid.classList.toggle("hidden", show);
    }
    if (searchInput) {
      searchInput.addEventListener("input", window.sbr.debounce(function() {
        const q = searchInput.value.trim().toLowerCase();
        filterTools();
        renderSuggestions(q);
      }, 150));
      searchInput.addEventListener("focus", function() {
        renderSuggestions(this.value.trim().toLowerCase());
      });
      searchInput.addEventListener("blur", function() {
        setTimeout(closeSuggestions, 200);
      });
      searchInput.addEventListener("keydown", function(e) {
        const items = $$(".search-suggestion-item");
        if (e.key === "ArrowDown") {
          e.preventDefault();
          const next = currentFocusIdx < items.length - 1 ? currentFocusIdx + 1 : 0;
          setFocus(next);
          if (items[next]) items[next].scrollIntoView({ block: "nearest" });
        } else if (e.key === "ArrowUp") {
          e.preventDefault();
          const prev = currentFocusIdx > 0 ? currentFocusIdx - 1 : items.length - 1;
          setFocus(prev);
          if (items[prev]) items[prev].scrollIntoView({ block: "nearest" });
        } else if (e.key === "Enter" && currentFocusIdx >= 0) {
          e.preventDefault();
          selectSuggestion(currentFocusIdx);
        } else if (e.key === "Escape") {
          closeSuggestions();
          this.blur();
        }
      });
    }
    function _isEditable(el) {
      if (!el || !el.tagName) return false;
      const t = el.tagName.toLowerCase();
      return t === "input" || t === "textarea" || t === "select" || el.isContentEditable === true;
    }
    document.addEventListener("keydown", function(e) {
      if (e.key !== "/" || e.ctrlKey || e.metaKey || e.altKey) return;
      const dia = document.getElementById("searchDialog");
      if (dia && dia.open) return;
      if (_isEditable(document.activeElement)) return;
      if (!searchInput) return;
      e.preventDefault();
      searchInput.focus();
      try {
        searchInput.scrollIntoView({ block: "nearest", behavior: "smooth" });
      } catch {
      }
    });
    if (categoryBtns.length) {
      categoryBtns.forEach(function(btn, idx) {
        btn.addEventListener("click", function() {
          categoryBtns.forEach(function(b) {
            b.classList.remove("active");
            b.setAttribute("aria-selected", "false");
            b.setAttribute("tabindex", "-1");
          });
          this.classList.add("active");
          this.setAttribute("aria-selected", "true");
          this.removeAttribute("tabindex");
          closeSuggestions();
          filterTools();
        });
        btn.addEventListener("keydown", function(e) {
          if (e.key !== "ArrowRight" && e.key !== "ArrowLeft" && e.key !== "Home" && e.key !== "End") return;
          e.preventDefault();
          let next = idx;
          if (e.key === "ArrowRight") next = (idx + 1) % categoryBtns.length;
          else if (e.key === "ArrowLeft") next = (idx - 1 + categoryBtns.length) % categoryBtns.length;
          else if (e.key === "Home") next = 0;
          else if (e.key === "End") next = categoryBtns.length - 1;
          categoryBtns[next].focus();
          categoryBtns[next].click();
        });
        if (!btn.classList.contains("active")) btn.setAttribute("tabindex", "-1");
      });
    }
    if (clearBtn) {
      clearBtn.addEventListener("click", function() {
        const allBtn = document.querySelector('.category-card[data-filter="all"]');
        if (allBtn) {
          categoryBtns.forEach(function(b) {
            b.classList.remove("active");
            b.setAttribute("aria-selected", "false");
            b.setAttribute("tabindex", "-1");
          });
          allBtn.classList.add("active");
          allBtn.setAttribute("aria-selected", "true");
          allBtn.removeAttribute("tabindex");
        }
        if (searchInput) searchInput.value = "";
        filterTools();
        if (searchInput) searchInput.focus();
      });
    }
    function init() {
      showSkeleton(false);
      filterTools();
    }
    if (document.readyState === "loading") {
      document.addEventListener("DOMContentLoaded", init);
    } else {
      init();
    }
  })();
})();
//# sourceMappingURL=data:application/json;base64,ewogICJ2ZXJzaW9uIjogMywKICAic291cmNlcyI6IFsiLi4vLi4vc3JjL2pzL3Rvb2xzLmpzIl0sCiAgInNvdXJjZXNDb250ZW50IjogWyIoZnVuY3Rpb24gKCkge1xuICAndXNlIHN0cmljdCc7XG5cbiAgLyogU0NIRU1BIGxvY2FsU3RvcmFnZSBrZXlzOiBzYi10aGVtZSAoJ2xpZ2h0J3wnbmlnaHQnKSwgY29va2llQ29uc2VudCAoJ2FjY2VwdGVkJ3wncmVqZWN0ZWQnKSwgc2JyX3Rvb2xzX3JlY2VudF9zZWFyY2ggKEpTT04gYXJyYXkpICovXG4gIGNvbnN0IHN0b3JlPXtnZXQoayl7dHJ5e3JldHVybiBsb2NhbFN0b3JhZ2UuZ2V0SXRlbShrKX1jYXRjaHtyZXR1cm4gbnVsbH19LHNldChrLHYpe3RyeXtsb2NhbFN0b3JhZ2Uuc2V0SXRlbShrLHYpfWNhdGNoe319LGRlbChrKXt0cnl7bG9jYWxTdG9yYWdlLnJlbW92ZUl0ZW0oayl9Y2F0Y2h7fX19O1xuXG4gIGNvbnN0IFNUT1JBR0VfS0VZID0gJ3Nicl90b29sc19yZWNlbnRfc2VhcmNoJztcbiAgY29uc3QgTUFYX1JFQ0VOVCA9IDU7XG4gIGNvbnN0ICQgPSAocywgcCkgPT4gKHAgfHwgZG9jdW1lbnQpLnF1ZXJ5U2VsZWN0b3Iocyk7XG4gIGNvbnN0ICQkID0gKHMsIHApID0+IFsuLi4ocCB8fCBkb2N1bWVudCkucXVlcnlTZWxlY3RvckFsbChzKV07XG5cbiAgY29uc3Qgc2VhcmNoSW5wdXQgPSAkKCcjdG9vbFNlYXJjaElucHV0Jyk7XG4gIGNvbnN0IHN1Z2dlc3Rpb25zID0gJCgnI3NlYXJjaFN1Z2dlc3Rpb25zJyk7XG4gIGNvbnN0IHN1Z2dlc3Rpb25IZWFkZXIgPSAkKCcjc3VnZ2VzdGlvbkhlYWRlcicpO1xuICBjb25zdCBza2VsZXRvbkdyaWQgPSAkKCcjc2tlbGV0b25HcmlkJyk7XG4gIGNvbnN0IHRvb2xzR3JpZCA9ICQoJyN0b29sc0dyaWQnKTtcbiAgY29uc3QgZW1wdHlTdGF0ZSA9ICQoJyNlbXB0eVN0YXRlJyk7XG4gIGNvbnN0IGNsZWFyQnRuID0gJCgnI2NsZWFyRmlsdGVyc0J0bicpO1xuICBjb25zdCBjYXRlZ29yeUJ0bnMgPSAkJCgnLmNhdGVnb3J5LWNhcmQnKTtcbiAgY29uc3Qgc2VjdGlvbnMgPSAkJCgnLmNhdGVnb3J5LXNlY3Rpb24nKTtcbiAgY29uc3QgdG9vbENhcmRzID0gKCkgPT4gJCQoJy50b29sLWNhcmQnKTtcblxuICBsZXQgY3VycmVudEZvY3VzSWR4ID0gLTE7XG4gIGxldCBzdWdnZXN0aW9uSXRlbXMgPSBbXTtcblxuICAvKiBcdTI1MDBcdTI1MDAgUmVjZW50IHNlYXJjaGVzIChsb2NhbFN0b3JhZ2UgdmlhIHNhZmUgc3RvcmUgd3JhcHBlcikgXHUyNTAwXHUyNTAwICovXG4gIGZ1bmN0aW9uIGdldFJlY2VudFNlYXJjaGVzKCkge1xuICAgIHRyeSB7IHJldHVybiBKU09OLnBhcnNlKHN0b3JlLmdldChTVE9SQUdFX0tFWSkgfHwgJ1tdJykuc2xpY2UoMCwgTUFYX1JFQ0VOVCk7IH1cbiAgICBjYXRjaCB7IHJldHVybiBbXTsgfVxuICB9XG4gIGZ1bmN0aW9uIGFkZFJlY2VudFNlYXJjaChxKSB7XG4gICAgY29uc3QgcWwgPSBxLnRyaW0oKS50b0xvd2VyQ2FzZSgpO1xuICAgIGlmICghcWwpIHJldHVybjtcbiAgICBsZXQgcmVjZW50cyA9IGdldFJlY2VudFNlYXJjaGVzKCkuZmlsdGVyKHIgPT4gciAhPT0gcWwpO1xuICAgIHJlY2VudHMudW5zaGlmdChxbCk7XG4gICAgaWYgKHJlY2VudHMubGVuZ3RoID4gTUFYX1JFQ0VOVCkgcmVjZW50cyA9IHJlY2VudHMuc2xpY2UoMCwgTUFYX1JFQ0VOVCk7XG4gICAgc3RvcmUuc2V0KFNUT1JBR0VfS0VZLCBKU09OLnN0cmluZ2lmeShyZWNlbnRzKSk7XG4gIH1cbiAgZnVuY3Rpb24gY2xlYXJSZWNlbnRTZWFyY2hlcygpIHtcbiAgICBzdG9yZS5kZWwoU1RPUkFHRV9LRVkpO1xuICAgIHJlbmRlclN1Z2dlc3Rpb25zKHNlYXJjaElucHV0ID8gc2VhcmNoSW5wdXQudmFsdWUudHJpbSgpLnRvTG93ZXJDYXNlKCkgOiAnJyk7XG4gIH1cblxuICAvKiBcdTI1MDBcdTI1MDAgQWxsIHRvb2wgbmFtZXMgZm9yIHN1Z2dlc3Rpb25zIFx1MjUwMFx1MjUwMCAqL1xuICBmdW5jdGlvbiBnZXRBbGxUb29sTmFtZXMoKSB7XG4gICAgcmV0dXJuIHRvb2xDYXJkcygpLm1hcChjID0+IHtcbiAgICAgIGNvbnN0IG5hbWVFbCA9IGMucXVlcnlTZWxlY3RvcignLnRvb2wtY2FyZC1uYW1lJyk7XG4gICAgICByZXR1cm4gbmFtZUVsID8gbmFtZUVsLnRleHRDb250ZW50LnRyaW0oKSA6ICcnO1xuICAgIH0pLmZpbHRlcihCb29sZWFuKTtcbiAgfVxuXG4gIC8qIFx1MjUwMFx1MjUwMCBSZW5kZXIgc3VnZ2VzdGlvbnMgZHJvcGRvd24gXHUyNTAwXHUyNTAwICovXG4gIGZ1bmN0aW9uIHJlbmRlclN1Z2dlc3Rpb25zKHF1ZXJ5KSB7XG4gICAgaWYgKCFzdWdnZXN0aW9ucyB8fCAhc2VhcmNoSW5wdXQpIHJldHVybjtcbiAgICBjb25zdCBxID0gKHF1ZXJ5IHx8ICcnKS50cmltKCkudG9Mb3dlckNhc2UoKTtcbiAgICBjb25zdCByZWNlbnQgPSBnZXRSZWNlbnRTZWFyY2hlcygpO1xuICAgIGxldCBpdGVtcyA9IFtdO1xuXG4gICAgaWYgKHEubGVuZ3RoID4gMCkge1xuICAgICAgY29uc3QgYWxsTmFtZXMgPSBnZXRBbGxUb29sTmFtZXMoKTtcbiAgICAgIGNvbnN0IG1hdGNoZXMgPSBhbGxOYW1lcy5maWx0ZXIobiA9PiBuLnRvTG93ZXJDYXNlKCkuaW5jbHVkZXMocSkpLnNsaWNlKDAsIDgpO1xuICAgICAgaXRlbXMgPSBtYXRjaGVzLm1hcChuID0+ICh7IGxhYmVsOiBuLCB0eXBlOiAnbWF0Y2gnIH0pKTtcbiAgICAgIGlmIChpdGVtcy5sZW5ndGggPT09IDApIHtcbiAgICAgICAgaXRlbXMgPSBbeyBsYWJlbDogJ05vIG1hdGNoaW5nIHRvb2xzJywgdHlwZTogJ2VtcHR5JyB9XTtcbiAgICAgIH1cbiAgICB9IGVsc2Uge1xuICAgICAgaWYgKHJlY2VudC5sZW5ndGggPiAwKSB7XG4gICAgICAgIGl0ZW1zID0gcmVjZW50Lm1hcChyID0+ICh7IGxhYmVsOiByLCB0eXBlOiAncmVjZW50JyB9KSk7XG4gICAgICAgIGl0ZW1zLnB1c2goeyBsYWJlbDogJ0NsZWFyIHJlY2VudCBzZWFyY2hlcycsIHR5cGU6ICdjbGVhcicgfSk7XG4gICAgICB9IGVsc2Uge1xuICAgICAgICBjb25zdCBwb3B1bGFyID0gZ2V0QWxsVG9vbE5hbWVzKCkuc2xpY2UoMCwgNik7XG4gICAgICAgIGl0ZW1zID0gcG9wdWxhci5tYXAobiA9PiAoeyBsYWJlbDogbiwgdHlwZTogJ3BvcHVsYXInIH0pKTtcbiAgICAgIH1cbiAgICB9XG5cbiAgICBzdWdnZXN0aW9uSXRlbXMgPSBpdGVtcztcbiAgICBjdXJyZW50Rm9jdXNJZHggPSAtMTtcbiAgICBidWlsZFN1Z2dlc3Rpb25MaXN0KGl0ZW1zKTtcbiAgICBzZWFyY2hJbnB1dC5zZXRBdHRyaWJ1dGUoJ2FyaWEtZXhwYW5kZWQnLCBpdGVtcy5sZW5ndGggPiAwICYmIGl0ZW1zWzBdLnR5cGUgIT09ICdlbXB0eScgPyAndHJ1ZScgOiAnZmFsc2UnKTtcbiAgfVxuXG4gIGZ1bmN0aW9uIGJ1aWxkU3VnZ2VzdGlvbkxpc3QoaXRlbXMpIHtcbiAgICBpZiAoIXN1Z2dlc3Rpb25zIHx8ICFzdWdnZXN0aW9uSGVhZGVyKSByZXR1cm47XG4gICAgc3VnZ2VzdGlvbnMuaW5uZXJIVE1MID0gJyc7XG4gICAgaWYgKHNlYXJjaElucHV0KSBzZWFyY2hJbnB1dC5yZW1vdmVBdHRyaWJ1dGUoJ2FyaWEtYWN0aXZlZGVzY2VuZGFudCcpO1xuICAgIGlmIChpdGVtcy5sZW5ndGggPT09IDAgfHwgKGl0ZW1zLmxlbmd0aCA9PT0gMSAmJiBpdGVtc1swXS50eXBlID09PSAnZW1wdHknKSkge1xuICAgICAgc3VnZ2VzdGlvbnMuY2xhc3NMaXN0LnJlbW92ZSgnb3BlbicpO1xuICAgICAgc2VhcmNoSW5wdXQgJiYgc2VhcmNoSW5wdXQuc2V0QXR0cmlidXRlKCdhcmlhLWV4cGFuZGVkJywgJ2ZhbHNlJyk7XG4gICAgICByZXR1cm47XG4gICAgfVxuICAgIHN1Z2dlc3Rpb25zLmNsYXNzTGlzdC5hZGQoJ29wZW4nKTtcblxuICAgIGNvbnN0IGZpcnN0VHlwZSA9IGl0ZW1zWzBdLnR5cGU7XG4gICAgY29uc3QgaGVhZGVyQ2xvbmUgPSBzdWdnZXN0aW9uSGVhZGVyLmNsb25lTm9kZSh0cnVlKTtcbiAgICBoZWFkZXJDbG9uZS5yZW1vdmVBdHRyaWJ1dGUoJ2lkJyk7XG4gICAgaWYgKGZpcnN0VHlwZSA9PT0gJ3JlY2VudCcpIGhlYWRlckNsb25lLnRleHRDb250ZW50ID0gJ1JlY2VudCBTZWFyY2hlcyc7XG4gICAgZWxzZSBpZiAoZmlyc3RUeXBlID09PSAnbWF0Y2gnKSBoZWFkZXJDbG9uZS50ZXh0Q29udGVudCA9ICdNYXRjaGluZyBUb29scyc7XG4gICAgZWxzZSBoZWFkZXJDbG9uZS50ZXh0Q29udGVudCA9ICdQb3B1bGFyIFRvb2xzJztcbiAgICBzdWdnZXN0aW9ucy5hcHBlbmRDaGlsZChoZWFkZXJDbG9uZSk7XG5cbiAgICBpdGVtcy5mb3JFYWNoKChpdGVtLCBpKSA9PiB7XG4gICAgICBjb25zdCBkaXYgPSBkb2N1bWVudC5jcmVhdGVFbGVtZW50KCdkaXYnKTtcbiAgICAgIGRpdi5jbGFzc05hbWUgPSAnc2VhcmNoLXN1Z2dlc3Rpb24taXRlbSc7XG4gICAgICBkaXYuc2V0QXR0cmlidXRlKCdyb2xlJywgJ29wdGlvbicpO1xuICAgICAgZGl2LnNldEF0dHJpYnV0ZSgnaWQnLCAnc3VnLScgKyBpKTtcbiAgICAgIGRpdi5zZXRBdHRyaWJ1dGUoJ2FyaWEtc2VsZWN0ZWQnLCAnZmFsc2UnKTtcblxuICAgICAgbGV0IGljb25TdmcgPSAnJztcbiAgICAgIGlmIChpdGVtLnR5cGUgPT09ICdyZWNlbnQnKSBpY29uU3ZnID0gJzxzdmcgY2xhc3M9XCJ3LTMuNSBoLTMuNSBzdWdnZXN0aW9uLWljb25cIiB2aWV3Qm94PVwiMCAwIDI0IDI0XCIgZmlsbD1cIm5vbmVcIiBzdHJva2U9XCJjdXJyZW50Q29sb3JcIiBzdHJva2Utd2lkdGg9XCIyXCI+PGNpcmNsZSBjeD1cIjEyXCIgY3k9XCIxMlwiIHI9XCIxMFwiLz48cG9seWxpbmUgcG9pbnRzPVwiMTIgNiAxMiAxMiAxNiAxNFwiLz48L3N2Zz4nO1xuICAgICAgZWxzZSBpZiAoaXRlbS50eXBlID09PSAnY2xlYXInKSBpY29uU3ZnID0gJzxzdmcgY2xhc3M9XCJ3LTMuNSBoLTMuNSBzdWdnZXN0aW9uLWljb25cIiB2aWV3Qm94PVwiMCAwIDI0IDI0XCIgZmlsbD1cIm5vbmVcIiBzdHJva2U9XCJjdXJyZW50Q29sb3JcIiBzdHJva2Utd2lkdGg9XCIyXCI+PHBhdGggZD1cIk0zIDZoMThcIi8+PHBhdGggZD1cIk0xOSA2djE0YzAgMS0xIDItMiAySDdjLTEgMC0yLTEtMi0yVjZcIi8+PHBhdGggZD1cIk04IDZWNGMwLTEgMS0yIDItMmg0YzEgMCAyIDEgMiAydjJcIi8+PC9zdmc+JztcbiAgICAgIGVsc2UgaWNvblN2ZyA9ICc8c3ZnIGNsYXNzPVwidy0zLjUgaC0zLjUgc3VnZ2VzdGlvbi1pY29uXCIgdmlld0JveD1cIjAgMCAyNCAyNFwiIGZpbGw9XCJub25lXCIgc3Ryb2tlPVwiY3VycmVudENvbG9yXCIgc3Ryb2tlLXdpZHRoPVwiMlwiPjxjaXJjbGUgY3g9XCIxMVwiIGN5PVwiMTFcIiByPVwiOFwiLz48cGF0aCBkPVwibTIxIDIxLTQuMy00LjNcIi8+PC9zdmc+JztcblxuICAgICAgZGl2LmlubmVySFRNTCA9IGljb25TdmcgKyAnPHNwYW4gY2xhc3M9XCJzdWdnZXN0aW9uLWxhYmVsXCI+JyArIGVzY2FwZUh0bWwoaXRlbS5sYWJlbCkgKyAnPC9zcGFuPic7XG4gICAgICBpZiAoaXRlbS50eXBlID09PSAncmVjZW50JyB8fCBpdGVtLnR5cGUgPT09ICdwb3B1bGFyJykge1xuICAgICAgICBjb25zdCBtZXRhID0gZG9jdW1lbnQuY3JlYXRlRWxlbWVudCgnc3BhbicpO1xuICAgICAgICBtZXRhLmNsYXNzTmFtZSA9ICdzdWdnZXN0aW9uLW1ldGEnO1xuICAgICAgICBtZXRhLnRleHRDb250ZW50ID0gaXRlbS50eXBlID09PSAncmVjZW50JyA/ICdSZWNlbnQnIDogJ1BvcHVsYXInO1xuICAgICAgICBkaXYuYXBwZW5kQ2hpbGQobWV0YSk7XG4gICAgICB9XG4gICAgICBkaXYuYWRkRXZlbnRMaXN0ZW5lcignbW91c2Vkb3duJywgZnVuY3Rpb24gKGUpIHtcbiAgICAgICAgZS5wcmV2ZW50RGVmYXVsdCgpO1xuICAgICAgICBzZWxlY3RTdWdnZXN0aW9uKGkpO1xuICAgICAgfSk7XG4gICAgICBkaXYuYWRkRXZlbnRMaXN0ZW5lcignbW91c2VlbnRlcicsIGZ1bmN0aW9uICgpIHtcbiAgICAgICAgc2V0Rm9jdXMoaSk7XG4gICAgICB9KTtcbiAgICAgIHN1Z2dlc3Rpb25zLmFwcGVuZENoaWxkKGRpdik7XG4gICAgfSk7XG4gIH1cblxuICBmdW5jdGlvbiBlc2NhcGVIdG1sKHMpIHtcbiAgICBjb25zdCBkID0gZG9jdW1lbnQuY3JlYXRlRWxlbWVudCgnZGl2Jyk7XG4gICAgZC50ZXh0Q29udGVudCA9IHM7XG4gICAgcmV0dXJuIGQuaW5uZXJIVE1MO1xuICB9XG5cbiAgZnVuY3Rpb24gc2VsZWN0U3VnZ2VzdGlvbihpZHgpIHtcbiAgICBpZiAoaWR4IDwgMCB8fCBpZHggPj0gc3VnZ2VzdGlvbkl0ZW1zLmxlbmd0aCkgcmV0dXJuO1xuICAgIGNvbnN0IGl0ZW0gPSBzdWdnZXN0aW9uSXRlbXNbaWR4XTtcbiAgICBpZiAoaXRlbS50eXBlID09PSAnY2xlYXInKSB7IGNsZWFyUmVjZW50U2VhcmNoZXMoKTsgcmV0dXJuOyB9XG4gICAgaWYgKGl0ZW0udHlwZSA9PT0gJ2VtcHR5JykgcmV0dXJuO1xuICAgIGlmIChzZWFyY2hJbnB1dCkge1xuICAgICAgc2VhcmNoSW5wdXQudmFsdWUgPSBpdGVtLmxhYmVsO1xuICAgICAgYWRkUmVjZW50U2VhcmNoKGl0ZW0ubGFiZWwpO1xuICAgIH1cbiAgICBjbG9zZVN1Z2dlc3Rpb25zKCk7XG4gICAgZmlsdGVyVG9vbHMoKTtcbiAgfVxuXG4gIGZ1bmN0aW9uIHNldEZvY3VzKGlkeCkge1xuICAgICQkKCcuc2VhcmNoLXN1Z2dlc3Rpb24taXRlbScpLmZvckVhY2goKGVsLCBpKSA9PiB7XG4gICAgICBlbC5jbGFzc0xpc3QudG9nZ2xlKCdhY3RpdmUnLCBpID09PSBpZHgpO1xuICAgICAgZWwuc2V0QXR0cmlidXRlKCdhcmlhLXNlbGVjdGVkJywgaSA9PT0gaWR4ID8gJ3RydWUnIDogJ2ZhbHNlJyk7XG4gICAgfSk7XG4gICAgY3VycmVudEZvY3VzSWR4ID0gaWR4O1xuICAgIGlmIChzZWFyY2hJbnB1dCkge1xuICAgICAgaWYgKGlkeCA+PSAwKSBzZWFyY2hJbnB1dC5zZXRBdHRyaWJ1dGUoJ2FyaWEtYWN0aXZlZGVzY2VuZGFudCcsICdzdWctJyArIGlkeCk7XG4gICAgICBlbHNlIHNlYXJjaElucHV0LnJlbW92ZUF0dHJpYnV0ZSgnYXJpYS1hY3RpdmVkZXNjZW5kYW50Jyk7XG4gICAgfVxuICB9XG5cbiAgZnVuY3Rpb24gY2xvc2VTdWdnZXN0aW9ucygpIHtcbiAgICBzdWdnZXN0aW9ucyAmJiBzdWdnZXN0aW9ucy5jbGFzc0xpc3QucmVtb3ZlKCdvcGVuJyk7XG4gICAgc3VnZ2VzdGlvbkl0ZW1zID0gW107XG4gICAgY3VycmVudEZvY3VzSWR4ID0gLTE7XG4gICAgaWYgKHNlYXJjaElucHV0KSB7XG4gICAgICBzZWFyY2hJbnB1dC5zZXRBdHRyaWJ1dGUoJ2FyaWEtZXhwYW5kZWQnLCAnZmFsc2UnKTtcbiAgICAgIHNlYXJjaElucHV0LnJlbW92ZUF0dHJpYnV0ZSgnYXJpYS1hY3RpdmVkZXNjZW5kYW50Jyk7XG4gICAgfVxuICB9XG5cbiAgLyogXHUyNTAwXHUyNTAwIEZpbHRlciB0b29scyBcdTI1MDBcdTI1MDAgKi9cbiAgZnVuY3Rpb24gZmlsdGVyVG9vbHMoKSB7XG4gICAgY29uc3QgcXVlcnkgPSBzZWFyY2hJbnB1dCA/IHNlYXJjaElucHV0LnZhbHVlLnRvTG93ZXJDYXNlKCkudHJpbSgpIDogJyc7XG4gICAgY29uc3QgYWN0aXZlQnRuID0gZG9jdW1lbnQucXVlcnlTZWxlY3RvcignLmNhdGVnb3J5LWNhcmQuYWN0aXZlJyk7XG4gICAgY29uc3QgYWN0aXZlRmlsdGVyID0gYWN0aXZlQnRuID8gYWN0aXZlQnRuLmdldEF0dHJpYnV0ZSgnZGF0YS1maWx0ZXInKSA6ICdhbGwnO1xuICAgIGxldCBhbnlWaXNpYmxlID0gZmFsc2U7XG5cbiAgICBzZWN0aW9ucy5mb3JFYWNoKGZ1bmN0aW9uIChzZWN0aW9uKSB7XG4gICAgICBjb25zdCBjYXQgPSBzZWN0aW9uLmdldEF0dHJpYnV0ZSgnZGF0YS1jYXRlZ29yeScpO1xuICAgICAgY29uc3QgY2F0TWF0Y2ggPSBhY3RpdmVGaWx0ZXIgPT09ICdhbGwnIHx8IGFjdGl2ZUZpbHRlciA9PT0gY2F0O1xuICAgICAgbGV0IGhhc1Zpc2libGUgPSBmYWxzZTtcbiAgICAgIGNvbnN0IGNhcmRzID0gc2VjdGlvbi5xdWVyeVNlbGVjdG9yQWxsKCcudG9vbC1jYXJkJyk7XG5cbiAgICAgIGNhcmRzLmZvckVhY2goZnVuY3Rpb24gKGNhcmQpIHtcbiAgICAgICAgY29uc3QgbmFtZUVsID0gY2FyZC5xdWVyeVNlbGVjdG9yKCcudG9vbC1jYXJkLW5hbWUnKTtcbiAgICAgICAgY29uc3QgZGVzY0VsID0gY2FyZC5xdWVyeVNlbGVjdG9yKCcudG9vbC1jYXJkLWRlc2MnKTtcbiAgICAgICAgY29uc3QgbmFtZSA9IG5hbWVFbCA/IG5hbWVFbC50ZXh0Q29udGVudC50b0xvd2VyQ2FzZSgpIDogJyc7XG4gICAgICAgIGNvbnN0IGRlc2MgPSBkZXNjRWwgPyBkZXNjRWwudGV4dENvbnRlbnQudG9Mb3dlckNhc2UoKSA6ICcnO1xuICAgICAgICBjb25zdCBtYXRjaCA9IG5hbWUuaW5jbHVkZXMocXVlcnkpIHx8IGRlc2MuaW5jbHVkZXMocXVlcnkpO1xuICAgICAgICBjYXJkLnN0eWxlLmRpc3BsYXkgPSBtYXRjaCA/ICcnIDogJ25vbmUnO1xuICAgICAgICBpZiAobWF0Y2gpIGhhc1Zpc2libGUgPSB0cnVlO1xuICAgICAgfSk7XG5cbiAgICAgIGNvbnN0IHNob3cgPSBjYXRNYXRjaCAmJiBoYXNWaXNpYmxlO1xuICAgICAgc2VjdGlvbi5zdHlsZS5kaXNwbGF5ID0gc2hvdyA/ICcnIDogJ25vbmUnO1xuICAgICAgaWYgKHNob3cpIGFueVZpc2libGUgPSB0cnVlO1xuICAgIH0pO1xuXG4gICAgaWYgKGVtcHR5U3RhdGUpIHtcbiAgICAgIGVtcHR5U3RhdGUuY2xhc3NMaXN0LnRvZ2dsZSgnc2hvdycsICFhbnlWaXNpYmxlKTtcbiAgICB9XG4gIH1cblxuICAvKiBcdTI1MDBcdTI1MDAgU2hvdyBza2VsZXRvbiwgaGlkZSBhZnRlciBwYWdlIHJlYWR5IFx1MjUwMFx1MjUwMCAqL1xuICBmdW5jdGlvbiBzaG93U2tlbGV0b24oc2hvdykge1xuICAgIGlmICghc2tlbGV0b25HcmlkIHx8ICF0b29sc0dyaWQpIHJldHVybjtcbiAgICBza2VsZXRvbkdyaWQuY2xhc3NMaXN0LnRvZ2dsZSgnaGlkZGVuJywgIXNob3cpO1xuICAgIHRvb2xzR3JpZC5jbGFzc0xpc3QudG9nZ2xlKCdoaWRkZW4nLCBzaG93KTtcbiAgfVxuXG4gIC8qIFx1MjUwMFx1MjUwMCBFdmVudCBoYW5kbGVycyBcdTI1MDBcdTI1MDAgKi9cbiAgaWYgKHNlYXJjaElucHV0KSB7XG4gICAgc2VhcmNoSW5wdXQuYWRkRXZlbnRMaXN0ZW5lcignaW5wdXQnLCB3aW5kb3cuc2JyLmRlYm91bmNlKGZ1bmN0aW9uICgpIHtcbiAgICAgIGNvbnN0IHEgPSBzZWFyY2hJbnB1dC52YWx1ZS50cmltKCkudG9Mb3dlckNhc2UoKTtcbiAgICAgIGZpbHRlclRvb2xzKCk7XG4gICAgICByZW5kZXJTdWdnZXN0aW9ucyhxKTtcbiAgICB9LCAxNTApKTtcblxuICAgIHNlYXJjaElucHV0LmFkZEV2ZW50TGlzdGVuZXIoJ2ZvY3VzJywgZnVuY3Rpb24gKCkge1xuICAgICAgcmVuZGVyU3VnZ2VzdGlvbnModGhpcy52YWx1ZS50cmltKCkudG9Mb3dlckNhc2UoKSk7XG4gICAgfSk7XG5cbiAgICBzZWFyY2hJbnB1dC5hZGRFdmVudExpc3RlbmVyKCdibHVyJywgZnVuY3Rpb24gKCkge1xuICAgICAgc2V0VGltZW91dChjbG9zZVN1Z2dlc3Rpb25zLCAyMDApO1xuICAgIH0pO1xuXG4gICAgc2VhcmNoSW5wdXQuYWRkRXZlbnRMaXN0ZW5lcigna2V5ZG93bicsIGZ1bmN0aW9uIChlKSB7XG4gICAgICBjb25zdCBpdGVtcyA9ICQkKCcuc2VhcmNoLXN1Z2dlc3Rpb24taXRlbScpO1xuICAgICAgaWYgKGUua2V5ID09PSAnQXJyb3dEb3duJykge1xuICAgICAgICBlLnByZXZlbnREZWZhdWx0KCk7XG4gICAgICAgIGNvbnN0IG5leHQgPSBjdXJyZW50Rm9jdXNJZHggPCBpdGVtcy5sZW5ndGggLSAxID8gY3VycmVudEZvY3VzSWR4ICsgMSA6IDA7XG4gICAgICAgIHNldEZvY3VzKG5leHQpO1xuICAgICAgICBpZiAoaXRlbXNbbmV4dF0pIGl0ZW1zW25leHRdLnNjcm9sbEludG9WaWV3KHsgYmxvY2s6ICduZWFyZXN0JyB9KTtcbiAgICAgIH0gZWxzZSBpZiAoZS5rZXkgPT09ICdBcnJvd1VwJykge1xuICAgICAgICBlLnByZXZlbnREZWZhdWx0KCk7XG4gICAgICAgIGNvbnN0IHByZXYgPSBjdXJyZW50Rm9jdXNJZHggPiAwID8gY3VycmVudEZvY3VzSWR4IC0gMSA6IGl0ZW1zLmxlbmd0aCAtIDE7XG4gICAgICAgIHNldEZvY3VzKHByZXYpO1xuICAgICAgICBpZiAoaXRlbXNbcHJldl0pIGl0ZW1zW3ByZXZdLnNjcm9sbEludG9WaWV3KHsgYmxvY2s6ICduZWFyZXN0JyB9KTtcbiAgICAgIH0gZWxzZSBpZiAoZS5rZXkgPT09ICdFbnRlcicgJiYgY3VycmVudEZvY3VzSWR4ID49IDApIHtcbiAgICAgICAgZS5wcmV2ZW50RGVmYXVsdCgpO1xuICAgICAgICBzZWxlY3RTdWdnZXN0aW9uKGN1cnJlbnRGb2N1c0lkeCk7XG4gICAgICB9IGVsc2UgaWYgKGUua2V5ID09PSAnRXNjYXBlJykge1xuICAgICAgICBjbG9zZVN1Z2dlc3Rpb25zKCk7XG4gICAgICAgIHRoaXMuYmx1cigpO1xuICAgICAgfVxuICAgIH0pO1xuICB9XG5cbiAgZnVuY3Rpb24gX2lzRWRpdGFibGUoZWwpIHtcbiAgICBpZiAoIWVsIHx8ICFlbC50YWdOYW1lKSByZXR1cm4gZmFsc2U7XG4gICAgY29uc3QgdCA9IGVsLnRhZ05hbWUudG9Mb3dlckNhc2UoKTtcbiAgICByZXR1cm4gdCA9PT0gJ2lucHV0JyB8fCB0ID09PSAndGV4dGFyZWEnIHx8IHQgPT09ICdzZWxlY3QnIHx8IGVsLmlzQ29udGVudEVkaXRhYmxlID09PSB0cnVlO1xuICB9XG5cbiAgZG9jdW1lbnQuYWRkRXZlbnRMaXN0ZW5lcigna2V5ZG93bicsIGZ1bmN0aW9uIChlKSB7XG4gICAgaWYgKGUua2V5ICE9PSAnLycgfHwgZS5jdHJsS2V5IHx8IGUubWV0YUtleSB8fCBlLmFsdEtleSkgcmV0dXJuO1xuICAgIC8vIE5ldmVyIHN0ZWFsICcvJyB3aGlsZSB0aGUgZ2xvYmFsIHNlYXJjaCBkaWFsb2cgaXMgb3BlbiAoYXBwLmpzIG93bnMgaXQgdGhlcmUpLFxuICAgIC8vIG9yIHdoaWxlIHR5cGluZyBpbiBhbnkgZWRpdGFibGUgZmllbGQgKGluY2wuIGhlcm9TZWFyY2hJbnB1dCkuXG4gICAgY29uc3QgZGlhID0gZG9jdW1lbnQuZ2V0RWxlbWVudEJ5SWQoJ3NlYXJjaERpYWxvZycpO1xuICAgIGlmIChkaWEgJiYgZGlhLm9wZW4pIHJldHVybjtcbiAgICBpZiAoX2lzRWRpdGFibGUoZG9jdW1lbnQuYWN0aXZlRWxlbWVudCkpIHJldHVybjtcbiAgICBpZiAoIXNlYXJjaElucHV0KSByZXR1cm47XG4gICAgZS5wcmV2ZW50RGVmYXVsdCgpO1xuICAgIHNlYXJjaElucHV0LmZvY3VzKCk7XG4gICAgLy8gTWFrZSB0aGUgdGFyZ2V0IHZpc2libGUgYmVmb3JlIGZvY3VzaW5nIG9uIHNtYWxsIHNjcmVlbnMuXG4gICAgdHJ5IHsgc2VhcmNoSW5wdXQuc2Nyb2xsSW50b1ZpZXcoeyBibG9jazogJ25lYXJlc3QnLCBiZWhhdmlvcjogJ3Ntb290aCcgfSk7IH0gY2F0Y2gge31cbiAgfSk7XG5cbiAgLyogQ2F0ZWdvcnkgY2FyZHMgXHUyMDE0IGNsaWNrICsgQXJyb3dMZWZ0L1JpZ2h0IHJvdmluZyBmb3IgdGFibGlzdCBwYXR0ZXJuICovXG4gIGlmIChjYXRlZ29yeUJ0bnMubGVuZ3RoKSB7XG4gICAgY2F0ZWdvcnlCdG5zLmZvckVhY2goZnVuY3Rpb24gKGJ0biwgaWR4KSB7XG4gICAgICBidG4uYWRkRXZlbnRMaXN0ZW5lcignY2xpY2snLCBmdW5jdGlvbiAoKSB7XG4gICAgICAgIGNhdGVnb3J5QnRucy5mb3JFYWNoKGZ1bmN0aW9uIChiKSB7XG4gICAgICAgICAgYi5jbGFzc0xpc3QucmVtb3ZlKCdhY3RpdmUnKTtcbiAgICAgICAgICBiLnNldEF0dHJpYnV0ZSgnYXJpYS1zZWxlY3RlZCcsICdmYWxzZScpO1xuICAgICAgICAgIGIuc2V0QXR0cmlidXRlKCd0YWJpbmRleCcsICctMScpO1xuICAgICAgICB9KTtcbiAgICAgICAgdGhpcy5jbGFzc0xpc3QuYWRkKCdhY3RpdmUnKTtcbiAgICAgICAgdGhpcy5zZXRBdHRyaWJ1dGUoJ2FyaWEtc2VsZWN0ZWQnLCAndHJ1ZScpO1xuICAgICAgICB0aGlzLnJlbW92ZUF0dHJpYnV0ZSgndGFiaW5kZXgnKTtcbiAgICAgICAgY2xvc2VTdWdnZXN0aW9ucygpO1xuICAgICAgICBmaWx0ZXJUb29scygpO1xuICAgICAgfSk7XG4gICAgICBidG4uYWRkRXZlbnRMaXN0ZW5lcigna2V5ZG93bicsIGZ1bmN0aW9uIChlKSB7XG4gICAgICAgIGlmIChlLmtleSAhPT0gJ0Fycm93UmlnaHQnICYmIGUua2V5ICE9PSAnQXJyb3dMZWZ0JyAmJiBlLmtleSAhPT0gJ0hvbWUnICYmIGUua2V5ICE9PSAnRW5kJykgcmV0dXJuO1xuICAgICAgICBlLnByZXZlbnREZWZhdWx0KCk7XG4gICAgICAgIGxldCBuZXh0ID0gaWR4O1xuICAgICAgICBpZiAoZS5rZXkgPT09ICdBcnJvd1JpZ2h0JykgbmV4dCA9IChpZHggKyAxKSAlIGNhdGVnb3J5QnRucy5sZW5ndGg7XG4gICAgICAgIGVsc2UgaWYgKGUua2V5ID09PSAnQXJyb3dMZWZ0JykgbmV4dCA9IChpZHggLSAxICsgY2F0ZWdvcnlCdG5zLmxlbmd0aCkgJSBjYXRlZ29yeUJ0bnMubGVuZ3RoO1xuICAgICAgICBlbHNlIGlmIChlLmtleSA9PT0gJ0hvbWUnKSBuZXh0ID0gMDtcbiAgICAgICAgZWxzZSBpZiAoZS5rZXkgPT09ICdFbmQnKSBuZXh0ID0gY2F0ZWdvcnlCdG5zLmxlbmd0aCAtIDE7XG4gICAgICAgIGNhdGVnb3J5QnRuc1tuZXh0XS5mb2N1cygpO1xuICAgICAgICBjYXRlZ29yeUJ0bnNbbmV4dF0uY2xpY2soKTtcbiAgICAgIH0pO1xuICAgICAgaWYgKCFidG4uY2xhc3NMaXN0LmNvbnRhaW5zKCdhY3RpdmUnKSkgYnRuLnNldEF0dHJpYnV0ZSgndGFiaW5kZXgnLCAnLTEnKTtcbiAgICB9KTtcbiAgfVxuXG4gIC8qIENsZWFyIGZpbHRlcnMgYnV0dG9uICovXG4gIGlmIChjbGVhckJ0bikge1xuICAgIGNsZWFyQnRuLmFkZEV2ZW50TGlzdGVuZXIoJ2NsaWNrJywgZnVuY3Rpb24gKCkge1xuICAgICAgY29uc3QgYWxsQnRuID0gZG9jdW1lbnQucXVlcnlTZWxlY3RvcignLmNhdGVnb3J5LWNhcmRbZGF0YS1maWx0ZXI9XCJhbGxcIl0nKTtcbiAgICAgIGlmIChhbGxCdG4pIHtcbiAgICAgICAgY2F0ZWdvcnlCdG5zLmZvckVhY2goZnVuY3Rpb24gKGIpIHtcbiAgICAgICAgICBiLmNsYXNzTGlzdC5yZW1vdmUoJ2FjdGl2ZScpO1xuICAgICAgICAgIGIuc2V0QXR0cmlidXRlKCdhcmlhLXNlbGVjdGVkJywgJ2ZhbHNlJyk7XG4gICAgICAgICAgYi5zZXRBdHRyaWJ1dGUoJ3RhYmluZGV4JywgJy0xJyk7XG4gICAgICAgIH0pO1xuICAgICAgICBhbGxCdG4uY2xhc3NMaXN0LmFkZCgnYWN0aXZlJyk7XG4gICAgICAgIGFsbEJ0bi5zZXRBdHRyaWJ1dGUoJ2FyaWEtc2VsZWN0ZWQnLCAndHJ1ZScpO1xuICAgICAgICBhbGxCdG4ucmVtb3ZlQXR0cmlidXRlKCd0YWJpbmRleCcpO1xuICAgICAgfVxuICAgICAgaWYgKHNlYXJjaElucHV0KSBzZWFyY2hJbnB1dC52YWx1ZSA9ICcnO1xuICAgICAgZmlsdGVyVG9vbHMoKTtcbiAgICAgIGlmIChzZWFyY2hJbnB1dCkgc2VhcmNoSW5wdXQuZm9jdXMoKTtcbiAgICB9KTtcbiAgfVxuXG4gIC8qIFx1MjUwMFx1MjUwMCBJbml0OiBncmlkIGlzIHNlcnZlci1yZW5kZXJlZCAoTENQIGNvbnRlbnQpIFx1MjAxNCBzaG93IGl0IGltbWVkaWF0ZWx5LFxuICAgICBkb24ndCBoaWRlIGl0IGJlaGluZCBhIHNrZWxldG9uIGZsYXNoLiBcdTI1MDBcdTI1MDAgKi9cbiAgZnVuY3Rpb24gaW5pdCgpIHtcbiAgICBzaG93U2tlbGV0b24oZmFsc2UpO1xuICAgIGZpbHRlclRvb2xzKCk7XG4gIH1cblxuICBpZiAoZG9jdW1lbnQucmVhZHlTdGF0ZSA9PT0gJ2xvYWRpbmcnKSB7XG4gICAgZG9jdW1lbnQuYWRkRXZlbnRMaXN0ZW5lcignRE9NQ29udGVudExvYWRlZCcsIGluaXQpO1xuICB9IGVsc2Uge1xuICAgIGluaXQoKTtcbiAgfVxufSkoKTtcbiJdLAogICJtYXBwaW5ncyI6ICI7O0FBQUEsR0FBQyxXQUFZO0FBQ1g7QUFHQSxVQUFNLFFBQU0sRUFBQyxJQUFJLEdBQUU7QUFBQyxVQUFHO0FBQUMsZUFBTyxhQUFhLFFBQVEsQ0FBQztBQUFBLE1BQUMsUUFBTTtBQUFDLGVBQU87QUFBQSxNQUFJO0FBQUEsSUFBQyxHQUFFLElBQUks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
