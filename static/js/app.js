(() => {
  // src/js/app.js
  (function() {
    "use strict";
    var html = document.documentElement;
    function setTheme(t) {
      html.setAttribute("data-theme", t);
      localStorage.setItem("sb-theme", t);
    }
    document.querySelectorAll(".theme-toggle").forEach(function(b2) {
      b2.addEventListener("click", function() {
        var c = html.getAttribute("data-theme") || "night";
        setTheme(c === "night" ? "light" : "night");
      });
    });
    window.matchMedia("(prefers-color-scheme: dark)").addEventListener("change", function(e) {
      if (!localStorage.getItem("sb-theme")) {
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
        if (l.getAttribute("href") === "/tools") l.classList.add("active");
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
          if (sr) sr.innerHTML = '<p class="text-base-content/30 text-center py-4">Could not load tools. Try again later.</p>';
        });
      }
    }
    function filterTools() {
      var q = si.value.trim().toLowerCase();
      if (!toolCache || !q) {
        sr.innerHTML = '<p class="text-base-content/30 text-center py-4">' + (q ? "No results found" : "Start typing to find tools") + "</p>";
        return;
      }
      var m = toolCache.filter(function(t) {
        return t.name.toLowerCase().indexOf(q) > -1 || t.desc && t.desc.toLowerCase().indexOf(q) > -1;
      });
      if (m.length === 0) {
        sr.innerHTML = '<p class="text-base-content/30 text-center py-4">No results found</p>';
        return;
      }
      sr.innerHTML = m.slice(0, 20).map(function(t) {
        return '<a href="' + t.url + `" class="flex items-center justify-between p-3 rounded-xl hover:glass transition-all duration-200" onclick="document.getElementById('searchDialog').close()"><div><div class="font-semibold text-sm">` + t.name + '</div><div class="text-xs text-base-content/40">' + t.category + '</div></div><svg class="w-4 h-4 text-base-content/20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M5 12h14"/><path d="m12 5 7 7-7 7"/></svg></a>';
      }).join("");
    }
    function cS() {
      if (dia) dia.close();
    }
    document.querySelectorAll("[id^=searchToggle]").forEach(function(b2) {
      b2.addEventListener("click", oS);
    });
    var hsi = document.getElementById("heroSearchInput");
    if (hsi) {
      hsi.addEventListener("focus", function() {
        if (!dia.open) oS();
      });
    }
    var sc = document.getElementById("searchClose");
    if (sc) sc.addEventListener("click", cS);
    if (dia) {
      dia.addEventListener("click", function(e) {
        if (e.target === dia) cS();
      });
      dia.addEventListener("keydown", function(e) {
        if (e.key === "Escape") cS();
      });
    }
    var eb = document.getElementById("exploreToolsBtn");
    if (eb) {
      eb.addEventListener("click", function() {
        var d = document.getElementById("mobileDrawer");
        if (d) d.checked = true;
      });
    }
    if ("serviceWorker" in navigator) {
      var swRefreshing = false;
      navigator.serviceWorker.register("/sw.js", { scope: "/" }).then(function(reg) {
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
    }
    var an = document.getElementById("analytics-track");
    if (an && "sendBeacon" in navigator) {
      var b = new Blob([JSON.stringify({ name: an.dataset.tool || "page", category: "page_view" })], { type: "application/json" });
      navigator.sendBeacon("/api/track", b);
    }
    var prefetched = /* @__PURE__ */ new Set();
    document.addEventListener("mouseover", function(e) {
      var t = e.target.closest("a");
      if (t && t.href && t.href.startsWith(window.location.origin) && !t.hash && !prefetched.has(t.href)) {
        var timer = setTimeout(function() {
          prefetched.add(t.href);
          var link = document.createElement("link");
          link.rel = "prefetch";
          link.href = t.href;
          document.head.appendChild(link);
        }, 60);
        t.addEventListener("mouseout", function() {
          clearTimeout(timer);
        }, { once: true });
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
//# sourceMappingURL=data:application/json;base64,ewogICJ2ZXJzaW9uIjogMywKICAic291cmNlcyI6IFsiLi4vLi4vc3JjL2pzL2FwcC5qcyJdLAogICJzb3VyY2VzQ29udGVudCI6IFsiLyogXHUyNTAwXHUyNTAwIFN0b3J5QnJhaW4gQUk6IGFwcC5qcyAoYmFzZS5qcyArIHVpLWluaXQuanMgYnVuZGxlZCkgXHUyNTAwXHUyNTAwICovXG4oZnVuY3Rpb24oKXsndXNlIHN0cmljdCc7dmFyIGh0bWw9ZG9jdW1lbnQuZG9jdW1lbnRFbGVtZW50O2Z1bmN0aW9uIHNldFRoZW1lKHQpe2h0bWwuc2V0QXR0cmlidXRlKCdkYXRhLXRoZW1lJyx0KTtsb2NhbFN0b3JhZ2Uuc2V0SXRlbSgnc2ItdGhlbWUnLHQpfVxuZG9jdW1lbnQucXVlcnlTZWxlY3RvckFsbCgnLnRoZW1lLXRvZ2dsZScpLmZvckVhY2goZnVuY3Rpb24oYil7Yi5hZGRFdmVudExpc3RlbmVyKCdjbGljaycsZnVuY3Rpb24oKXt2YXIgYz1odG1sLmdldEF0dHJpYnV0ZSgnZGF0YS10aGVtZScpfHwnbmlnaHQnO3NldFRoZW1lKGM9PT0nbmlnaHQnPydsaWdodCc6J25pZ2h0Jyl9KX0pXG53aW5kb3cubWF0Y2hNZWRpYSgnKHByZWZlcnMtY29sb3Itc2NoZW1lOiBkYXJrKScpLmFkZEV2ZW50TGlzdGVuZXIoJ2NoYW5nZScsZnVuY3Rpb24oZSl7aWYoIWxvY2FsU3RvcmFnZS5nZXRJdGVtKCdzYi10aGVtZScpKXtzZXRUaGVtZShlLm1hdGNoZXM/J25pZ2h0JzonbGlnaHQnKX19KVxudmFyIG5hdj1kb2N1bWVudC5nZXRFbGVtZW50QnlJZCgnc2l0ZU5hdmJhcicpLHNoPWRvY3VtZW50LmdldEVsZW1lbnRCeUlkKCdzaXRlSGVhZGVyJyk7ZnVuY3Rpb24gaFMoKXt2YXIgcz13aW5kb3cuc2Nyb2xsWT4yMDtpZihuYXYpbmF2LmNsYXNzTGlzdC50b2dnbGUoJ3NoYWRvdy1zbScscyk7aWYoc2gpc2guY2xhc3NMaXN0LnRvZ2dsZSgnc2Nyb2xsZWQnLHMpfVxud2luZG93LmFkZEV2ZW50TGlzdGVuZXIoJ3Njcm9sbCcsaFMse3Bhc3NpdmU6dHJ1ZX0pO2hTKClcblxuLyogXHUyNTAwXHUyNTAwIE5hdiBhY3RpdmUgc3RhdGUgZm9yIHRvb2wgcGFnZXMgXHUyNTAwXHUyNTAwICovXG5pZih3aW5kb3cubG9jYXRpb24ucGF0aG5hbWUuaW5kZXhPZignL3Rvb2wvJyk9PT0wKXtkb2N1bWVudC5xdWVyeVNlbGVjdG9yQWxsKCcubmF2LWxpbmsnKS5mb3JFYWNoKGZ1bmN0aW9uKGwpe2lmKGwuZ2V0QXR0cmlidXRlKCdocmVmJyk9PT0nL3Rvb2xzJylsLmNsYXNzTGlzdC5hZGQoJ2FjdGl2ZScpfSl9XG5cbi8qIFx1MjUwMFx1MjUwMCBUaWx0IGNhcmRzIFx1MjUwMFx1MjUwMCAqL1xuZG9jdW1lbnQucXVlcnlTZWxlY3RvckFsbCgnLnRpbHQtY2FyZFtkYXRhLXRpbHRdJykuZm9yRWFjaChmdW5jdGlvbihjKXtjLmFkZEV2ZW50TGlzdGVuZXIoJ21vdXNlbW92ZScsZnVuY3Rpb24oZSl7dmFyIHI9dGhpcy5nZXRCb3VuZGluZ0NsaWVudFJlY3QoKSx4PShlLmNsaWVudFgtci5sZWZ0KS9yLndpZHRoLTAuNSx5PShlLmNsaWVudFktci50b3ApL3IuaGVpZ2h0LTAuNTt0aGlzLnN0eWxlLnNldFByb3BlcnR5KCctLXRpbHQteCcsKC15KjEyKSsnZGVnJyk7dGhpcy5zdHlsZS5zZXRQcm9wZXJ0eSgnLS10aWx0LXknLCh4KjEyKSsnZGVnJyl9KTtjLmFkZEV2ZW50TGlzdGVuZXIoJ21vdXNlbGVhdmUnLGZ1bmN0aW9uKCl7dGhpcy5zdHlsZS5zZXRQcm9wZXJ0eSgnLS10aWx0LXgnLCcwZGVnJyk7dGhpcy5zdHlsZS5zZXRQcm9wZXJ0eSgnLS10aWx0LXknLCcwZGVnJyl9KX0pXG5cbi8qIFx1MjUwMFx1MjUwMCBCdXR0b24gcmlwcGxlIFx1MjUwMFx1MjUwMCAqL1xuZG9jdW1lbnQucXVlcnlTZWxlY3RvckFsbCgnLmJ0bi1yaXBwbGUnKS5mb3JFYWNoKGZ1bmN0aW9uKGIpe2IuYWRkRXZlbnRMaXN0ZW5lcignbW91c2Vkb3duJyxmdW5jdGlvbihlKXt2YXIgcj10aGlzLmdldEJvdW5kaW5nQ2xpZW50UmVjdCgpO3RoaXMuc3R5bGUuc2V0UHJvcGVydHkoJy0tcmlwcGxlLXgnLCgoZS5jbGllbnRYLXIubGVmdCkvci53aWR0aCoxMDApKyclJyk7dGhpcy5zdHlsZS5zZXRQcm9wZXJ0eSgnLS1yaXBwbGUteScsKChlLmNsaWVudFktci50b3ApL3IuaGVpZ2h0KjEwMCkrJyUnKX0pfSlcbnZhciBkaWE9ZG9jdW1lbnQuZ2V0RWxlbWVudEJ5SWQoJ3NlYXJjaERpYWxvZycpLHNpPWRvY3VtZW50LmdldEVsZW1lbnRCeUlkKCdzZWFyY2hJbnB1dCcpLHNyPWRvY3VtZW50LmdldEVsZW1lbnRCeUlkKCdzZWFyY2hSZXN1bHRzJyksdG9vbENhY2hlPW51bGw7XG5mdW5jdGlvbiBvUygpe1xuICBpZighZGlhKXJldHVybjtcbiAgZGlhLnNob3dNb2RhbCgpO1xuICBpZihzaSlzaS5mb2N1cygpO1xuICBpZighdG9vbENhY2hlKXtcbiAgICBmZXRjaCgnL2FwaS90b29scy9jYXRhbG9nJykudGhlbihmdW5jdGlvbihyKXtyZXR1cm4gci5qc29uKCl9KS50aGVuKGZ1bmN0aW9uKGQpe3Rvb2xDYWNoZT1kO2ZpbHRlclRvb2xzKCl9KS5jYXRjaChmdW5jdGlvbigpe2lmKHNyKXNyLmlubmVySFRNTD0nPHAgY2xhc3M9XCJ0ZXh0LWJhc2UtY29udGVudC8zMCB0ZXh0LWNlbnRlciBweS00XCI+Q291bGQgbm90IGxvYWQgdG9vbHMuIFRyeSBhZ2FpbiBsYXRlci48L3A+J30pXG4gIH1cbn1cbmZ1bmN0aW9uIGZpbHRlclRvb2xzKCl7dmFyIHE9c2kudmFsdWUudHJpbSgpLnRvTG93ZXJDYXNlKCk7aWYoIXRvb2xDYWNoZXx8IXEpe3NyLmlubmVySFRNTD0nPHAgY2xhc3M9XCJ0ZXh0LWJhc2UtY29udGVudC8zMCB0ZXh0LWNlbnRlciBweS00XCI+JysocT8nTm8gcmVzdWx0cyBmb3VuZCc6J1N0YXJ0IHR5cGluZyB0byBmaW5kIHRvb2xzJykrJzwvcD4nO3JldHVybn1cbnZhciBtPXRvb2xDYWNoZS5maWx0ZXIoZnVuY3Rpb24odCl7cmV0dXJuIHQubmFtZS50b0xvd2VyQ2FzZSgpLmluZGV4T2YocSk+LTF8fCh0LmRlc2MmJnQuZGVzYy50b0xvd2VyQ2FzZSgpLmluZGV4T2YocSk+LTEpfSlcbmlmKG0ubGVuZ3RoPT09MCl7c3IuaW5uZXJIVE1MPSc8cCBjbGFzcz1cInRleHQtYmFzZS1jb250ZW50LzMwIHRleHQtY2VudGVyIHB5LTRcIj5ObyByZXN1bHRzIGZvdW5kPC9wPic7cmV0dXJufVxuc3IuaW5uZXJIVE1MPW0uc2xpY2UoMCwyMCkubWFwKGZ1bmN0aW9uKHQpe3JldHVybic8YSBocmVmPVwiJyt0LnVybCsnXCIgY2xhc3M9XCJmbGV4IGl0ZW1zLWNlbnRlciBqdXN0aWZ5LWJldHdlZW4gcC0zIHJvdW5kZWQteGwgaG92ZXI6Z2xhc3MgdHJhbnNpdGlvbi1hbGwgZHVyYXRpb24tMjAwXCIgb25jbGljaz1cImRvY3VtZW50LmdldEVsZW1lbnRCeUlkKFxcJ3NlYXJjaERpYWxvZ1xcJykuY2xvc2UoKVwiPjxkaXY+PGRpdiBjbGFzcz1cImZvbnQtc2VtaWJvbGQgdGV4dC1zbVwiPicrdC5uYW1lKyc8L2Rpdj48ZGl2IGNsYXNzPVwidGV4dC14cyB0ZXh0LWJhc2UtY29udGVudC80MFwiPicrdC5jYXRlZ29yeSsnPC9kaXY+PC9kaXY+PHN2ZyBjbGFzcz1cInctNCBoLTQgdGV4dC1iYXNlLWNvbnRlbnQvMjBcIiB2aWV3Qm94PVwiMCAwIDI0IDI0XCIgZmlsbD1cIm5vbmVcIiBzdHJva2U9XCJjdXJyZW50Q29sb3JcIiBzdHJva2Utd2lkdGg9XCIyXCI+PHBhdGggZD1cIk01IDEyaDE0XCIvPjxwYXRoIGQ9XCJtMTIgNSA3IDctNyA3XCIvPjwvc3ZnPjwvYT4nfSkuam9pbignJyl9XG5mdW5jdGlvbiBjUygpe2lmKGRpYSlkaWEuY2xvc2UoKX1cbmRvY3VtZW50LnF1ZXJ5U2VsZWN0b3JBbGwoJ1tpZF49c2VhcmNoVG9nZ2xlXScpLmZvckVhY2goZnVuY3Rpb24oYil7Yi5hZGRFdmVudExpc3RlbmVyKCdjbGljaycsb1MpfSlcbnZhciBoc2k9ZG9jdW1lbnQuZ2V0RWxlbWVudEJ5SWQoJ2hlcm9TZWFyY2hJbnB1dCcpO2lmKGhzaSl7aHNpLmFkZEV2ZW50TGlzdGVuZXIoJ2ZvY3VzJyxmdW5jdGlvbigpe2lmKCFkaWEub3BlbilvUygpfSl9XG52YXIgc2M9ZG9jdW1lbnQuZ2V0RWxlbWVudEJ5SWQoJ3NlYXJjaENsb3NlJyk7aWYoc2Mpc2MuYWRkRXZlbnRMaXN0ZW5lcignY2xpY2snLGNTKVxuaWYoZGlhKXtkaWEuYWRkRXZlbnRMaXN0ZW5lcignY2xpY2snLGZ1bmN0aW9uKGUpe2lmKGUudGFyZ2V0PT09ZGlhKWNTKCl9KTtkaWEuYWRkRXZlbnRMaXN0ZW5lcigna2V5ZG93bicsZnVuY3Rpb24oZSl7aWYoZS5rZXk9PT0nRXNjYXBlJyljUygpfSl9XG52YXIgZWI9ZG9jdW1lbnQuZ2V0RWxlbWVudEJ5SWQoJ2V4cGxvcmVUb29sc0J0bicpO2lmKGViKXtlYi5hZGRFdmVudExpc3RlbmVyKCdjbGljaycsZnVuY3Rpb24oKXt2YXIgZD1kb2N1bWVudC5nZXRFbGVtZW50QnlJZCgnbW9iaWxlRHJhd2VyJyk7aWYoZClkLmNoZWNrZWQ9dHJ1ZX0pfVxuaWYoJ3NlcnZpY2VXb3JrZXInaW4gbmF2aWdhdG9yKXt2YXIgc3dSZWZyZXNoaW5nPWZhbHNlO25hdmlnYXRvci5zZXJ2aWNlV29ya2VyLnJlZ2lzdGVyKCcvc3cuanMnLHtzY29wZTonLyd9KS50aGVuKGZ1bmN0aW9uKHJlZyl7cmVnLmFkZEV2ZW50TGlzdGVuZXIoJ3VwZGF0ZWZvdW5kJyxmdW5jdGlvbigpe3ZhciB3PXJlZy5pbnN0YWxsaW5nO2lmKHcpe3cuYWRkRXZlbnRMaXN0ZW5lcignc3RhdGVjaGFuZ2UnLGZ1bmN0aW9uKCl7aWYody5zdGF0ZT09PSdpbnN0YWxsZWQnJiZuYXZpZ2F0b3Iuc2VydmljZVdvcmtlci5jb250cm9sbGVyKXt2YXIgbXNnPWRvY3VtZW50LmNyZWF0ZUVsZW1lbnQoJ2RpdicpO21zZy5jbGFzc05hbWU9J2ZpeGVkIGJvdHRvbS00IHJpZ2h0LTQgei01MCBnbGFzcy1zdHJvbmcgcm91bmRlZC14bCBzaGFkb3ctMnhsIGJvcmRlciBib3JkZXItcHJpbWFyeS8yMCBhbmltYXRlLWZhZGUtaW4nO21zZy5zZXRBdHRyaWJ1dGUoJ3JvbGUnLCdhbGVydCcpO3ZhciBidG49ZG9jdW1lbnQuY3JlYXRlRWxlbWVudCgnYnV0dG9uJyk7YnRuLmNsYXNzTmFtZT0nZmxleCBpdGVtcy1jZW50ZXIgZ2FwLTIgcHgtNCBweS0zIHRleHQtc20gZm9udC1ib2xkIGN1cnNvci1wb2ludGVyIGZvY3VzLXZpc2libGU6b3V0bGluZS0yIGZvY3VzLXZpc2libGU6b3V0bGluZS1wcmltYXJ5IHJvdW5kZWQteGwnO2J0bi5pbm5lckhUTUw9J05ldyB2ZXJzaW9uIGF2YWlsYWJsZSEgPHNwYW4gY2xhc3M9XCJ0ZXh0LXByaW1hcnkgbWwtMVwiPlJlZnJlc2g8L3NwYW4+JztidG4uYWRkRXZlbnRMaXN0ZW5lcignY2xpY2snLGZ1bmN0aW9uKCl7dy5wb3N0TWVzc2FnZSh7YWN0aW9uOidza2lwV2FpdGluZyd9KTt9KTtidG4uYWRkRXZlbnRMaXN0ZW5lcigna2V5ZG93bicsZnVuY3Rpb24oZSl7aWYoZS5rZXk9PT0nRW50ZXInfHxlLmtleT09PScgJyl7ZS5wcmV2ZW50RGVmYXVsdCgpO3cucG9zdE1lc3NhZ2Uoe2FjdGlvbjonc2tpcFdhaXRpbmcnfSl9fSk7bXNnLmFwcGVuZENoaWxkKGJ0bik7ZG9jdW1lbnQuYm9keS5hcHBlbmRDaGlsZChtc2cpO2J0bi5mb2N1cygpO319KTt9fSk7fSkuY2F0Y2goZnVuY3Rpb24oKXt9KX1uYXZpZ2F0b3Iuc2VydmljZVdvcmtlci5hZGRFdmVudExpc3RlbmVyKCdjb250cm9sbGVyY2hhbmdlJyxmdW5jdGlvbigpe2lmKHN3UmVmcmVzaGluZylyZXR1cm47c3dSZWZyZXNoaW5nPXRydWU7d2luZG93LmxvY2F0aW9uLnJlbG9hZCgpO30pXG5cbi8qIFx1MjUwMFx1MjUwMCBEaWFsb2cgKyBhY2NvcmRpb24gXHUyNTAwXHUyNTAwICovXG5kb2N1bWVudC5hZGRFdmVudExpc3RlbmVyKCdjbGljaycsZnVuY3Rpb24oZSl7dmFyIHQ9ZS50YXJnZXQuY2xvc2VzdCgnW2RhdGEtZGlhbG9nLXRyaWdnZXJdJyk7aWYodCl7dmFyIGlkPXQuZGF0YXNldC5kaWFsb2dUcmlnZ2VyLGRsZz1kb2N1bWVudC5nZXRFbGVtZW50QnlJZChpZCk7aWYoZGxnKXtpZihkbGcudGFnTmFtZT09PSdESUFMT0cnKWRsZy5zaG93TW9kYWwoKTtlbHNle2RsZy5jbGFzc0xpc3QucmVtb3ZlKCdoaWRkZW4nKTtkbGcuY2xhc3NMaXN0LmFkZCgnZmxleCcpO2RvY3VtZW50LmJvZHkuc3R5bGUub3ZlcmZsb3c9J2hpZGRlbid9fXJldHVybn1cbnZhciBjYj1lLnRhcmdldC5jbG9zZXN0KCdbZGF0YS1kaWFsb2ctY2xvc2VdJyk7aWYoY2Ipe2NEKGNiLmRhdGFzZXQuZGlhbG9nQ2xvc2UpO3JldHVybn1cbnZhciBvdj1lLnRhcmdldC5jbG9zZXN0KCdbZGF0YS1kaWFsb2ctb3ZlcmxheV0nKTtpZihvdil7dmFyIGQyPW92LmNsb3Nlc3QoJ1tkYXRhLWRpYWxvZ10nKTtpZihkMiljRChkMi5pZCl9fSlcbmRvY3VtZW50LmFkZEV2ZW50TGlzdGVuZXIoJ2tleWRvd24nLGZ1bmN0aW9uKGUpe2lmKGUua2V5PT09J0VzY2FwZScpe2RvY3VtZW50LnF1ZXJ5U2VsZWN0b3JBbGwoJ1tkYXRhLWRpYWxvZ106bm90KC5oaWRkZW4pJykuZm9yRWFjaChmdW5jdGlvbihkKXtjRChkLmlkKX0pfX0pXG5mdW5jdGlvbiBjRChpZCl7dmFyIGRsZz1kb2N1bWVudC5nZXRFbGVtZW50QnlJZChpZCk7aWYoZGxnKXtpZihkbGcudGFnTmFtZT09PSdESUFMT0cnKWRsZy5jbG9zZSgpO2Vsc2V7ZGxnLmNsYXNzTGlzdC5hZGQoJ2hpZGRlbicpO2RsZy5jbGFzc0xpc3QucmVtb3ZlKCdmbGV4Jyk7ZG9jdW1lbnQuYm9keS5zdHlsZS5vdmVyZmxvdz0nJ319fVxuZnVuY3Rpb24gdG9nZ2xlQWNjb3JkaW9uKHQpe3ZhciBhYz10LmNsb3Nlc3QoJ1tkYXRhLWFjY29yZGlvbl0nKTtpZighYWMpcmV0dXJuO3ZhciBpdD10LmNsb3Nlc3QoJ1tkYXRhLWFjY29yZGlvbi1pdGVtXScpLGlzT3Blbj1pdD9pdC5kYXRhc2V0Lm9wZW49PT0ndHJ1ZSc6ZmFsc2VcbmlmKGFjLmRhdGFzZXQuYWNjb3JkaW9uIT09J211bHRpJyl7YWMucXVlcnlTZWxlY3RvckFsbCgnW2RhdGEtYWNjb3JkaW9uLWl0ZW1dJykuZm9yRWFjaChmdW5jdGlvbihpKXtpLmRhdGFzZXQub3Blbj0nZmFsc2UnO3ZhciBjPWkucXVlcnlTZWxlY3RvcignW2RhdGEtYWNjb3JkaW9uLWNvbnRlbnRdJyk7aWYoYyl7Yy5zdHlsZS5kaXNwbGF5PSdub25lJztjLnN0eWxlLm1heEhlaWdodD0nMCd9XG52YXIgY2g9aS5xdWVyeVNlbGVjdG9yKCdbZGF0YS1hY2NvcmRpb24tY2hldnJvbl0nKTtpZihjaCljaC5jbGFzc0xpc3QucmVtb3ZlKCdyb3RhdGUtMTgwJyk7dmFyIHRyPWkucXVlcnlTZWxlY3RvcignW2RhdGEtYWNjb3JkaW9uLXRyaWdnZXJdJyk7aWYodHIpdHIuc2V0QXR0cmlidXRlKCdhcmlhLWV4cGFuZGVkJywnZmFsc2UnKX0pfVxuaWYoaXQpe3ZhciBuTz1pc09wZW4/J2ZhbHNlJzondHJ1ZSc7aXQuZGF0YXNldC5vcGVuPW5PO3ZhciBjMj1pdC5xdWVyeVNlbGVjdG9yKCdbZGF0YS1hY2NvcmRpb24tY29udGVudF0nKTtpZihjMil7YzIuc3R5bGUuZGlzcGxheT1uTz09PSd0cnVlJz8nYmxvY2snOidub25lJztjMi5zdHlsZS5tYXhIZWlnaHQ9bk89PT0ndHJ1ZSc/YzIuc2Nyb2xsSGVpZ2h0KydweCc6JzAnfVxudmFyIGNoMj1pdC5xdWVyeVNlbGVjdG9yKCdbZGF0YS1hY2NvcmRpb24tY2hldnJvbl0nKTtpZihjaDIpY2gyLmNsYXNzTGlzdC50b2dnbGUoJ3JvdGF0ZS0xODAnLG5PPT09J3RydWUnKTt0LnNldEF0dHJpYnV0ZSgnYXJpYS1leHBhbmRlZCcsbk8pfX1cbmRvY3VtZW50LmFkZEV2ZW50TGlzdGVuZXIoJ2NsaWNrJyxmdW5jdGlvbihlKXt2YXIgdD1lLnRhcmdldC5jbG9zZXN0KCdbZGF0YS1hY2NvcmRpb24tdHJpZ2dlcl0nKTtpZih0KXtlLnByZXZlbnREZWZhdWx0KCk7dG9nZ2xlQWNjb3JkaW9uKHQpfX0pXG5kb2N1bWVudC5hZGRFdmVudExpc3RlbmVyKCdrZXlkb3duJyxmdW5jdGlvbihlKXtpZihlLmtleSE9PSdFbnRlcicmJmUua2V5IT09JyAnKXJldHVybjt2YXIgdD1lLnRhcmdldC5jbG9zZXN0KCdbZGF0YS1hY2NvcmRpb24tdHJpZ2dlcl0nKTtpZih0KXtlLnByZXZlbnREZWZhdWx0KCk7dG9nZ2xlQWNjb3JkaW9uKHQpfX0pXG5kb2N1bWVudC5xdWVyeVNlbGVjdG9yQWxsKCdbZGF0YS1hY2NvcmRpb24taXRlbV1bZGF0YS1vcGVuPVwidHJ1ZVwiXScpLmZvckVhY2goZnVuY3Rpb24oaXQpe3ZhciBjPWl0LnF1ZXJ5U2VsZWN0b3IoJ1tkYXRhLWFjY29yZGlvbi1jb250ZW50XScpO2lmKGMpe2Muc3R5bGUuZGlzcGxheT0nYmxvY2snO2Muc3R5bGUubWF4SGVpZ2h0PWMuc2Nyb2xsSGVpZ2h0KydweCd9XG52YXIgY2g9aXQucXVlcnlTZWxlY3RvcignW2RhdGEtYWNjb3JkaW9uLWNoZXZyb25dJyk7aWYoY2gpY2guY2xhc3NMaXN0LmFkZCgncm90YXRlLTE4MCcpfSlcbmRvY3VtZW50LnF1ZXJ5U2VsZWN0b3JBbGwoJy5kcm9wZG93biBidXR0b25bYXJpYS1oYXNwb3B1cD1cInRydWVcIl0nKS5mb3JFYWNoKGZ1bmN0aW9uKGIpe2IuYWRkRXZlbnRMaXN0ZW5lcignY2xpY2snLGZ1bmN0aW9uKCl7dmFyIGQ9Yi5jbG9zZXN0KCcuZHJvcGRvd24nKSxjPWQ/ZC5xdWVyeVNlbGVjdG9yKCcuZHJvcGRvd24tY29udGVudCcpOm51bGw7aWYoYyl7dmFyIG89Yy5zdHlsZS5kaXNwbGF5IT09J2Jsb2NrJztjLnN0eWxlLmRpc3BsYXk9bz8nYmxvY2snOicnO2Iuc2V0QXR0cmlidXRlKCdhcmlhLWV4cGFuZGVkJyxvKX19KX0pXG5cbi8qIFx1MjUwMFx1MjUwMCBTY3JvbGwgcmV2ZWFsIEludGVyc2VjdGlvbk9ic2VydmVyIFx1MjUwMFx1MjUwMCAqL1xuaWYoJ0ludGVyc2VjdGlvbk9ic2VydmVyJ2luIHdpbmRvdyl7dmFyIHJvPW5ldyBJbnRlcnNlY3Rpb25PYnNlcnZlcihmdW5jdGlvbihlcyl7ZXMuZm9yRWFjaChmdW5jdGlvbihlKXtpZihlLmlzSW50ZXJzZWN0aW5nKXtlLnRhcmdldC5jbGFzc0xpc3QuYWRkKCd2aXNpYmxlJyk7cm8udW5vYnNlcnZlKGUudGFyZ2V0KX19KX0se3RocmVzaG9sZDowLjF9KVxuZG9jdW1lbnQucXVlcnlTZWxlY3RvckFsbCgnLnJldmVhbCcpLmZvckVhY2goZnVuY3Rpb24oZWwpe3JvLm9ic2VydmUoZWwpfSl9XG5cbi8qIFx1MjUwMFx1MjUwMCBMaWdodHdlaWdodCBhbmFseXRpY3MgXHUyNTAwXHUyNTAwICovXG52YXIgYW49ZG9jdW1lbnQuZ2V0RWxlbWVudEJ5SWQoJ2FuYWx5dGljcy10cmFjaycpO2lmKGFuJiYnc2VuZEJlYWNvbidpbiBuYXZpZ2F0b3Ipe3ZhciBiPW5ldyBCbG9iKFtKU09OLnN0cmluZ2lmeSh7bmFtZTphbi5kYXRhc2V0LnRvb2x8fCdwYWdlJyxjYXRlZ29yeToncGFnZV92aWV3J30pXSx7dHlwZTonYXBwbGljYXRpb24vanNvbid9KTtuYXZpZ2F0b3Iuc2VuZEJlYWNvbignL2FwaS90cmFjaycsYil9XG5cblxuXG4vKiBcdTI1MDBcdTI1MDAgSG92ZXItSW50ZW50IFByZWZldGNoaW5nIFx1MjUwMFx1MjUwMCAqL1xudmFyIHByZWZldGNoZWQgPSBuZXcgU2V0KCk7XG5kb2N1bWVudC5hZGRFdmVudExpc3RlbmVyKCdtb3VzZW92ZXInLCBmdW5jdGlvbihlKSB7XG4gIHZhciB0ID0gZS50YXJnZXQuY2xvc2VzdCgnYScpO1xuICBpZiAodCAmJiB0LmhyZWYgJiYgdC5ocmVmLnN0YXJ0c1dpdGgod2luZG93LmxvY2F0aW9uLm9yaWdpbikgJiYgIXQuaGFzaCAmJiAhcHJlZmV0Y2hlZC5oYXModC5ocmVmKSkge1xuICAgIHZhciB0aW1lciA9IHNldFRpbWVvdXQoZnVuY3Rpb24oKSB7XG4gICAgICBwcmVmZXRjaGVkLmFkZCh0LmhyZWYpO1xuICAgICAgdmFyIGxpbmsgPSBkb2N1bWVudC5jcmVhdGVFbGVtZW50KCdsaW5rJyk7XG4gICAgICBsaW5rLnJlbCA9ICdwcmVmZXRjaCc7XG4gICAgICBsaW5rLmhyZWYgPSB0LmhyZWY7XG4gICAgICBkb2N1bWVudC5oZWFkLmFwcGVuZENoaWxkKGxpbmspO1xuICAgIH0sIDYwKTtcbiAgICB0LmFkZEV2ZW50TGlzdGVuZXIoJ21vdXNlb3V0JywgZnVuY3Rpb24oKSB7IGNsZWFyVGltZW91dCh0aW1lcik7IH0sIHsgb25jZTogdHJ1ZSB9KTtcbiAgfVxufSk7XG5cbi8qIFx1MjUwMFx1MjUwMCBIZXJvIG1vdXNlLWZvbGxvdyBnbG93IFx1MjUwMFx1MjUwMCAqL1xudmFyIGhzPWRvY3VtZW50LmdldEVsZW1lbnRCeUlkKCdoZXJvU2VjdGlvbicpO2lmKGhzKXt2YXIgX3I9bnVsbCxfcmlkPSExO2hzLmFkZEV2ZW50TGlzdGVuZXIoJ21vdXNlbW92ZScsZnVuY3Rpb24oZSl7aWYoX3JpZCljYW5jZWxBbmltYXRpb25GcmFtZShfcik7X3JpZD0hMDtfcj1yZXF1ZXN0QW5pbWF0aW9uRnJhbWUoZnVuY3Rpb24oKXt2YXIgYj1ocy5nZXRCb3VuZGluZ0NsaWVudFJlY3QoKSxteD0oZS5jbGllbnRYLWIubGVmdCkvYi53aWR0aCoxMDAsbXk9KGUuY2xpZW50WS1iLnRvcCkvYi5oZWlnaHQqMTAwO2hzLnN0eWxlLnNldFByb3BlcnR5KCctLW14JyxteCsnJScpO2hzLnN0eWxlLnNldFBy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
