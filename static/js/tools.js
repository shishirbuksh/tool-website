(() => {
  // src/js/tools.js
  (function() {
    "use strict";
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
        return JSON.parse(localStorage.getItem(STORAGE_KEY) || "[]").slice(0, MAX_RECENT);
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
      try {
        localStorage.setItem(STORAGE_KEY, JSON.stringify(recents));
      } catch {
      }
    }
    function clearRecentSearches() {
      try {
        localStorage.removeItem(STORAGE_KEY);
      } catch {
      }
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
      if (items.length === 0 || items.length === 1 && items[0].type === "empty") {
        suggestions.classList.remove("open");
        searchInput && searchInput.setAttribute("aria-expanded", "false");
        return;
      }
      suggestions.classList.add("open");
      const firstType = items[0].type;
      if (firstType === "recent") suggestionHeader.textContent = "Recent Searches";
      else if (firstType === "match") suggestionHeader.textContent = "Matching Tools";
      else suggestionHeader.textContent = "Popular Tools";
      suggestions.appendChild(suggestionHeader.cloneNode(true));
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
    }
    function closeSuggestions() {
      suggestions && suggestions.classList.remove("open");
      suggestionItems = [];
      currentFocusIdx = -1;
      searchInput && searchInput.setAttribute("aria-expanded", "false");
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
        } else if (e.key === "ArrowUp") {
          e.preventDefault();
          const prev = currentFocusIdx > 0 ? currentFocusIdx - 1 : items.length - 1;
          setFocus(prev);
        } else if (e.key === "Enter" && currentFocusIdx >= 0) {
          e.preventDefault();
          selectSuggestion(currentFocusIdx);
        } else if (e.key === "Escape") {
          closeSuggestions();
          this.blur();
        } else if (e.key === "/" && document.activeElement !== searchInput) {
          e.preventDefault();
          searchInput.focus();
        }
      });
    }
    document.addEventListener("keydown", function(e) {
      if (e.key === "/" && document.activeElement !== searchInput && document.activeElement !== document.body) return;
      if (e.key === "/" && document.activeElement !== searchInput) {
        e.preventDefault();
        if (searchInput) searchInput.focus();
      }
    });
    if (categoryBtns.length) {
      categoryBtns.forEach(function(btn) {
        btn.addEventListener("click", function() {
          categoryBtns.forEach(function(b) {
            b.classList.remove("active");
            b.setAttribute("aria-selected", "false");
          });
          this.classList.add("active");
          this.setAttribute("aria-selected", "true");
          closeSuggestions();
          filterTools();
        });
      });
    }
    if (clearBtn) {
      clearBtn.addEventListener("click", function() {
        const allBtn = document.querySelector('.category-card[data-filter="all"]');
        if (allBtn) {
          categoryBtns.forEach(function(b) {
            b.classList.remove("active");
            b.setAttribute("aria-selected", "false");
          });
          allBtn.classList.add("active");
          allBtn.setAttribute("aria-selected", "true");
        }
        if (searchInput) searchInput.value = "";
        filterTools();
        if (searchInput) searchInput.focus();
      });
    }
    function init() {
      showSkeleton(true);
      requestAnimationFrame(function() {
        setTimeout(function() {
          showSkeleton(false);
          filterTools();
        }, 400);
      });
    }
    if (document.readyState === "loading") {
      document.addEventListener("DOMContentLoaded", init);
    } else {
      init();
    }
  })();
})();
//# sourceMappingURL=data:application/json;base64,ewogICJ2ZXJzaW9uIjogMywKICAic291cmNlcyI6IFsiLi4vLi4vc3JjL2pzL3Rvb2xzLmpzIl0sCiAgInNvdXJjZXNDb250ZW50IjogWyIoZnVuY3Rpb24gKCkge1xuICAndXNlIHN0cmljdCc7XG5cbiAgY29uc3QgU1RPUkFHRV9LRVkgPSAnc2JyX3Rvb2xzX3JlY2VudF9zZWFyY2gnO1xuICBjb25zdCBNQVhfUkVDRU5UID0gNTtcbiAgY29uc3QgJCA9IChzLCBwKSA9PiAocCB8fCBkb2N1bWVudCkucXVlcnlTZWxlY3RvcihzKTtcbiAgY29uc3QgJCQgPSAocywgcCkgPT4gWy4uLihwIHx8IGRvY3VtZW50KS5xdWVyeVNlbGVjdG9yQWxsKHMpXTtcblxuICBjb25zdCBzZWFyY2hJbnB1dCA9ICQoJyN0b29sU2VhcmNoSW5wdXQnKTtcbiAgY29uc3Qgc3VnZ2VzdGlvbnMgPSAkKCcjc2VhcmNoU3VnZ2VzdGlvbnMnKTtcbiAgY29uc3Qgc3VnZ2VzdGlvbkhlYWRlciA9ICQoJyNzdWdnZXN0aW9uSGVhZGVyJyk7XG4gIGNvbnN0IHNrZWxldG9uR3JpZCA9ICQoJyNza2VsZXRvbkdyaWQnKTtcbiAgY29uc3QgdG9vbHNHcmlkID0gJCgnI3Rvb2xzR3JpZCcpO1xuICBjb25zdCBlbXB0eVN0YXRlID0gJCgnI2VtcHR5U3RhdGUnKTtcbiAgY29uc3QgY2xlYXJCdG4gPSAkKCcjY2xlYXJGaWx0ZXJzQnRuJyk7XG4gIGNvbnN0IGNhdGVnb3J5QnRucyA9ICQkKCcuY2F0ZWdvcnktY2FyZCcpO1xuICBjb25zdCBzZWN0aW9ucyA9ICQkKCcuY2F0ZWdvcnktc2VjdGlvbicpO1xuICBjb25zdCB0b29sQ2FyZHMgPSAoKSA9PiAkJCgnLnRvb2wtY2FyZCcpO1xuXG4gIGxldCBjdXJyZW50Rm9jdXNJZHggPSAtMTtcbiAgbGV0IHN1Z2dlc3Rpb25JdGVtcyA9IFtdO1xuXG4gIC8qIFx1MjUwMFx1MjUwMCBSZWNlbnQgc2VhcmNoZXMgKGxvY2FsU3RvcmFnZSkgXHUyNTAwXHUyNTAwICovXG4gIGZ1bmN0aW9uIGdldFJlY2VudFNlYXJjaGVzKCkge1xuICAgIHRyeSB7IHJldHVybiBKU09OLnBhcnNlKGxvY2FsU3RvcmFnZS5nZXRJdGVtKFNUT1JBR0VfS0VZKSB8fCAnW10nKS5zbGljZSgwLCBNQVhfUkVDRU5UKTsgfVxuICAgIGNhdGNoIHsgcmV0dXJuIFtdOyB9XG4gIH1cbiAgZnVuY3Rpb24gYWRkUmVjZW50U2VhcmNoKHEpIHtcbiAgICBjb25zdCBxbCA9IHEudHJpbSgpLnRvTG93ZXJDYXNlKCk7XG4gICAgaWYgKCFxbCkgcmV0dXJuO1xuICAgIGxldCByZWNlbnRzID0gZ2V0UmVjZW50U2VhcmNoZXMoKS5maWx0ZXIociA9PiByICE9PSBxbCk7XG4gICAgcmVjZW50cy51bnNoaWZ0KHFsKTtcbiAgICBpZiAocmVjZW50cy5sZW5ndGggPiBNQVhfUkVDRU5UKSByZWNlbnRzID0gcmVjZW50cy5zbGljZSgwLCBNQVhfUkVDRU5UKTtcbiAgICB0cnkgeyBsb2NhbFN0b3JhZ2Uuc2V0SXRlbShTVE9SQUdFX0tFWSwgSlNPTi5zdHJpbmdpZnkocmVjZW50cykpOyB9IGNhdGNoIHt9XG4gIH1cbiAgZnVuY3Rpb24gY2xlYXJSZWNlbnRTZWFyY2hlcygpIHtcbiAgICB0cnkgeyBsb2NhbFN0b3JhZ2UucmVtb3ZlSXRlbShTVE9SQUdFX0tFWSk7IH0gY2F0Y2gge31cbiAgICByZW5kZXJTdWdnZXN0aW9ucyhzZWFyY2hJbnB1dCA/IHNlYXJjaElucHV0LnZhbHVlLnRyaW0oKS50b0xvd2VyQ2FzZSgpIDogJycpO1xuICB9XG5cbiAgLyogXHUyNTAwXHUyNTAwIEFsbCB0b29sIG5hbWVzIGZvciBzdWdnZXN0aW9ucyBcdTI1MDBcdTI1MDAgKi9cbiAgZnVuY3Rpb24gZ2V0QWxsVG9vbE5hbWVzKCkge1xuICAgIHJldHVybiB0b29sQ2FyZHMoKS5tYXAoYyA9PiB7XG4gICAgICBjb25zdCBuYW1lRWwgPSBjLnF1ZXJ5U2VsZWN0b3IoJy50b29sLWNhcmQtbmFtZScpO1xuICAgICAgcmV0dXJuIG5hbWVFbCA/IG5hbWVFbC50ZXh0Q29udGVudC50cmltKCkgOiAnJztcbiAgICB9KS5maWx0ZXIoQm9vbGVhbik7XG4gIH1cblxuICAvKiBcdTI1MDBcdTI1MDAgUmVuZGVyIHN1Z2dlc3Rpb25zIGRyb3Bkb3duIFx1MjUwMFx1MjUwMCAqL1xuICBmdW5jdGlvbiByZW5kZXJTdWdnZXN0aW9ucyhxdWVyeSkge1xuICAgIGlmICghc3VnZ2VzdGlvbnMgfHwgIXNlYXJjaElucHV0KSByZXR1cm47XG4gICAgY29uc3QgcSA9IChxdWVyeSB8fCAnJykudHJpbSgpLnRvTG93ZXJDYXNlKCk7XG4gICAgY29uc3QgcmVjZW50ID0gZ2V0UmVjZW50U2VhcmNoZXMoKTtcbiAgICBsZXQgaXRlbXMgPSBbXTtcblxuICAgIGlmIChxLmxlbmd0aCA+IDApIHtcbiAgICAgIGNvbnN0IGFsbE5hbWVzID0gZ2V0QWxsVG9vbE5hbWVzKCk7XG4gICAgICBjb25zdCBtYXRjaGVzID0gYWxsTmFtZXMuZmlsdGVyKG4gPT4gbi50b0xvd2VyQ2FzZSgpLmluY2x1ZGVzKHEpKS5zbGljZSgwLCA4KTtcbiAgICAgIGl0ZW1zID0gbWF0Y2hlcy5tYXAobiA9PiAoeyBsYWJlbDogbiwgdHlwZTogJ21hdGNoJyB9KSk7XG4gICAgICBpZiAoaXRlbXMubGVuZ3RoID09PSAwKSB7XG4gICAgICAgIGl0ZW1zID0gW3sgbGFiZWw6ICdObyBtYXRjaGluZyB0b29scycsIHR5cGU6ICdlbXB0eScgfV07XG4gICAgICB9XG4gICAgfSBlbHNlIHtcbiAgICAgIGlmIChyZWNlbnQubGVuZ3RoID4gMCkge1xuICAgICAgICBpdGVtcyA9IHJlY2VudC5tYXAociA9PiAoeyBsYWJlbDogciwgdHlwZTogJ3JlY2VudCcgfSkpO1xuICAgICAgICBpdGVtcy5wdXNoKHsgbGFiZWw6ICdDbGVhciByZWNlbnQgc2VhcmNoZXMnLCB0eXBlOiAnY2xlYXInIH0pO1xuICAgICAgfSBlbHNlIHtcbiAgICAgICAgY29uc3QgcG9wdWxhciA9IGdldEFsbFRvb2xOYW1lcygpLnNsaWNlKDAsIDYpO1xuICAgICAgICBpdGVtcyA9IHBvcHVsYXIubWFwKG4gPT4gKHsgbGFiZWw6IG4sIHR5cGU6ICdwb3B1bGFyJyB9KSk7XG4gICAgICB9XG4gICAgfVxuXG4gICAgc3VnZ2VzdGlvbkl0ZW1zID0gaXRlbXM7XG4gICAgY3VycmVudEZvY3VzSWR4ID0gLTE7XG4gICAgYnVpbGRTdWdnZXN0aW9uTGlzdChpdGVtcyk7XG4gICAgc2VhcmNoSW5wdXQuc2V0QXR0cmlidXRlKCdhcmlhLWV4cGFuZGVkJywgaXRlbXMubGVuZ3RoID4gMCAmJiBpdGVtc1swXS50eXBlICE9PSAnZW1wdHknID8gJ3RydWUnIDogJ2ZhbHNlJyk7XG4gIH1cblxuICBmdW5jdGlvbiBidWlsZFN1Z2dlc3Rpb25MaXN0KGl0ZW1zKSB7XG4gICAgaWYgKCFzdWdnZXN0aW9ucyB8fCAhc3VnZ2VzdGlvbkhlYWRlcikgcmV0dXJuO1xuICAgIHN1Z2dlc3Rpb25zLmlubmVySFRNTCA9ICcnO1xuICAgIGlmIChpdGVtcy5sZW5ndGggPT09IDAgfHwgKGl0ZW1zLmxlbmd0aCA9PT0gMSAmJiBpdGVtc1swXS50eXBlID09PSAnZW1wdHknKSkge1xuICAgICAgc3VnZ2VzdGlvbnMuY2xhc3NMaXN0LnJlbW92ZSgnb3BlbicpO1xuICAgICAgc2VhcmNoSW5wdXQgJiYgc2VhcmNoSW5wdXQuc2V0QXR0cmlidXRlKCdhcmlhLWV4cGFuZGVkJywgJ2ZhbHNlJyk7XG4gICAgICByZXR1cm47XG4gICAgfVxuICAgIHN1Z2dlc3Rpb25zLmNsYXNzTGlzdC5hZGQoJ29wZW4nKTtcblxuICAgIGNvbnN0IGZpcnN0VHlwZSA9IGl0ZW1zWzBdLnR5cGU7XG4gICAgaWYgKGZpcnN0VHlwZSA9PT0gJ3JlY2VudCcpIHN1Z2dlc3Rpb25IZWFkZXIudGV4dENvbnRlbnQgPSAnUmVjZW50IFNlYXJjaGVzJztcbiAgICBlbHNlIGlmIChmaXJzdFR5cGUgPT09ICdtYXRjaCcpIHN1Z2dlc3Rpb25IZWFkZXIudGV4dENvbnRlbnQgPSAnTWF0Y2hpbmcgVG9vbHMnO1xuICAgIGVsc2Ugc3VnZ2VzdGlvbkhlYWRlci50ZXh0Q29udGVudCA9ICdQb3B1bGFyIFRvb2xzJztcbiAgICBzdWdnZXN0aW9ucy5hcHBlbmRDaGlsZChzdWdnZXN0aW9uSGVhZGVyLmNsb25lTm9kZSh0cnVlKSk7XG5cbiAgICBpdGVtcy5mb3JFYWNoKChpdGVtLCBpKSA9PiB7XG4gICAgICBjb25zdCBkaXYgPSBkb2N1bWVudC5jcmVhdGVFbGVtZW50KCdkaXYnKTtcbiAgICAgIGRpdi5jbGFzc05hbWUgPSAnc2VhcmNoLXN1Z2dlc3Rpb24taXRlbSc7XG4gICAgICBkaXYuc2V0QXR0cmlidXRlKCdyb2xlJywgJ29wdGlvbicpO1xuICAgICAgZGl2LnNldEF0dHJpYnV0ZSgnaWQnLCAnc3VnLScgKyBpKTtcbiAgICAgIGRpdi5zZXRBdHRyaWJ1dGUoJ2FyaWEtc2VsZWN0ZWQnLCAnZmFsc2UnKTtcblxuICAgICAgbGV0IGljb25TdmcgPSAnJztcbiAgICAgIGlmIChpdGVtLnR5cGUgPT09ICdyZWNlbnQnKSBpY29uU3ZnID0gJzxzdmcgY2xhc3M9XCJ3LTMuNSBoLTMuNSBzdWdnZXN0aW9uLWljb25cIiB2aWV3Qm94PVwiMCAwIDI0IDI0XCIgZmlsbD1cIm5vbmVcIiBzdHJva2U9XCJjdXJyZW50Q29sb3JcIiBzdHJva2Utd2lkdGg9XCIyXCI+PGNpcmNsZSBjeD1cIjEyXCIgY3k9XCIxMlwiIHI9XCIxMFwiLz48cG9seWxpbmUgcG9pbnRzPVwiMTIgNiAxMiAxMiAxNiAxNFwiLz48L3N2Zz4nO1xuICAgICAgZWxzZSBpZiAoaXRlbS50eXBlID09PSAnY2xlYXInKSBpY29uU3ZnID0gJzxzdmcgY2xhc3M9XCJ3LTMuNSBoLTMuNSBzdWdnZXN0aW9uLWljb25cIiB2aWV3Qm94PVwiMCAwIDI0IDI0XCIgZmlsbD1cIm5vbmVcIiBzdHJva2U9XCJjdXJyZW50Q29sb3JcIiBzdHJva2Utd2lkdGg9XCIyXCI+PHBhdGggZD1cIk0zIDZoMThcIi8+PHBhdGggZD1cIk0xOSA2djE0YzAgMS0xIDItMiAySDdjLTEgMC0yLTEtMi0yVjZcIi8+PHBhdGggZD1cIk04IDZWNGMwLTEgMS0yIDItMmg0YzEgMCAyIDEgMiAydjJcIi8+PC9zdmc+JztcbiAgICAgIGVsc2UgaWNvblN2ZyA9ICc8c3ZnIGNsYXNzPVwidy0zLjUgaC0zLjUgc3VnZ2VzdGlvbi1pY29uXCIgdmlld0JveD1cIjAgMCAyNCAyNFwiIGZpbGw9XCJub25lXCIgc3Ryb2tlPVwiY3VycmVudENvbG9yXCIgc3Ryb2tlLXdpZHRoPVwiMlwiPjxjaXJjbGUgY3g9XCIxMVwiIGN5PVwiMTFcIiByPVwiOFwiLz48cGF0aCBkPVwibTIxIDIxLTQuMy00LjNcIi8+PC9zdmc+JztcblxuICAgICAgZGl2LmlubmVySFRNTCA9IGljb25TdmcgKyAnPHNwYW4gY2xhc3M9XCJzdWdnZXN0aW9uLWxhYmVsXCI+JyArIGVzY2FwZUh0bWwoaXRlbS5sYWJlbCkgKyAnPC9zcGFuPic7XG4gICAgICBpZiAoaXRlbS50eXBlID09PSAncmVjZW50JyB8fCBpdGVtLnR5cGUgPT09ICdwb3B1bGFyJykge1xuICAgICAgICBjb25zdCBtZXRhID0gZG9jdW1lbnQuY3JlYXRlRWxlbWVudCgnc3BhbicpO1xuICAgICAgICBtZXRhLmNsYXNzTmFtZSA9ICdzdWdnZXN0aW9uLW1ldGEnO1xuICAgICAgICBtZXRhLnRleHRDb250ZW50ID0gaXRlbS50eXBlID09PSAncmVjZW50JyA/ICdSZWNlbnQnIDogJ1BvcHVsYXInO1xuICAgICAgICBkaXYuYXBwZW5kQ2hpbGQobWV0YSk7XG4gICAgICB9XG4gICAgICBkaXYuYWRkRXZlbnRMaXN0ZW5lcignbW91c2Vkb3duJywgZnVuY3Rpb24gKGUpIHtcbiAgICAgICAgZS5wcmV2ZW50RGVmYXVsdCgpO1xuICAgICAgICBzZWxlY3RTdWdnZXN0aW9uKGkpO1xuICAgICAgfSk7XG4gICAgICBkaXYuYWRkRXZlbnRMaXN0ZW5lcignbW91c2VlbnRlcicsIGZ1bmN0aW9uICgpIHtcbiAgICAgICAgc2V0Rm9jdXMoaSk7XG4gICAgICB9KTtcbiAgICAgIHN1Z2dlc3Rpb25zLmFwcGVuZENoaWxkKGRpdik7XG4gICAgfSk7XG4gIH1cblxuICBmdW5jdGlvbiBlc2NhcGVIdG1sKHMpIHtcbiAgICBjb25zdCBkID0gZG9jdW1lbnQuY3JlYXRlRWxlbWVudCgnZGl2Jyk7XG4gICAgZC50ZXh0Q29udGVudCA9IHM7XG4gICAgcmV0dXJuIGQuaW5uZXJIVE1MO1xuICB9XG5cbiAgZnVuY3Rpb24gc2VsZWN0U3VnZ2VzdGlvbihpZHgpIHtcbiAgICBpZiAoaWR4IDwgMCB8fCBpZHggPj0gc3VnZ2VzdGlvbkl0ZW1zLmxlbmd0aCkgcmV0dXJuO1xuICAgIGNvbnN0IGl0ZW0gPSBzdWdnZXN0aW9uSXRlbXNbaWR4XTtcbiAgICBpZiAoaXRlbS50eXBlID09PSAnY2xlYXInKSB7IGNsZWFyUmVjZW50U2VhcmNoZXMoKTsgcmV0dXJuOyB9XG4gICAgaWYgKGl0ZW0udHlwZSA9PT0gJ2VtcHR5JykgcmV0dXJuO1xuICAgIGlmIChzZWFyY2hJbnB1dCkge1xuICAgICAgc2VhcmNoSW5wdXQudmFsdWUgPSBpdGVtLmxhYmVsO1xuICAgICAgYWRkUmVjZW50U2VhcmNoKGl0ZW0ubGFiZWwpO1xuICAgIH1cbiAgICBjbG9zZVN1Z2dlc3Rpb25zKCk7XG4gICAgZmlsdGVyVG9vbHMoKTtcbiAgfVxuXG4gIGZ1bmN0aW9uIHNldEZvY3VzKGlkeCkge1xuICAgICQkKCcuc2VhcmNoLXN1Z2dlc3Rpb24taXRlbScpLmZvckVhY2goKGVsLCBpKSA9PiB7XG4gICAgICBlbC5jbGFzc0xpc3QudG9nZ2xlKCdhY3RpdmUnLCBpID09PSBpZHgpO1xuICAgICAgZWwuc2V0QXR0cmlidXRlKCdhcmlhLXNlbGVjdGVkJywgaSA9PT0gaWR4ID8gJ3RydWUnIDogJ2ZhbHNlJyk7XG4gICAgfSk7XG4gICAgY3VycmVudEZvY3VzSWR4ID0gaWR4O1xuICB9XG5cbiAgZnVuY3Rpb24gY2xvc2VTdWdnZXN0aW9ucygpIHtcbiAgICBzdWdnZXN0aW9ucyAmJiBzdWdnZXN0aW9ucy5jbGFzc0xpc3QucmVtb3ZlKCdvcGVuJyk7XG4gICAgc3VnZ2VzdGlvbkl0ZW1zID0gW107XG4gICAgY3VycmVudEZvY3VzSWR4ID0gLTE7XG4gICAgc2VhcmNoSW5wdXQgJiYgc2VhcmNoSW5wdXQuc2V0QXR0cmlidXRlKCdhcmlhLWV4cGFuZGVkJywgJ2ZhbHNlJyk7XG4gIH1cblxuICAvKiBcdTI1MDBcdTI1MDAgRmlsdGVyIHRvb2xzIFx1MjUwMFx1MjUwMCAqL1xuICBmdW5jdGlvbiBmaWx0ZXJUb29scygpIHtcbiAgICBjb25zdCBxdWVyeSA9IHNlYXJjaElucHV0ID8gc2VhcmNoSW5wdXQudmFsdWUudG9Mb3dlckNhc2UoKS50cmltKCkgOiAnJztcbiAgICBjb25zdCBhY3RpdmVCdG4gPSBkb2N1bWVudC5xdWVyeVNlbGVjdG9yKCcuY2F0ZWdvcnktY2FyZC5hY3RpdmUnKTtcbiAgICBjb25zdCBhY3RpdmVGaWx0ZXIgPSBhY3RpdmVCdG4gPyBhY3RpdmVCdG4uZ2V0QXR0cmlidXRlKCdkYXRhLWZpbHRlcicpIDogJ2FsbCc7XG4gICAgbGV0IGFueVZpc2libGUgPSBmYWxzZTtcblxuICAgIHNlY3Rpb25zLmZvckVhY2goZnVuY3Rpb24gKHNlY3Rpb24pIHtcbiAgICAgIGNvbnN0IGNhdCA9IHNlY3Rpb24uZ2V0QXR0cmlidXRlKCdkYXRhLWNhdGVnb3J5Jyk7XG4gICAgICBjb25zdCBjYXRNYXRjaCA9IGFjdGl2ZUZpbHRlciA9PT0gJ2FsbCcgfHwgYWN0aXZlRmlsdGVyID09PSBjYXQ7XG4gICAgICBsZXQgaGFzVmlzaWJsZSA9IGZhbHNlO1xuICAgICAgY29uc3QgY2FyZHMgPSBzZWN0aW9uLnF1ZXJ5U2VsZWN0b3JBbGwoJy50b29sLWNhcmQnKTtcblxuICAgICAgY2FyZHMuZm9yRWFjaChmdW5jdGlvbiAoY2FyZCkge1xuICAgICAgICBjb25zdCBuYW1lRWwgPSBjYXJkLnF1ZXJ5U2VsZWN0b3IoJy50b29sLWNhcmQtbmFtZScpO1xuICAgICAgICBjb25zdCBkZXNjRWwgPSBjYXJkLnF1ZXJ5U2VsZWN0b3IoJy50b29sLWNhcmQtZGVzYycpO1xuICAgICAgICBjb25zdCBuYW1lID0gbmFtZUVsID8gbmFtZUVsLnRleHRDb250ZW50LnRvTG93ZXJDYXNlKCkgOiAnJztcbiAgICAgICAgY29uc3QgZGVzYyA9IGRlc2NFbCA/IGRlc2NFbC50ZXh0Q29udGVudC50b0xvd2VyQ2FzZSgpIDogJyc7XG4gICAgICAgIGNvbnN0IG1hdGNoID0gbmFtZS5pbmNsdWRlcyhxdWVyeSkgfHwgZGVzYy5pbmNsdWRlcyhxdWVyeSk7XG4gICAgICAgIGNhcmQuc3R5bGUuZGlzcGxheSA9IG1hdGNoID8gJycgOiAnbm9uZSc7XG4gICAgICAgIGlmIChtYXRjaCkgaGFzVmlzaWJsZSA9IHRydWU7XG4gICAgICB9KTtcblxuICAgICAgY29uc3Qgc2hvdyA9IGNhdE1hdGNoICYmIGhhc1Zpc2libGU7XG4gICAgICBzZWN0aW9uLnN0eWxlLmRpc3BsYXkgPSBzaG93ID8gJycgOiAnbm9uZSc7XG4gICAgICBpZiAoc2hvdykgYW55VmlzaWJsZSA9IHRydWU7XG4gICAgfSk7XG5cbiAgICBpZiAoZW1wdHlTdGF0ZSkge1xuICAgICAgZW1wdHlTdGF0ZS5jbGFzc0xpc3QudG9nZ2xlKCdzaG93JywgIWFueVZpc2libGUpO1xuICAgIH1cbiAgfVxuXG4gIC8qIFx1MjUwMFx1MjUwMCBTaG93IHNrZWxldG9uLCBoaWRlIGFmdGVyIHBhZ2UgcmVhZHkgXHUyNTAwXHUyNTAwICovXG4gIGZ1bmN0aW9uIHNob3dTa2VsZXRvbihzaG93KSB7XG4gICAgaWYgKCFza2VsZXRvbkdyaWQgfHwgIXRvb2xzR3JpZCkgcmV0dXJuO1xuICAgIHNrZWxldG9uR3JpZC5jbGFzc0xpc3QudG9nZ2xlKCdoaWRkZW4nLCAhc2hvdyk7XG4gICAgdG9vbHNHcmlkLmNsYXNzTGlzdC50b2dnbGUoJ2hpZGRlbicsIHNob3cpO1xuICB9XG5cbiAgLyogXHUyNTAwXHUyNTAwIEV2ZW50IGhhbmRsZXJzIFx1MjUwMFx1MjUwMCAqL1xuICBpZiAoc2VhcmNoSW5wdXQpIHtcbiAgICBzZWFyY2hJbnB1dC5hZGRFdmVudExpc3RlbmVyKCdpbnB1dCcsIHdpbmRvdy5zYnIuZGVib3VuY2UoZnVuY3Rpb24gKCkge1xuICAgICAgY29uc3QgcSA9IHNlYXJjaElucHV0LnZhbHVlLnRyaW0oKS50b0xvd2VyQ2FzZSgpO1xuICAgICAgZmlsdGVyVG9vbHMoKTtcbiAgICAgIHJlbmRlclN1Z2dlc3Rpb25zKHEpO1xuICAgIH0sIDE1MCkpO1xuXG4gICAgc2VhcmNoSW5wdXQuYWRkRXZlbnRMaXN0ZW5lcignZm9jdXMnLCBmdW5jdGlvbiAoKSB7XG4gICAgICByZW5kZXJTdWdnZXN0aW9ucyh0aGlzLnZhbHVlLnRyaW0oKS50b0xvd2VyQ2FzZSgpKTtcbiAgICB9KTtcblxuICAgIHNlYXJjaElucHV0LmFkZEV2ZW50TGlzdGVuZXIoJ2JsdXInLCBmdW5jdGlvbiAoKSB7XG4gICAgICBzZXRUaW1lb3V0KGNsb3NlU3VnZ2VzdGlvbnMsIDIwMCk7XG4gICAgfSk7XG5cbiAgICBzZWFyY2hJbnB1dC5hZGRFdmVudExpc3RlbmVyKCdrZXlkb3duJywgZnVuY3Rpb24gKGUpIHtcbiAgICAgIGNvbnN0IGl0ZW1zID0gJCQoJy5zZWFyY2gtc3VnZ2VzdGlvbi1pdGVtJyk7XG4gICAgICBpZiAoZS5rZXkgPT09ICdBcnJvd0Rvd24nKSB7XG4gICAgICAgIGUucHJldmVudERlZmF1bHQoKTtcbiAgICAgICAgY29uc3QgbmV4dCA9IGN1cnJlbnRGb2N1c0lkeCA8IGl0ZW1zLmxlbmd0aCAtIDEgPyBjdXJyZW50Rm9jdXNJZHggKyAxIDogMDtcbiAgICAgICAgc2V0Rm9jdXMobmV4dCk7XG4gICAgICB9IGVsc2UgaWYgKGUua2V5ID09PSAnQXJyb3dVcCcpIHtcbiAgICAgICAgZS5wcmV2ZW50RGVmYXVsdCgpO1xuICAgICAgICBjb25zdCBwcmV2ID0gY3VycmVudEZvY3VzSWR4ID4gMCA/IGN1cnJlbnRGb2N1c0lkeCAtIDEgOiBpdGVtcy5sZW5ndGggLSAxO1xuICAgICAgICBzZXRGb2N1cyhwcmV2KTtcbiAgICAgIH0gZWxzZSBpZiAoZS5rZXkgPT09ICdFbnRlcicgJiYgY3VycmVudEZvY3VzSWR4ID49IDApIHtcbiAgICAgICAgZS5wcmV2ZW50RGVmYXVsdCgpO1xuICAgICAgICBzZWxlY3RTdWdnZXN0aW9uKGN1cnJlbnRGb2N1c0lkeCk7XG4gICAgICB9IGVsc2UgaWYgKGUua2V5ID09PSAnRXNjYXBlJykge1xuICAgICAgICBjbG9zZVN1Z2dlc3Rpb25zKCk7XG4gICAgICAgIHRoaXMuYmx1cigpO1xuICAgICAgfSBlbHNlIGlmIChlLmtleSA9PT0gJy8nICYmIGRvY3VtZW50LmFjdGl2ZUVsZW1lbnQgIT09IHNlYXJjaElucHV0KSB7XG4gICAgICAgIGUucHJldmVudERlZmF1bHQoKTtcbiAgICAgICAgc2VhcmNoSW5wdXQuZm9jdXMoKTtcbiAgICAgIH1cbiAgICB9KTtcbiAgfVxuXG4gIGRvY3VtZW50LmFkZEV2ZW50TGlzdGVuZXIoJ2tleWRvd24nLCBmdW5jdGlvbiAoZSkge1xuICAgIGlmIChlLmtleSA9PT0gJy8nICYmIGRvY3VtZW50LmFjdGl2ZUVsZW1lbnQgIT09IHNlYXJjaElucHV0ICYmIGRvY3VtZW50LmFjdGl2ZUVsZW1lbnQgIT09IGRvY3VtZW50LmJvZHkpIHJldHVybjtcbiAgICBpZiAoZS5rZXkgPT09ICcvJyAmJiBkb2N1bWVudC5hY3RpdmVFbGVtZW50ICE9PSBzZWFyY2hJbnB1dCkge1xuICAgICAgZS5wcmV2ZW50RGVmYXVsdCgpO1xuICAgICAgaWYgKHNlYXJjaElucHV0KSBzZWFyY2hJbnB1dC5mb2N1cygpO1xuICAgIH1cbiAgfSk7XG5cbiAgLyogQ2F0ZWdvcnkgY2FyZHMgKi9cbiAgaWYgKGNhdGVnb3J5QnRucy5sZW5ndGgpIHtcbiAgICBjYXRlZ29yeUJ0bnMuZm9yRWFjaChmdW5jdGlvbiAoYnRuKSB7XG4gICAgICBidG4uYWRkRXZlbnRMaXN0ZW5lcignY2xpY2snLCBmdW5jdGlvbiAoKSB7XG4gICAgICAgIGNhdGVnb3J5QnRucy5mb3JFYWNoKGZ1bmN0aW9uIChiKSB7XG4gICAgICAgICAgYi5jbGFzc0xpc3QucmVtb3ZlKCdhY3RpdmUnKTtcbiAgICAgICAgICBiLnNldEF0dHJpYnV0ZSgnYXJpYS1zZWxlY3RlZCcsICdmYWxzZScpO1xuICAgICAgICB9KTtcbiAgICAgICAgdGhpcy5jbGFzc0xpc3QuYWRkKCdhY3RpdmUnKTtcbiAgICAgICAgdGhpcy5zZXRBdHRyaWJ1dGUoJ2FyaWEtc2VsZWN0ZWQnLCAndHJ1ZScpO1xuICAgICAgICBjbG9zZVN1Z2dlc3Rpb25zKCk7XG4gICAgICAgIGZpbHRlclRvb2xzKCk7XG4gICAgICB9KTtcbiAgICB9KTtcbiAgfVxuXG4gIC8qIENsZWFyIGZpbHRlcnMgYnV0dG9uICovXG4gIGlmIChjbGVhckJ0bikge1xuICAgIGNsZWFyQnRuLmFkZEV2ZW50TGlzdGVuZXIoJ2NsaWNrJywgZnVuY3Rpb24gKCkge1xuICAgICAgY29uc3QgYWxsQnRuID0gZG9jdW1lbnQucXVlcnlTZWxlY3RvcignLmNhdGVnb3J5LWNhcmRbZGF0YS1maWx0ZXI9XCJhbGxcIl0nKTtcbiAgICAgIGlmIChhbGxCdG4pIHtcbiAgICAgICAgY2F0ZWdvcnlCdG5zLmZvckVhY2goZnVuY3Rpb24gKGIpIHtcbiAgICAgICAgICBiLmNsYXNzTGlzdC5yZW1vdmUoJ2FjdGl2ZScpO1xuICAgICAgICAgIGIuc2V0QXR0cmlidXRlKCdhcmlhLXNlbGVjdGVkJywgJ2ZhbHNlJyk7XG4gICAgICAgIH0pO1xuICAgICAgICBhbGxCdG4uY2xhc3NMaXN0LmFkZCgnYWN0aXZlJyk7XG4gICAgICAgIGFsbEJ0bi5zZXRBdHRyaWJ1dGUoJ2FyaWEtc2VsZWN0ZWQnLCAndHJ1ZScpO1xuICAgICAgfVxuICAgICAgaWYgKHNlYXJjaElucHV0KSBzZWFyY2hJbnB1dC52YWx1ZSA9ICcnO1xuICAgICAgZmlsdGVyVG9vbHMoKTtcbiAgICAgIGlmIChzZWFyY2hJbnB1dCkgc2VhcmNoSW5wdXQuZm9jdXMoKTtcbiAgICB9KTtcbiAgfVxuXG4gIC8qIFx1MjUwMFx1MjUwMCBJbml0IFx1MjUwMFx1MjUwMCAqL1xuICBmdW5jdGlvbiBpbml0KCkge1xuICAgIHNob3dTa2VsZXRvbih0cnVlKTtcbiAgICByZXF1ZXN0QW5pbWF0aW9uRnJhbWUoZnVuY3Rpb24gKCkge1xuICAgICAgc2V0VGltZW91dChmdW5jdGlvbiAoKSB7XG4gICAgICAgIHNob3dTa2VsZXRvbihmYWxzZSk7XG4gICAgICAgIGZpbHRlclRvb2xzKCk7XG4gICAgICB9LCA0MDApO1xuICAgIH0pO1xuICB9XG5cbiAgaWYgKGRvY3VtZW50LnJlYWR5U3RhdGUgPT09ICdsb2FkaW5nJykge1xuICAgIGRvY3VtZW50LmFkZEV2ZW50TGlzdGVuZXIoJ0RPTUNvbnRlbnRMb2FkZWQnLCBpbml0KTtcbiAgfSBlbHNlIHtcbiAgICBpbml0KCk7XG4gIH1cbn0pKCk7XG4iXSwKICAibWFwcGluZ3MiOiAiOztBQUFBLEdBQUMsV0FBWTtBQUNYO0FBRUEsVUFBTSxjQUFjO0FBQ3BCLFVBQU0sYUFBYTtBQUNuQixVQUFNLElBQUksQ0FBQyxHQUFHLE9BQU8sS0FBSyxVQUFVLGNBQWMsQ0FBQztBQUNuRCxVQUFNLEtBQUssQ0FBQyxHQUFHLE1BQU0sQ0FBQyxJQUFJLEtBQUssVUFBVSxpQkFBaUIsQ0FBQyxDQUFDO0FBRTVELFVBQU0sY0FBYyxFQUFFLGtCQUFrQjtBQUN4QyxVQUFNLGNBQWMsRUFBRSxvQkFBb0I7QUFDMUMsVUFBTSxtQkFBbUIsRUFBRSxtQkFBbUI7QUFDOUMsVUFBTSxlQUFlLEVBQUUsZUFBZTtBQUN0QyxVQUFNLFlBQVksRUFBRSxZQUFZO0FBQ2hDLFVBQU0sYUFBYSxFQUFFLGFBQWE7QUFDbEMsVUFBTSxXQUFXLEVBQUUsa0JBQWtCO0FBQ3JDLFVBQU0sZUFBZSxHQUFHLGdCQUFnQjtBQUN4QyxVQUFNLFdBQVcsR0FBRyxtQkFBbUI7QUFDdkMsVUFBTSxZQUFZLE1BQU0sR0FBRyxZQUFZO0FBRXZDLFFBQUksa0JBQWtCO0FBQ3RCLFFBQUksa0JBQWtCLENBQUM7QUFH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
