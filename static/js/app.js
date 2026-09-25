(() => {
  // src/js/app.js
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
    var html = document.documentElement;
    function setTheme(t) {
      html.setAttribute("data-theme", t);
      store.set("sb-theme", t);
    }
    document.querySelectorAll(".theme-toggle").forEach(function(b2) {
      b2.addEventListener("click", function() {
        var c = html.getAttribute("data-theme") || "night";
        setTheme(c === "night" ? "light" : "night");
      });
    });
    window.matchMedia("(prefers-color-scheme: dark)").addEventListener("change", function(e) {
      if (!store.get("sb-theme")) {
        setTheme(e.matches ? "night" : "light");
      }
    });
    var nav = document.getElementById("siteNavbar"), sh = document.getElementById("siteHeader");
    function hS() {
      var s = window.scrollY > 20;
      if (nav) nav.classList.toggle("shadow-sm", s);
      if (sh) sh.classList.toggle("scrolled", s);
    }
    window.addEventListener("scroll", hS, { passive: true });
    hS();
    if (window.location.pathname.indexOf("/tool/") === 0) {
      document.querySelectorAll(".nav-link").forEach(function(l) {
        if (l.getAttribute("href") === "/#tools") l.classList.add("active");
      });
    }
    document.querySelectorAll(".tilt-card[data-tilt]").forEach(function(c) {
      c.addEventListener("mousemove", function(e) {
        var r = this.getBoundingClientRect(), x = (e.clientX - r.left) / r.width - 0.5, y = (e.clientY - r.top) / r.height - 0.5;
        this.style.setProperty("--tilt-x", -y * 12 + "deg");
        this.style.setProperty("--tilt-y", x * 12 + "deg");
      });
      c.addEventListener("mouseleave", function() {
        this.style.setProperty("--tilt-x", "0deg");
        this.style.setProperty("--tilt-y", "0deg");
      });
    });
    document.querySelectorAll(".btn-ripple").forEach(function(b2) {
      b2.addEventListener("mousedown", function(e) {
        var r = this.getBoundingClientRect();
        this.style.setProperty("--ripple-x", (e.clientX - r.left) / r.width * 100 + "%");
        this.style.setProperty("--ripple-y", (e.clientY - r.top) / r.height * 100 + "%");
      });
    });
    var dia = document.getElementById("searchDialog"), si = document.getElementById("searchInput"), sr = document.getElementById("searchResults"), toolCache = null;
    function _msg(m) {
      if (!sr) return;
      sr.innerHTML = "";
      var p = document.createElement("p");
      p.className = "text-base-content/30 text-center py-4";
      p.textContent = m;
      sr.appendChild(p);
    }
    function _results(items) {
      if (!sr) return;
      sr.innerHTML = "";
      if (!items || !items.length) {
        _msg("No results found");
        return;
      }
      var df = document.createDocumentFragment();
      items.slice(0, 20).forEach(function(t) {
        var a = document.createElement("a");
        a.setAttribute("href", typeof t.url === "string" && t.url.charAt(0) === "/" ? t.url : "#");
        a.className = "flex items-center justify-between p-3 rounded-xl hover:glass transition-all duration-200";
        var d1 = document.createElement("div");
        var d2 = document.createElement("div");
        d2.className = "font-semibold text-sm";
        d2.textContent = t.name || "";
        d1.appendChild(d2);
        var d3 = document.createElement("div");
        d3.className = "text-xs text-base-content/40";
        d3.textContent = t.category || "";
        d1.appendChild(d3);
        a.appendChild(d1);
        var sv = document.createElementNS("http://www.w3.org/2000/svg", "svg");
        sv.setAttribute("class", "w-4 h-4 text-base-content/20");
        sv.setAttribute("viewBox", "0 0 24 24");
        sv.setAttribute("fill", "none");
        sv.setAttribute("stroke", "currentColor");
        sv.setAttribute("stroke-width", "2");
        var p1 = document.createElementNS("http://www.w3.org/2000/svg", "path");
        p1.setAttribute("d", "M5 12h14");
        sv.appendChild(p1);
        var p2 = document.createElementNS("http://www.w3.org/2000/svg", "path");
        p2.setAttribute("d", "m12 5 7 7-7 7");
        sv.appendChild(p2);
        a.appendChild(sv);
        a.addEventListener("click", function() {
          if (dia) dia.close();
        });
        df.appendChild(a);
      });
      sr.appendChild(df);
    }
    function oS() {
      if (!dia) return;
      dia.showModal();
      if (si) si.focus();
      if (!toolCache) {
        fetch("/api/tools/catalog").then(function(r) {
          return r.json();
        }).then(function(d) {
          toolCache = d;
          filterTools();
        }).catch(function() {
          if (sr) _msg("Could not load tools. Try again later.");
        });
      }
    }
    function filterTools() {
      if (!si || !sr) return;
      var q = si.value.trim().toLowerCase();
      if (!toolCache || !q) {
        _msg(q ? "No results found" : "Start typing to find tools");
        return;
      }
      var m = toolCache.filter(function(t) {
        return t.name.toLowerCase().indexOf(q) > -1 || t.desc && t.desc.toLowerCase().indexOf(q) > -1;
      });
      _results(m);
    }
    function cS() {
      if (dia) dia.close();
      document.querySelectorAll("[id^=searchToggle]").forEach(function(b2) {
        b2.setAttribute("aria-expanded", "false");
      });
    }
    document.querySelectorAll("[id^=searchToggle]").forEach(function(b2) {
      b2.setAttribute("aria-expanded", "false");
      b2.addEventListener("click", function() {
        oS();
        b2.setAttribute("aria-expanded", "true");
      });
    });
    var hsi = document.getElementById("heroSearchInput");
    function openFromHero() {
      if (dia && dia.open) return;
      var v = hsi ? hsi.value : "";
      oS();
      if (si && v) {
        si.value = v;
        filterTools();
      }
      if (hsi) {
        hsi.setAttribute("aria-expanded", "true");
        try {
          hsi.blur();
        } catch (e) {
        }
      }
    }
    if (hsi) {
      hsi.setAttribute("aria-haspopup", "dialog");
      hsi.setAttribute("aria-expanded", "false");
      hsi.addEventListener("click", openFromHero);
      hsi.addEventListener("keydown", function(e) {
        if (e.key === "Enter") {
          e.preventDefault();
          openFromHero();
        }
      });
    }
    function _isEditable(el) {
      if (!el || !el.tagName) return false;
      var t = el.tagName.toLowerCase();
      return t === "input" || t === "textarea" || t === "select" || el.isContentEditable === true;
    }
    document.addEventListener("keydown", function(e) {
      if (e.key !== "/" || e.ctrlKey || e.metaKey || e.altKey) return;
      if (dia && dia.open) return;
      if (_isEditable(document.activeElement)) return;
      if (document.getElementById("toolSearchInput")) return;
      e.preventDefault();
      oS();
    });
    var sc = document.getElementById("searchClose");
    if (sc) sc.addEventListener("click", cS);
    if (dia) {
      dia.addEventListener("click", function(e) {
        if (e.target === dia) cS();
      });
      dia.addEventListener("keydown", function(e) {
        if (e.key === "Escape") cS();
      });
      dia.addEventListener("close", function() {
        if (hsi) hsi.setAttribute("aria-expanded", "false");
        document.querySelectorAll("[id^=searchToggle]").forEach(function(b2) {
          b2.setAttribute("aria-expanded", "false");
        });
      });
    }
    if ("serviceWorker" in navigator) {
      var swRefreshing = false;
      navigator.serviceWorker.register("/service-worker", { scope: "/" }).then(function(reg) {
        reg.addEventListener("updatefound", function() {
          var w = reg.installing;
          if (w) {
            w.addEventListener("statechange", function() {
              if (w.state === "installed" && navigator.serviceWorker.controller) {
                var msg = document.createElement("div");
                msg.className = "fixed bottom-4 right-4 z-50 glass-strong rounded-xl shadow-2xl border border-primary/20 animate-fade-in";
                msg.setAttribute("role", "alert");
                var btn = document.createElement("button");
                btn.className = "flex items-center gap-2 px-4 py-3 text-sm font-bold cursor-pointer focus-visible:outline-2 focus-visible:outline-primary rounded-xl";
                btn.innerHTML = 'New version available! <span class="text-primary ml-1">Refresh</span>';
                btn.addEventListener("click", function() {
                  w.postMessage({ action: "skipWaiting" });
                });
                btn.addEventListener("keydown", function(e) {
                  if (e.key === "Enter" || e.key === " ") {
                    e.preventDefault();
                    w.postMessage({ action: "skipWaiting" });
                  }
                });
                msg.appendChild(btn);
                document.body.appendChild(msg);
                btn.focus();
              }
            });
          }
        });
      }).catch(function() {
      });
    }
    navigator.serviceWorker.addEventListener("controllerchange", function() {
      if (swRefreshing) return;
      swRefreshing = true;
      window.location.reload();
    });
    document.addEventListener("click", function(e) {
      var t = e.target.closest("[data-dialog-trigger]");
      if (t) {
        var id = t.dataset.dialogTrigger, dlg = document.getElementById(id);
        if (dlg) {
          if (dlg.tagName === "DIALOG") dlg.showModal();
          else {
            dlg.classList.remove("hidden");
            dlg.classList.add("flex");
            document.body.style.overflow = "hidden";
          }
        }
        return;
      }
      var cb = e.target.closest("[data-dialog-close]");
      if (cb) {
        cD(cb.dataset.dialogClose);
        return;
      }
      var ov = e.target.closest("[data-dialog-overlay]");
      if (ov) {
        var d2 = ov.closest("[data-dialog]");
        if (d2) cD(d2.id);
      }
    });
    document.addEventListener("keydown", function(e) {
      if (e.key === "Escape") {
        document.querySelectorAll("[data-dialog]:not(.hidden)").forEach(function(d) {
          cD(d.id);
        });
      }
    });
    function cD(id) {
      var dlg = document.getElementById(id);
      if (dlg) {
        if (dlg.tagName === "DIALOG") dlg.close();
        else {
          dlg.classList.add("hidden");
          dlg.classList.remove("flex");
          document.body.style.overflow = "";
        }
      }
    }
    function toggleAccordion(t) {
      var ac = t.closest("[data-accordion]");
      if (!ac) return;
      var it = t.closest("[data-accordion-item]"), isOpen = it ? it.dataset.open === "true" : false;
      if (ac.dataset.accordion !== "multi") {
        ac.querySelectorAll("[data-accordion-item]").forEach(function(i) {
          i.dataset.open = "false";
          var c = i.querySelector("[data-accordion-content]");
          if (c) {
            c.style.display = "none";
            c.style.maxHeight = "0";
          }
          var ch = i.querySelector("[data-accordion-chevron]");
          if (ch) ch.classList.remove("rotate-180");
          var tr = i.querySelector("[data-accordion-trigger]");
          if (tr) tr.setAttribute("aria-expanded", "false");
        });
      }
      if (it) {
        var nO = isOpen ? "false" : "true";
        it.dataset.open = nO;
        var c2 = it.querySelector("[data-accordion-content]");
        if (c2) {
          c2.style.display = nO === "true" ? "block" : "none";
          c2.style.maxHeight = nO === "true" ? c2.scrollHeight + "px" : "0";
        }
        var ch2 = it.querySelector("[data-accordion-chevron]");
        if (ch2) ch2.classList.toggle("rotate-180", nO === "true");
        t.setAttribute("aria-expanded", nO);
      }
    }
    document.addEventListener("click", function(e) {
      var t = e.target.closest("[data-accordion-trigger]");
      if (t) {
        e.preventDefault();
        toggleAccordion(t);
      }
    });
    document.addEventListener("keydown", function(e) {
      if (e.key !== "Enter" && e.key !== " ") return;
      var t = e.target.closest("[data-accordion-trigger]");
      if (t) {
        e.preventDefault();
        toggleAccordion(t);
      }
    });
    document.querySelectorAll('[data-accordion-item][data-open="true"]').forEach(function(it) {
      var c = it.querySelector("[data-accordion-content]");
      if (c) {
        c.style.display = "block";
        c.style.maxHeight = c.scrollHeight + "px";
      }
      var ch = it.querySelector("[data-accordion-chevron]");
      if (ch) ch.classList.add("rotate-180");
    });
    document.querySelectorAll('.dropdown button[aria-haspopup="true"]').forEach(function(b2) {
      b2.addEventListener("click", function() {
        var d = b2.closest(".dropdown"), c = d ? d.querySelector(".dropdown-content") : null;
        if (c) {
          var o = c.style.display !== "block";
          c.style.display = o ? "block" : "";
          b2.setAttribute("aria-expanded", o);
        }
      });
    });
    if ("IntersectionObserver" in window) {
      var ro = new IntersectionObserver(function(es) {
        es.forEach(function(e) {
          if (e.isIntersecting) {
            e.target.classList.add("visible");
            ro.unobserve(e.target);
          }
        });
      }, { threshold: 0.1 });
      document.querySelectorAll(".reveal").forEach(function(el) {
        ro.observe(el);
      });
    } else {
      document.querySelectorAll(".reveal").forEach(function(el) {
        el.classList.add("visible");
      });
    }
    var an = document.getElementById("analytics-track");
    if (an && "sendBeacon" in navigator) {
      var b = new Blob([JSON.stringify({ name: an.dataset.tool || "page", category: "page_view" })], { type: "application/json" });
      navigator.sendBeacon("/api/track", b);
    }
    document.addEventListener("click", function(e) {
      var el = e.target && e.target.closest ? e.target.closest("[data-action]") : null;
      if (!el) return;
      var a = el.getAttribute("data-action"), w = window;
      function idx() {
        var v = parseInt(el.getAttribute("data-index"), 10);
        return isNaN(v) ? 0 : v;
      }
      if (a === "close-dialog") {
        var t = el.getAttribute("data-target"), d = t && document.getElementById(t);
        if (d && d.close) d.close();
        return;
      }
      if (a === "close-zoom") {
        el.classList.remove("open");
        return;
      }
      if (a === "refresh-fng") {
        return;
      }
      if (a === "meme-preset") {
        if (typeof w.applyPreset === "function") w.applyPreset(el.getAttribute("data-preset"));
        return;
      }
      if (a === "meme-download") {
        if (typeof w.downloadMeme === "function") w.downloadMeme();
        return;
      }
      if (a === "meme-copy") {
        if (typeof w.copyMeme === "function") w.copyMeme();
        return;
      }
      if (a === "meme-clear-hist") {
        if (typeof w.clearHist === "function") w.clearHist();
        return;
      }
      if (a === "meme-restore-hist") {
        if (typeof w.restoreHist === "function") w.restoreHist(idx());
        return;
      }
      if (a === "meme-del-hist") {
        if (typeof w.delHist === "function") w.delHist(idx());
        return;
      }
      if (a === "qr-dot-style") {
        if (typeof w.setDotStyle === "function") w.setDotStyle(el.getAttribute("data-style"), el);
        return;
      }
      if (a === "qr-eye-style") {
        if (typeof w.setEyeStyle === "function") w.setEyeStyle(el.getAttribute("data-style"), el);
        return;
      }
      if (a === "qr-clear-logo") {
        if (typeof w.clearLogo === "function") w.clearLogo();
        return;
      }
      if (a === "qr-scan") {
        if (typeof w.scanQR === "function") w.scanQR();
        return;
      }
      if (a === "qr-fill-scan") {
        if (typeof w.fillFromScan === "function") w.fillFromScan();
        return;
      }
      if (a === "qr-gen") {
        if (typeof w.gen === "function") w.gen();
        return;
      }
      if (a === "qr-download-png") {
        if (typeof w.downloadPNG === "function") w.downloadPNG();
        return;
      }
      if (a === "qr-download-svg") {
        if (typeof w.downloadSVG === "function") w.downloadSVG();
        return;
      }
      if (a === "qr-copy-png") {
        if (typeof w.copyPNG === "function") w.copyPNG();
        return;
      }
      if (a === "qr-copy-svg") {
        if (typeof w.copySVGCode === "function") w.copySVGCode();
        return;
      }
      if (a === "qr-clear-hist") {
        if (typeof w.clearHist === "function") w.clearHist();
        return;
      }
      if (a === "qr-restore-hist") {
        if (typeof w.restoreHist === "function") w.restoreHist(idx());
        return;
      }
      if (a === "qr-apply-preset") {
        if (typeof w.applyPreset === "function") w.applyPreset(el.getAttribute("data-fg"), el.getAttribute("data-bg"));
        return;
      }
    });
    var hs = document.getElementById("heroSection");
    if (hs) {
      var _r = null, _rid = false;
      hs.addEventListener("mousemove", function(e) {
        if (_rid) cancelAnimationFrame(_r);
        _rid = true;
        _r = requestAnimationFrame(function() {
          var b2 = hs.getBoundingClientRect(), mx = (e.clientX - b2.left) / b2.width * 100, my = (e.clientY - b2.top) / b2.height * 100;
          hs.style.setProperty("--mx", mx + "%");
          hs.style.setProperty("--my", my + "%");
          _rid = false;
        });
      }, { passive: true });
    }
  })();
})();
//# sourceMappingURL=data:application/json;base64,ewogICJ2ZXJzaW9uIjogMywKICAic291cmNlcyI6IFsiLi4vLi4vc3JjL2pzL2FwcC5qcyJdLAogICJzb3VyY2VzQ29udGVudCI6IFsiLyogXHUyNTAwXHUyNTAwIFN0b3J5QnJhaW4gQUk6IGFwcC5qcyAoYmFzZS5qcyArIHVpLWluaXQuanMgYnVuZGxlZCkgXHUyNTAwXHUyNTAwICovXHJcbi8qIFNDSEVNQSBsb2NhbFN0b3JhZ2Uga2V5czogc2ItdGhlbWUgKCdsaWdodCd8J25pZ2h0JyksIGNvb2tpZUNvbnNlbnQgKCdhY2NlcHRlZCd8J3JlamVjdGVkJyksIHNicl90b29sc19yZWNlbnRfc2VhcmNoIChKU09OIGFycmF5KSAqL1xyXG4oZnVuY3Rpb24oKXsndXNlIHN0cmljdCc7Y29uc3Qgc3RvcmU9e2dldChrKXt0cnl7cmV0dXJuIGxvY2FsU3RvcmFnZS5nZXRJdGVtKGspfWNhdGNoe3JldHVybiBudWxsfX0sc2V0KGssdil7dHJ5e2xvY2FsU3RvcmFnZS5zZXRJdGVtKGssdil9Y2F0Y2h7fX0sZGVsKGspe3RyeXtsb2NhbFN0b3JhZ2UucmVtb3ZlSXRlbShrKX1jYXRjaHt9fX07dmFyIGh0bWw9ZG9jdW1lbnQuZG9jdW1lbnRFbGVtZW50O2Z1bmN0aW9uIHNldFRoZW1lKHQpe2h0bWwuc2V0QXR0cmlidXRlKCdkYXRhLXRoZW1lJyx0KTtzdG9yZS5zZXQoJ3NiLXRoZW1lJyx0KX1cclxuZG9jdW1lbnQucXVlcnlTZWxlY3RvckFsbCgnLnRoZW1lLXRvZ2dsZScpLmZvckVhY2goZnVuY3Rpb24oYil7Yi5hZGRFdmVudExpc3RlbmVyKCdjbGljaycsZnVuY3Rpb24oKXt2YXIgYz1odG1sLmdldEF0dHJpYnV0ZSgnZGF0YS10aGVtZScpfHwnbmlnaHQnO3NldFRoZW1lKGM9PT0nbmlnaHQnPydsaWdodCc6J25pZ2h0Jyl9KX0pXHJcbndpbmRvdy5tYXRjaE1lZGlhKCcocHJlZmVycy1jb2xvci1zY2hlbWU6IGRhcmspJykuYWRkRXZlbnRMaXN0ZW5lcignY2hhbmdlJyxmdW5jdGlvbihlKXtpZighc3RvcmUuZ2V0KCdzYi10aGVtZScpKXtzZXRUaGVtZShlLm1hdGNoZXM/J25pZ2h0JzonbGlnaHQnKX19KVxyXG52YXIgbmF2PWRvY3VtZW50LmdldEVsZW1lbnRCeUlkKCdzaXRlTmF2YmFyJyksc2g9ZG9jdW1lbnQuZ2V0RWxlbWVudEJ5SWQoJ3NpdGVIZWFkZXInKTtmdW5jdGlvbiBoUygpe3ZhciBzPXdpbmRvdy5zY3JvbGxZPjIwO2lmKG5hdiluYXYuY2xhc3NMaXN0LnRvZ2dsZSgnc2hhZG93LXNtJyxzKTtpZihzaClzaC5jbGFzc0xpc3QudG9nZ2xlKCdzY3JvbGxlZCcscyl9XHJcbndpbmRvdy5hZGRFdmVudExpc3RlbmVyKCdzY3JvbGwnLGhTLHtwYXNzaXZlOnRydWV9KTtoUygpXHJcblxyXG4vKiBcdTI1MDBcdTI1MDAgTmF2IGFjdGl2ZSBzdGF0ZSBmb3IgdG9vbCBwYWdlcyBcdTI1MDBcdTI1MDAgKi9cclxuaWYod2luZG93LmxvY2F0aW9uLnBhdGhuYW1lLmluZGV4T2YoJy90b29sLycpPT09MCl7ZG9jdW1lbnQucXVlcnlTZWxlY3RvckFsbCgnLm5hdi1saW5rJykuZm9yRWFjaChmdW5jdGlvbihsKXtpZihsLmdldEF0dHJpYnV0ZSgnaHJlZicpPT09Jy8jdG9vbHMnKWwuY2xhc3NMaXN0LmFkZCgnYWN0aXZlJyl9KX1cclxuXHJcbi8qIFx1MjUwMFx1MjUwMCBUaWx0IGNhcmRzIFx1MjUwMFx1MjUwMCAqL1xyXG5kb2N1bWVudC5xdWVyeVNlbGVjdG9yQWxsKCcudGlsdC1jYXJkW2RhdGEtdGlsdF0nKS5mb3JFYWNoKGZ1bmN0aW9uKGMpe2MuYWRkRXZlbnRMaXN0ZW5lcignbW91c2Vtb3ZlJyxmdW5jdGlvbihlKXt2YXIgcj10aGlzLmdldEJvdW5kaW5nQ2xpZW50UmVjdCgpLHg9KGUuY2xpZW50WC1yLmxlZnQpL3Iud2lkdGgtMC41LHk9KGUuY2xpZW50WS1yLnRvcCkvci5oZWlnaHQtMC41O3RoaXMuc3R5bGUuc2V0UHJvcGVydHkoJy0tdGlsdC14JywoLXkqMTIpKydkZWcnKTt0aGlzLnN0eWxlLnNldFByb3BlcnR5KCctLXRpbHQteScsKHgqMTIpKydkZWcnKX0pO2MuYWRkRXZlbnRMaXN0ZW5lcignbW91c2VsZWF2ZScsZnVuY3Rpb24oKXt0aGlzLnN0eWxlLnNldFByb3BlcnR5KCctLXRpbHQteCcsJzBkZWcnKTt0aGlzLnN0eWxlLnNldFByb3BlcnR5KCctLXRpbHQteScsJzBkZWcnKX0pfSlcclxuXHJcbi8qIFx1MjUwMFx1MjUwMCBCdXR0b24gcmlwcGxlIFx1MjUwMFx1MjUwMCAqL1xyXG5kb2N1bWVudC5xdWVyeVNlbGVjdG9yQWxsKCcuYnRuLXJpcHBsZScpLmZvckVhY2goZnVuY3Rpb24oYil7Yi5hZGRFdmVudExpc3RlbmVyKCdtb3VzZWRvd24nLGZ1bmN0aW9uKGUpe3ZhciByPXRoaXMuZ2V0Qm91bmRpbmdDbGllbnRSZWN0KCk7dGhpcy5zdHlsZS5zZXRQcm9wZXJ0eSgnLS1yaXBwbGUteCcsKChlLmNsaWVudFgtci5sZWZ0KS9yLndpZHRoKjEwMCkrJyUnKTt0aGlzLnN0eWxlLnNldFByb3BlcnR5KCctLXJpcHBsZS15JywoKGUuY2xpZW50WS1yLnRvcCkvci5oZWlnaHQqMTAwKSsnJScpfSl9KVxyXG52YXIgZGlhPWRvY3VtZW50LmdldEVsZW1lbnRCeUlkKCdzZWFyY2hEaWFsb2cnKSxzaT1kb2N1bWVudC5nZXRFbGVtZW50QnlJZCgnc2VhcmNoSW5wdXQnKSxzcj1kb2N1bWVudC5nZXRFbGVtZW50QnlJZCgnc2VhcmNoUmVzdWx0cycpLHRvb2xDYWNoZT1udWxsO1xyXG5mdW5jdGlvbiBfbXNnKG0pe2lmKCFzcilyZXR1cm47c3IuaW5uZXJIVE1MPScnO3ZhciBwPWRvY3VtZW50LmNyZWF0ZUVsZW1lbnQoJ3AnKTtwLmNsYXNzTmFtZT0ndGV4dC1iYXNlLWNvbnRlbnQvMzAgdGV4dC1jZW50ZXIgcHktNCc7cC50ZXh0Q29udGVudD1tO3NyLmFwcGVuZENoaWxkKHApfVxyXG5mdW5jdGlvbiBfcmVzdWx0cyhpdGVtcyl7aWYoIXNyKXJldHVybjtzci5pbm5lckhUTUw9Jyc7aWYoIWl0ZW1zfHwhaXRlbXMubGVuZ3RoKXtfbXNnKCdObyByZXN1bHRzIGZvdW5kJyk7cmV0dXJufVxyXG52YXIgZGY9ZG9jdW1lbnQuY3JlYXRlRG9jdW1lbnRGcmFnbWVudCgpO2l0ZW1zLnNsaWNlKDAsMjApLmZvckVhY2goZnVuY3Rpb24odCl7dmFyIGE9ZG9jdW1lbnQuY3JlYXRlRWxlbWVudCgnYScpO2Euc2V0QXR0cmlidXRlKCdocmVmJyx0eXBlb2YgdC51cmw9PT0nc3RyaW5nJyYmdC51cmwuY2hhckF0KDApPT09Jy8nP3QudXJsOicjJyk7YS5jbGFzc05hbWU9J2ZsZXggaXRlbXMtY2VudGVyIGp1c3RpZnktYmV0d2VlbiBwLTMgcm91bmRlZC14bCBob3ZlcjpnbGFzcyB0cmFuc2l0aW9uLWFsbCBkdXJhdGlvbi0yMDAnXHJcbnZhciBkMT1kb2N1bWVudC5jcmVhdGVFbGVtZW50KCdkaXYnKTt2YXIgZDI9ZG9jdW1lbnQuY3JlYXRlRWxlbWVudCgnZGl2Jyk7ZDIuY2xhc3NOYW1lPSdmb250LXNlbWlib2xkIHRleHQtc20nO2QyLnRleHRDb250ZW50PXQubmFtZXx8Jyc7ZDEuYXBwZW5kQ2hpbGQoZDIpXHJcbnZhciBkMz1kb2N1bWVudC5jcmVhdGVFbGVtZW50KCdkaXYnKTtkMy5jbGFzc05hbWU9J3RleHQteHMgdGV4dC1iYXNlLWNvbnRlbnQvNDAnO2QzLnRleHRDb250ZW50PXQuY2F0ZWdvcnl8fCcnO2QxLmFwcGVuZENoaWxkKGQzKTthLmFwcGVuZENoaWxkKGQxKVxyXG52YXIgc3Y9ZG9jdW1lbnQuY3JlYXRlRWxlbWVudE5TKCdodHRwOi8vd3d3LnczLm9yZy8yMDAwL3N2ZycsJ3N2ZycpO3N2LnNldEF0dHJpYnV0ZSgnY2xhc3MnLCd3LTQgaC00IHRleHQtYmFzZS1jb250ZW50LzIwJyk7c3Yuc2V0QXR0cmlidXRlKCd2aWV3Qm94JywnMCAwIDI0IDI0Jyk7c3Yuc2V0QXR0cmlidXRlKCdmaWxsJywnbm9uZScpO3N2LnNldEF0dHJpYnV0ZSgnc3Ryb2tlJywnY3VycmVudENvbG9yJyk7c3Yuc2V0QXR0cmlidXRlKCdzdHJva2Utd2lkdGgnLCcyJylcclxudmFyIHAxPWRvY3VtZW50LmNyZWF0ZUVsZW1lbnROUygnaHR0cDovL3d3dy53My5vcmcvMjAwMC9zdmcnLCdwYXRoJyk7cDEuc2V0QXR0cmlidXRlKCdkJywnTTUgMTJoMTQnKTtzdi5hcHBlbmRDaGlsZChwMSlcclxudmFyIHAyPWRvY3VtZW50LmNyZWF0ZUVsZW1lbnROUygnaHR0cDovL3d3dy53My5vcmcvMjAwMC9zdmcnLCdwYXRoJyk7cDIuc2V0QXR0cmlidXRlKCdkJywnbTEyIDUgNyA3LTcgNycpO3N2LmFwcGVuZENoaWxkKHAyKTthLmFwcGVuZENoaWxkKHN2KVxyXG5hLmFkZEV2ZW50TGlzdGVuZXIoJ2NsaWNrJyxmdW5jdGlvbigpe2lmKGRpYSlkaWEuY2xvc2UoKX0pO2RmLmFwcGVuZENoaWxkKGEpfSk7c3IuYXBwZW5kQ2hpbGQoZGYpfVxyXG5mdW5jdGlvbiBvUygpe1xyXG4gIGlmKCFkaWEpcmV0dXJuO1xyXG4gIGRpYS5zaG93TW9kYWwoKTtcclxuICBpZihzaSlzaS5mb2N1cygpO1xyXG4gIGlmKCF0b29sQ2FjaGUpe1xyXG4gICAgZmV0Y2goJy9hcGkvdG9vbHMvY2F0YWxvZycpLnRoZW4oZnVuY3Rpb24ocil7cmV0dXJuIHIuanNvbigpfSkudGhlbihmdW5jdGlvbihkKXt0b29sQ2FjaGU9ZDtmaWx0ZXJUb29scygpfSkuY2F0Y2goZnVuY3Rpb24oKXtpZihzcilfbXNnKCdDb3VsZCBub3QgbG9hZCB0b29scy4gVHJ5IGFnYWluIGxhdGVyLicpfSlcclxuICB9XHJcbn1cclxuZnVuY3Rpb24gZmlsdGVyVG9vbHMoKXtpZighc2l8fCFzcilyZXR1cm47dmFyIHE9c2kudmFsdWUudHJpbSgpLnRvTG93ZXJDYXNlKCk7aWYoIXRvb2xDYWNoZXx8IXEpe19tc2cocT8nTm8gcmVzdWx0cyBmb3VuZCc6J1N0YXJ0IHR5cGluZyB0byBmaW5kIHRvb2xzJyk7cmV0dXJufVxyXG52YXIgbT10b29sQ2FjaGUuZmlsdGVyKGZ1bmN0aW9uKHQpe3JldHVybiB0Lm5hbWUudG9Mb3dlckNhc2UoKS5pbmRleE9mKHEpPi0xfHwodC5kZXNjJiZ0LmRlc2MudG9Mb3dlckNhc2UoKS5pbmRleE9mKHEpPi0xKX0pXHJcbl9yZXN1bHRzKG0pfVxyXG5mdW5jdGlvbiBjUygpe2lmKGRpYSlkaWEuY2xvc2UoKTtkb2N1bWVudC5xdWVyeVNlbGVjdG9yQWxsKCdbaWRePXNlYXJjaFRvZ2dsZV0nKS5mb3JFYWNoKGZ1bmN0aW9uKGIpe2Iuc2V0QXR0cmlidXRlKCdhcmlhLWV4cGFuZGVkJywnZmFsc2UnKX0pfVxyXG5kb2N1bWVudC5xdWVyeVNlbGVjdG9yQWxsKCdbaWRePXNlYXJjaFRvZ2dsZV0nKS5mb3JFYWNoKGZ1bmN0aW9uKGIpe2Iuc2V0QXR0cmlidXRlKCdhcmlhLWV4cGFuZGVkJywnZmFsc2UnKTtiLmFkZEV2ZW50TGlzdGVuZXIoJ2NsaWNrJyxmdW5jdGlvbigpe29TKCk7Yi5zZXRBdHRyaWJ1dGUoJ2FyaWEtZXhwYW5kZWQnLCd0cnVlJyl9KX0pXHJcbnZhciBoc2k9ZG9jdW1lbnQuZ2V0RWxlbWVudEJ5SWQoJ2hlcm9TZWFyY2hJbnB1dCcpO2Z1bmN0aW9uIG9wZW5Gcm9tSGVybygpe2lmKGRpYSYmZGlhLm9wZW4pcmV0dXJuO3ZhciB2PWhzaT9oc2kudmFsdWU6Jyc7b1MoKTtpZihzaSYmdil7c2kudmFsdWU9djtmaWx0ZXJUb29scygpfWlmKGhzaSl7aHNpLnNldEF0dHJpYnV0ZSgnYXJpYS1leHBhbmRlZCcsJ3RydWUnKTt0cnl7aHNpLmJsdXIoKX1jYXRjaChlKXt9fX1pZihoc2kpe2hzaS5zZXRBdHRyaWJ1dGUoJ2FyaWEtaGFzcG9wdXAnLCdkaWFsb2cnKTtoc2kuc2V0QXR0cmlidXRlKCdhcmlhLWV4cGFuZGVkJywnZmFsc2UnKTtoc2kuYWRkRXZlbnRMaXN0ZW5lcignY2xpY2snLG9wZW5Gcm9tSGVybyk7aHNpLmFkZEV2ZW50TGlzdGVuZXIoJ2tleWRvd24nLGZ1bmN0aW9uKGUpe2lmKGUua2V5PT09J0VudGVyJyl7ZS5wcmV2ZW50RGVmYXVsdCgpO29wZW5Gcm9tSGVybygpfX0pfVxyXG5mdW5jdGlvbiBfaXNFZGl0YWJsZShlbCl7aWYoIWVsfHwhZWwudGFnTmFtZSlyZXR1cm4gZmFsc2U7dmFyIHQ9ZWwudGFnTmFtZS50b0xvd2VyQ2FzZSgpO3JldHVybiB0PT09J2lucHV0J3x8dD09PSd0ZXh0YXJlYSd8fHQ9PT0nc2VsZWN0J3x8ZWwuaXNDb250ZW50RWRpdGFibGU9PT10cnVlfVxyXG5kb2N1bWVudC5hZGRFdmVudExpc3RlbmVyKCdrZXlkb3duJyxmdW5jdGlvbihlKXtpZihlLmtleSE9PScvJ3x8ZS5jdHJsS2V5fHxlLm1ldGFLZXl8fGUuYWx0S2V5KXJldHVybjtpZihkaWEmJmRpYS5vcGVuKXJldHVybjtpZihfaXNFZGl0YWJsZShkb2N1bWVudC5hY3RpdmVFbGVtZW50KSlyZXR1cm47aWYoZG9jdW1lbnQuZ2V0RWxlbWVudEJ5SWQoJ3Rvb2xTZWFyY2hJbnB1dCcpKXJldHVybjtlLnByZXZlbnREZWZhdWx0KCk7b1MoKX0pXHJcbnZhciBzYz1kb2N1bWVudC5nZXRFbGVtZW50QnlJZCgnc2VhcmNoQ2xvc2UnKTtpZihzYylzYy5hZGRFdmVudExpc3RlbmVyKCdjbGljaycsY1MpXHJcbmlmKGRpYSl7ZGlhLmFkZEV2ZW50TGlzdGVuZXIoJ2NsaWNrJyxmdW5jdGlvbihlKXtpZihlLnRhcmdldD09PWRpYSljUygpfSk7ZGlhLmFkZEV2ZW50TGlzdGVuZXIoJ2tleWRvd24nLGZ1bmN0aW9uKGUpe2lmKGUua2V5PT09J0VzY2FwZScpY1MoKX0pO2RpYS5hZGRFdmVudExpc3RlbmVyKCdjbG9zZScsZnVuY3Rpb24oKXtpZihoc2kpaHNpLnNldEF0dHJpYnV0ZSgnYXJpYS1leHBhbmRlZCcsJ2ZhbHNlJyk7ZG9jdW1lbnQucXVlcnlTZWxlY3RvckFsbCgnW2lkXj1zZWFyY2hUb2dnbGVdJykuZm9yRWFjaChmdW5jdGlvbihiKXtiLnNldEF0dHJpYnV0ZSgnYXJpYS1leHBhbmRlZCcsJ2ZhbHNlJyl9KX0pfVxyXG5pZignc2VydmljZVdvcmtlcidpbiBuYXZpZ2F0b3Ipe3ZhciBzd1JlZnJlc2hpbmc9ZmFsc2U7bmF2aWdhdG9yLnNlcnZpY2VXb3JrZXIucmVnaXN0ZXIoJy9zZXJ2aWNlLXdvcmtlcicse3Njb3BlOicvJ30pLnRoZW4oZnVuY3Rpb24ocmVnKXtyZWcuYWRkRXZlbnRMaXN0ZW5lcigndXBkYXRlZm91bmQnLGZ1bmN0aW9uKCl7dmFyIHc9cmVnLmluc3RhbGxpbmc7aWYodyl7dy5hZGRFdmVudExpc3RlbmVyKCdzdGF0ZWNoYW5nZScsZnVuY3Rpb24oKXtpZih3LnN0YXRlPT09J2luc3RhbGxlZCcmJm5hdmlnYXRvci5zZXJ2aWNlV29ya2VyLmNvbnRyb2xsZXIpe3ZhciBtc2c9ZG9jdW1lbnQuY3JlYXRlRWxlbWVudCgnZGl2Jyk7bXNnLmNsYXNzTmFtZT0nZml4ZWQgYm90dG9tLTQgcmlnaHQtNCB6LTUwIGdsYXNzLXN0cm9uZyByb3VuZGVkLXhsIHNoYWRvdy0yeGwgYm9yZGVyIGJvcmRlci1wcmltYXJ5LzIwIGFuaW1hdGUtZmFkZS1pbic7bXNnLnNldEF0dHJpYnV0ZSgncm9sZScsJ2FsZXJ0Jyk7dmFyIGJ0bj1kb2N1bWVudC5jcmVhdGVFbGVtZW50KCdidXR0b24nKTtidG4uY2xhc3NOYW1lPSdmbGV4IGl0ZW1zLWNlbnRlciBnYXAtMiBweC00IHB5LTMgdGV4dC1zbSBmb250LWJvbGQgY3Vyc29yLXBvaW50ZXIgZm9jdXMtdmlzaWJsZTpvdXRsaW5lLTIgZm9jdXMtdmlzaWJsZTpvdXRsaW5lLXByaW1hcnkgcm91bmRlZC14bCc7YnRuLmlubmVySFRNTD0nTmV3IHZlcnNpb24gYXZhaWxhYmxlISA8c3BhbiBjbGFzcz1cInRleHQtcHJpbWFyeSBtbC0xXCI+UmVmcmVzaDwvc3Bhbj4nO2J0bi5hZGRFdmVudExpc3RlbmVyKCdjbGljaycsZnVuY3Rpb24oKXt3LnBvc3RNZXNzYWdlKHthY3Rpb246J3NraXBXYWl0aW5nJ30pO30pO2J0bi5hZGRFdmVudExpc3RlbmVyKCdrZXlkb3duJyxmdW5jdGlvbihlKXtpZihlLmtleT09PSdFbnRlcid8fGUua2V5PT09JyAnKXtlLnByZXZlbnREZWZhdWx0KCk7dy5wb3N0TWVzc2FnZSh7YWN0aW9uOidza2lwV2FpdGluZyd9KX19KTttc2cuYXBwZW5kQ2hpbGQoYnRuKTtkb2N1bWVudC5ib2R5LmFwcGVuZENoaWxkKG1zZyk7YnRuLmZvY3VzKCk7fX0pO319KTt9KS5jYXRjaChmdW5jdGlvbigpe30pfW5hdmlnYXRvci5zZXJ2aWNlV29ya2VyLmFkZEV2ZW50TGlzdGVuZXIoJ2NvbnRyb2xsZXJjaGFuZ2UnLGZ1bmN0aW9uKCl7aWYoc3dSZWZyZXNoaW5nKXJldHVybjtzd1JlZnJlc2hpbmc9dHJ1ZTt3aW5kb3cubG9jYXRpb24ucmVsb2FkKCk7fSlcclxuXHJcbi8qIFx1MjUwMFx1MjUwMCBEaWFsb2cgKyBhY2NvcmRpb24gXHUyNTAwXHUyNTAwICovXHJcbmRvY3VtZW50LmFkZEV2ZW50TGlzdGVuZXIoJ2NsaWNrJyxmdW5jdGlvbihlKXt2YXIgdD1lLnRhcmdldC5jbG9zZXN0KCdbZGF0YS1kaWFsb2ctdHJpZ2dlcl0nKTtpZih0KXt2YXIgaWQ9dC5kYXRhc2V0LmRpYWxvZ1RyaWdnZXIsZGxnPWRvY3VtZW50LmdldEVsZW1lbnRCeUlkKGlkKTtpZihkbGcpe2lmKGRsZy50YWdOYW1lPT09J0RJQUxPRycpZGxnLnNob3dNb2RhbCgpO2Vsc2V7ZGxnLmNsYXNzTGlzdC5yZW1vdmUoJ2hpZGRlbicpO2RsZy5jbGFzc0xpc3QuYWRkKCdmbGV4Jyk7ZG9jdW1lbnQuYm9keS5zdHlsZS5vdmVyZmxvdz0naGlkZGVuJ319cmV0dXJufVxyXG52YXIgY2I9ZS50YXJnZXQuY2xvc2VzdCgnW2RhdGEtZGlhbG9nLWNsb3NlXScpO2lmKGNiKXtjRChjYi5kYXRhc2V0LmRpYWxvZ0Nsb3NlKTtyZXR1cm59XHJcbnZhciBvdj1lLnRhcmdldC5jbG9zZXN0KCdbZGF0YS1kaWFsb2ctb3ZlcmxheV0nKTtpZihvdil7dmFyIGQyPW92LmNsb3Nlc3QoJ1tkYXRhLWRpYWxvZ10nKTtpZihkMiljRChkMi5pZCl9fSlcclxuZG9jdW1lbnQuYWRkRXZlbnRMaXN0ZW5lcigna2V5ZG93bicsZnVuY3Rpb24oZSl7aWYoZS5rZXk9PT0nRXNjYXBlJyl7ZG9jdW1lbnQucXVlcnlTZWxlY3RvckFsbCgnW2RhdGEtZGlhbG9nXTpub3QoLmhpZGRlbiknKS5mb3JFYWNoKGZ1bmN0aW9uKGQpe2NEKGQuaWQpfSl9fSlcclxuZnVuY3Rpb24gY0QoaWQpe3ZhciBkbGc9ZG9jdW1lbnQuZ2V0RWxlbWVudEJ5SWQoaWQpO2lmKGRsZyl7aWYoZGxnLnRhZ05hbWU9PT0nRElBTE9HJylkbGcuY2xvc2UoKTtlbHNle2RsZy5jbGFzc0xpc3QuYWRkKCdoaWRkZW4nKTtkbGcuY2xhc3NMaXN0LnJlbW92ZSgnZmxleCcpO2RvY3VtZW50LmJvZHkuc3R5bGUub3ZlcmZsb3c9Jyd9fX1cclxuZnVuY3Rpb24gdG9nZ2xlQWNjb3JkaW9uKHQpe3ZhciBhYz10LmNsb3Nlc3QoJ1tkYXRhLWFjY29yZGlvbl0nKTtpZighYWMpcmV0dXJuO3ZhciBpdD10LmNsb3Nlc3QoJ1tkYXRhLWFjY29yZGlvbi1pdGVtXScpLGlzT3Blbj1pdD9pdC5kYXRhc2V0Lm9wZW49PT0ndHJ1ZSc6ZmFsc2VcclxuaWYoYWMuZGF0YXNldC5hY2NvcmRpb24hPT0nbXVsdGknKXthYy5xdWVyeVNlbGVjdG9yQWxsKCdbZGF0YS1hY2NvcmRpb24taXRlbV0nKS5mb3JFYWNoKGZ1bmN0aW9uKGkpe2kuZGF0YXNldC5vcGVuPSdmYWxzZSc7dmFyIGM9aS5xdWVyeVNlbGVjdG9yKCdbZGF0YS1hY2NvcmRpb24tY29udGVudF0nKTtpZihjKXtjLnN0eWxlLmRpc3BsYXk9J25vbmUnO2Muc3R5bGUubWF4SGVpZ2h0PScwJ31cclxudmFyIGNoPWkucXVlcnlTZWxlY3RvcignW2RhdGEtYWNjb3JkaW9uLWNoZXZyb25dJyk7aWYoY2gpY2guY2xhc3NMaXN0LnJlbW92ZSgncm90YXRlLTE4MCcpO3ZhciB0cj1pLnF1ZXJ5U2VsZWN0b3IoJ1tkYXRhLWFjY29yZGlvbi10cmlnZ2VyXScpO2lmKHRyKXRyLnNldEF0dHJpYnV0ZSgnYXJpYS1leHBhbmRlZCcsJ2ZhbHNlJyl9KX1cclxuaWYoaXQpe3ZhciBuTz1pc09wZW4/J2ZhbHNlJzondHJ1ZSc7aXQuZGF0YXNldC5vcGVuPW5PO3ZhciBjMj1pdC5xdWVyeVNlbGVjdG9yKCdbZGF0YS1hY2NvcmRpb24tY29udGVudF0nKTtpZihjMil7YzIuc3R5bGUuZGlzcGxheT1uTz09PSd0cnVlJz8nYmxvY2snOidub25lJztjMi5zdHlsZS5tYXhIZWlnaHQ9bk89PT0ndHJ1ZSc/YzIuc2Nyb2xsSGVpZ2h0KydweCc6JzAnfVxyXG52YXIgY2gyPWl0LnF1ZXJ5U2VsZWN0b3IoJ1tkYXRhLWFjY29yZGlvbi1jaGV2cm9uXScpO2lmKGNoMiljaDIuY2xhc3NMaXN0LnRvZ2dsZSgncm90YXRlLTE4MCcsbk89PT0ndHJ1ZScpO3Quc2V0QXR0cmlidXRlKCdhcmlhLWV4cGFuZGVkJyxuTyl9fVxyXG5kb2N1bWVudC5hZGRFdmVudExpc3RlbmVyKCdjbGljaycsZnVuY3Rpb24oZSl7dmFyIHQ9ZS50YXJnZXQuY2xvc2VzdCgnW2RhdGEtYWNjb3JkaW9uLXRyaWdnZXJdJyk7aWYodCl7ZS5wcmV2ZW50RGVmYXVsdCgpO3RvZ2dsZUFjY29yZGlvbih0KX19KVxyXG5kb2N1bWVudC5hZGRFdmVudExpc3RlbmVyKCdrZXlkb3duJyxmdW5jdGlvbihlKXtpZihlLmtleSE9PSdFbnRlcicmJmUua2V5IT09JyAnKXJldHVybjt2YXIgdD1lLnRhcmdldC5jbG9zZXN0KCdbZGF0YS1hY2NvcmRpb24tdHJpZ2dlcl0nKTtpZih0KXtlLnByZXZlbnREZWZhdWx0KCk7dG9nZ2xlQWNjb3JkaW9uKHQpfX0pXHJcbmRvY3VtZW50LnF1ZXJ5U2VsZWN0b3JBbGwoJ1tkYXRhLWFjY29yZGlvbi1pdGVtXVtkYXRhLW9wZW49XCJ0cnVlXCJdJykuZm9yRWFjaChmdW5jdGlvbihpdCl7dmFyIGM9aXQucXVlcnlTZWxlY3RvcignW2RhdGEtYWNjb3JkaW9uLWNvbnRlbnRdJyk7aWYoYyl7Yy5zdHlsZS5kaXNwbGF5PSdibG9jayc7Yy5zdHlsZS5tYXhIZWlnaHQ9Yy5zY3JvbGxIZWlnaHQrJ3B4J31cclxudmFyIGNoPWl0LnF1ZXJ5U2VsZWN0b3IoJ1tkYXRhLWFjY29yZGlvbi1jaGV2cm9uXScpO2lmKGNoKWNoLmNsYXNzTGlzdC5hZGQoJ3JvdGF0ZS0xODAnKX0pXHJcbmRvY3VtZW50LnF1ZXJ5U2VsZWN0b3JBbGwoJy5kcm9wZG93biBidXR0b25bYXJpYS1oYXNwb3B1cD1cInRydWVcIl0nKS5mb3JFYWNoKGZ1bmN0aW9uKGIpe2IuYWRkRXZlbnRMaXN0ZW5lcignY2xpY2snLGZ1bmN0aW9uKCl7dmFyIGQ9Yi5jbG9zZXN0KCcuZHJvcGRvd24nKSxjPWQ/ZC5xdWVyeVNlbGVjdG9yKCcuZHJvcGRvd24tY29udGVudCcpOm51bGw7aWYoYyl7dmFyIG89Yy5zdHlsZS5kaXNwbGF5IT09J2Jsb2NrJztjLnN0eWxlLmRpc3BsYXk9bz8nYmxvY2snOicnO2Iuc2V0QXR0cmlidXRlKCdhcmlhLWV4cGFuZGVkJyxvKX19KX0pXHJcblxyXG4vKiBcdTI1MDBcdTI1MDAgU2Nyb2xsIHJldmVhbCBJbnRlcnNlY3Rpb25PYnNlcnZlciAod2l0aCBuby1KUy9uby1JTyBmYWxsYmFjazogcmV2ZWFsIGFsbCkgXHUyNTAwXHUyNTAwICovXHJcbmlmKCdJbnRlcnNlY3Rpb25PYnNlcnZlcidpbiB3aW5kb3cpe3ZhciBybz1uZXcgSW50ZXJzZWN0aW9uT2JzZXJ2ZXIoZnVuY3Rpb24oZXMpe2VzLmZvckVhY2goZnVuY3Rpb24oZSl7aWYoZS5pc0ludGVyc2VjdGluZyl7ZS50YXJnZXQuY2xhc3NMaXN0LmFkZCgndmlzaWJsZScpO3JvLnVub2JzZXJ2ZShlLnRhcmdldCl9fSl9LHt0aHJlc2hvbGQ6MC4xfSlcclxuZG9jdW1lbnQucXVlcnlTZWxlY3RvckFsbCgnLnJldmVhbCcpLmZvckVhY2goZnVuY3Rpb24oZWwpe3JvLm9ic2VydmUoZWwpfSl9XHJcbmVsc2V7ZG9jdW1lbnQucXVlcnlTZWxlY3RvckFsbCgnLnJldmVhbCcpLmZvckVhY2goZnVuY3Rpb24oZWwpe2VsLmNsYXNzTGlzdC5hZGQoJ3Zpc2libGUnKX0pfVxyXG5cclxuLyogXHUyNTAwXHUyNTAwIExpZ2h0d2VpZ2h0IGFuYWx5dGljcyBcdTI1MDBcdTI1MDAgKi9cclxudmFyIGFuPWRvY3VtZW50LmdldEVsZW1lbnRCeUlkKCdhbmFseXRpY3MtdHJhY2snKTtpZihhbiYmJ3NlbmRCZWFjb24naW4gbmF2aWdhdG9yKXt2YXIgYj1uZXcgQmxvYihbSlNPTi5zdHJpbmdpZnkoe25hbWU6YW4uZGF0YXNldC50b29sfHwncGFnZScsY2F0ZWdvcnk6J3BhZ2Vfdmlldyd9KV0se3R5cGU6J2FwcGxpY2F0aW9uL2pzb24nfSk7bmF2aWdhdG9yLnNlbmRCZWFjb24oJy9hcGkvdHJhY2snLGIpfVxyXG5cclxuXHJcblxyXG4vKiBcdTI1MDBcdTI1MDAgQ1NQLXNhZmUgZGVsZWdhdGVkIGFjdGlvbnMgKHJlcGxhY2VzIGlubGluZSBvbmNsaWNrPVwiLi4uXCIpIFx1MjUwMFx1MjUwMFxyXG4gICBDb3ZlcnM6IG1lbWVfZ2VuZXJhdG9yLCBxcl9nZW5lcmF0b3IsIHNpdGVtYXBfZ2VuZXJhdG9yLCBpbWFnZV9iYWNrZ3JvdW5kX3JlbW92ZXIsXHJcbiAgIGNyeXB0b19mZWFyX2dyZWVkLiBUb29sLWxvY2FsIGVsLm9uY2xpY2s9IHByb3BlcnR5IGFzc2lnbm1lbnRzIGFyZSBrZXB0IGFzLWlzLiAqL1xyXG5kb2N1bWVudC5hZGRFdmVudExpc3RlbmVyKCdjbGljaycsZnVuY3Rpb24oZSl7XHJcbiAgdmFyIGVsPWUudGFyZ2V0JiZlLnRhcmdldC5jbG9zZXN0P2UudGFyZ2V0LmNsb3Nlc3QoJ1tkYXRhLWFjdGlvbl0nKTpudWxsO1xyXG4gIGlmKCFlbClyZXR1cm47XHJcbiAgdmFyIGE9ZWwuZ2V0QXR0cmlidXRlKCdkYXRhLWFjdGlvbicpLHc9d2luZG93O1xyXG4gIGZ1bmN0aW9uIGlkeCgpe3ZhciB2PXBhcnNlSW50KGVsLmdldEF0dHJpYnV0ZSgnZGF0YS1pbmRleCcpLDEwKTtyZXR1cm4gaXNOYU4odik/MDp2fVxyXG4gIGlmKGE9PT0nY2xvc2UtZGlhbG9nJyl7dmFyIHQ9ZWwuZ2V0QXR0cmlidXRlKCdkYXRhLXRhcmdldCcpLGQ9dCYmZG9jdW1lbnQuZ2V0RWxlbWVudEJ5SWQodCk7aWYoZCYmZC5jbG9zZSlkLmNsb3NlKCk7cmV0dXJufVxyXG4gIGlmKGE9PT0nY2xvc2Utem9vbScpe2VsLmNsYXNzTGlzdC5yZW1vdmUoJ29wZW4nKTtyZXR1cm59XHJcbiAgaWYoYT09PSdyZWZyZXNoLWZuZycpe3JldHVybn0gLyogdG9vbCBzY3JpcHQgb3ducyBmZXRjaExpdmUgdmlhICNyZWZyZXNoQnRuIGxpc3RlbmVyICovXHJcbiAgaWYoYT09PSdtZW1lLXByZXNldCcpe2lmKHR5cGVvZiB3LmFwcGx5UHJlc2V0PT09J2Z1bmN0aW9uJyl3LmFwcGx5UHJlc2V0KGVsLmdldEF0dHJpYnV0ZSgnZGF0YS1wcmVzZXQnKSk7cmV0dXJufVxyXG4gIGlmKGE9PT0nbWVtZS1kb3dubG9hZCcpe2lmKHR5cGVvZiB3LmRvd25sb2FkTWVtZT09PSdmdW5jdGlvbicpdy5kb3dubG9hZE1lbWUoKTtyZXR1cm59XHJcbiAgaWYoYT09PSdtZW1lLWNvcHknKXtpZih0eXBlb2Ygdy5jb3B5TWVtZT09PSdmdW5jdGlvbicpdy5jb3B5TWVtZSgpO3JldHVybn1cclxuICBpZihhPT09J21lbWUtY2xlYXItaGlzdCcpe2lmKHR5cGVvZiB3LmNsZWFySGlzdD09PSdmdW5jdGlvbicpdy5jbGVhckhpc3QoKTtyZXR1cm59XHJcbiAgaWYoYT09PSdtZW1lLXJlc3RvcmUtaGlzdCcpe2lmKHR5cGVvZiB3LnJlc3RvcmVIaXN0PT09J2Z1bmN0aW9uJyl3LnJlc3RvcmVIaXN0KGlkeCgpKTtyZXR1cm59XHJcbiAgaWYoYT09PSdtZW1lLWRlbC1oaXN0Jyl7aWYodHlwZW9mIHcuZGVsSGlzdD09PSdmdW5jdGlvbicpdy5kZWxIaXN0KGlkeCgpKTtyZXR1cm59XHJcbiAgaWYoYT09PSdxci1kb3Qtc3R5bGUnKXtpZih0eXBlb2Ygdy5zZXREb3RTdHlsZT09PSdmdW5jdGlvbicpdy5zZXREb3RTdHlsZShlbC5nZXRBdHRyaWJ1dGUoJ2RhdGEtc3R5bGUnKSxlbCk7cmV0dXJufVxyXG4gIGlmKGE9PT0ncXItZXllLXN0eWxlJyl7aWYodHlwZW9mIHcuc2V0RXllU3R5bGU9PT0nZnVuY3Rpb24nKXcuc2V0RXllU3R5bGUoZWwuZ2V0QXR0cmlidXRlKCdkYXRhLXN0eWxlJyksZWwpO3JldHVybn1cclxuICBpZihhPT09J3FyLWNsZWFyLWxvZ28nKXtpZih0eXBlb2Ygdy5jbGVhckxvZ289PT0nZnVuY3Rpb24nKXcuY2xlYXJMb2dvKCk7cmV0dXJufVxyXG4gIGlmKGE9PT0ncXItc2Nhbicpe2lmKHR5cGVvZiB3LnNjYW5RUj09PSdmdW5jdGlvbicpdy5zY2FuUVIoKTtyZXR1cm59XHJcbiAgaWYoYT09PSdxci1maWxsLXNjYW4nKXtpZih0eXBlb2Ygdy5maWxsRnJvbVNjYW49PT0nZnVuY3Rpb24nKXcuZmlsbEZyb21TY2FuKCk7cmV0dXJufVxyXG4gIGlmKGE9PT0ncXItZ2VuJyl7aWYodHlwZW9mIHcuZ2VuPT09J2Z1bmN0aW9uJyl3LmdlbigpO3JldHVybn1cclxuICBpZihhPT09J3FyLWRvd25sb2FkLXBuZycpe2lmKHR5cGVvZiB3LmRvd25sb2FkUE5HPT09J2Z1bmN0aW9uJyl3LmRvd25sb2FkUE5HKCk7cmV0dXJufVxyXG4gIGlmKGE9PT0ncXItZG93bmxvYWQtc3ZnJyl7aWYodHlwZW9mIHcuZG93bmxvYWRTVkc9PT0nZnVuY3Rpb24nKXcuZG93bmxvYWRTVkcoKTtyZXR1cm59XHJcbiAgaWYoYT09PSdxci1jb3B5LXBuZycpe2lmKHR5cGVvZiB3LmNvcHlQTkc9PT0nZnVuY3Rpb24nKXcuY29weVBORygpO3JldHVybn1cclxuICBpZihhPT09J3FyLWNvcHktc3ZnJyl7aWYodHlwZW9mIHcuY29weVNWR0NvZGU9PT0nZnVuY3Rpb24nKXcuY29weVNWR0NvZGUoKTtyZXR1cm59XHJcbiAgaWYoYT09PSdxci1jbGVhci1oaXN0Jyl7aWYodHlwZW9mIHcuY2xlYXJIaXN0PT09J2Z1bmN0aW9uJyl3LmNsZWFySGlzdCgpO3JldHVybn1cclxuICBpZihhPT09J3FyLXJlc3RvcmUtaGlzdCcpe2lmKHR5cGVvZiB3LnJlc3RvcmVIaXN0PT09J2Z1bmN0aW9uJyl3LnJlc3RvcmVIaXN0KGlkeCgpKTtyZXR1cm59XHJcbiAgaWYoYT09PSdxci1hcHBseS1wcmVzZXQnKXtpZih0eXBlb2Ygdy5hcHBseVByZXNldD09PSdmdW5jdGlvbicpdy5hcHBseVByZXNldChlbC5nZXRBdHRyaWJ1dGUoJ2RhdGEtZmcnKSxlbC5nZXRBdHRyaWJ1dGUoJ2RhdGEtYmcnKSk7cmV0dXJufVxyXG59KTtcclxuXHJcbi8qIFx1MjUwMFx1MjUwMCBMZWdhY3kgSG92ZXItSW50ZW50IFByZWZldGNoaW5nIFJlbW92ZWQgKFVzaW5nIFNwZWN1bGF0aW9uIFJ1bGVzIGluc3RlYWQpIFx1MjUwMFx1MjUwMCAqL1xyXG5cclxuLyogXHUyNTAwXHUyNTAwIEhlcm8gbW91c2UtZm9sbG93IGdsb3cgXHUyNTAwXHUyNTAwICovXHJcbnZhciBocz1kb2N1bWVudC5nZXRFbGVtZW50QnlJZCgnaGVyb1NlY3Rpb24nKTtpZihocyl7dmFyIF9yPW51bGwsX3JpZD0hMTtocy5hZGRFdmVudExpc3RlbmVyKCdtb3VzZW1vdmUnLGZ1bmN0aW9uKGUpe2lmKF9yaWQpY2FuY2VsQW5pbWF0aW9uRnJhbWUoX3IpO19yaWQ9ITA7X3I9cmVxdWVzdEFuaW1hdGlvbkZyYW1lKGZ1bmN0aW9uKCl7dmFyIGI9aHMuZ2V0Qm91bmRpbmdDbGllbnRSZWN0KCksbXg9KGUuY2xpZW50WC1iLmxlZnQpL2Iud2lkdGgqMTAwLG15PShlLmNsaWVudFktYi50b3ApL2IuaGVpZ2h0KjEwMDtocy5zdHlsZS5zZXRQcm9wZXJ0eSgnLS1teCcsbXgrJyUnKTtocy5zdHlsZS5zZXRQcm9wZXJ0eSgnLS1teScsbXkrJyUnKTtfcmlkPSExfSl9LHtwYXNzaXZlOiEwfSl9XHJcbn0pKCk7XHJcbiJdLAogICJtYXBwaW5ncyI6ICI7O0FBRUEsR0FBQyxXQUFVO0FBQUM7QUFBYSxVQUFNLFFBQU0sRUFBQyxJQUFJLEdBQUU7QUFBQyxVQUFHO0FBQUMsZUFBTyxhQUFhLFFBQVEsQ0FBQztBQUFBLE1BQUMsUUFBTTtBQUFDLGVBQU87QUFBQSxNQUFJO0FBQUEsSUFBQyxHQUFFLElBQUksR0FBRSxHQUFFO0FBQUMsVUFBRztBQUFDLHFCQUFhLFFBQVEsR0FBRSxDQUFDO0FBQUEsTUFBQyxRQUFNO0FBQUEsTUFBQztBQUFBLElBQUMsR0FBRSxJQUFJLEdBQUU7QUFBQyxVQUFHO0FBQUMscUJBQWEsV0FBVyxDQUFDO0FBQUEsTUFBQyxRQUFNO0FBQUEsTUFBQztBQUFBLElBQUMsRUFBQztBQUFFLFFBQUksT0FBSyxTQUFTO0FBQWdCLGFBQVMsU0FBUyxHQUFFO0FBQUMsV0FBSyxhQUFhLGNBQWEsQ0FBQztBQUFFLFlBQU0sSUFBSSxZQUFXLENBQUM7QUFBQSxJQUFDO0FBQ3BULGFBQVMsaUJBQWlCLGVBQWUsRUFBRSxRQUFRLFNBQVNBLElBQUU7QUFBQyxNQUFBQSxHQUFFLGlCQUFpQixTQUFRLFdBQVU7QUFBQyxZQUFJLElBQUUsS0FBSyxhQUFhLFlBQVksS0FBRztBQUFRLGlCQUFTLE1BQUksVUFBUSxVQUFRLE9BQU87QUFBQSxNQUFDLENBQUM7QUFBQSxJQUFDLENBQUM7QUFDNUwsV0FBTyxXQUFXLDhCQUE4QixFQUFFLGlCQUFpQixVQUFTLFNBQVMsR0FBRTtBQUFDLFVBQUcsQ0FBQyxNQUFNLElBQUksVUFBVSxHQUFFO0FBQUMsaUJBQVMsRUFBRSxVQUFRLFVBQVEsT0FBTztBQUFBLE1BQUM7QUFBQSxJQUFDLENBQUM7QUFDeEosUUFBSSxNQUFJLFNBQVMsZUFBZSxZQUFZLEdBQUUsS0FBRyxTQUFTLGVBQWUsWUFBWTtBQUFFLGFBQVMsS0FBSTtBQUFDLFVBQUksSUFBRSxPQUFPLFVB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
