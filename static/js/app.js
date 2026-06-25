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
    var dia = document.getElementById("searchDialog"), si = document.getElementById("searchInput");
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
    function cS() {
      if (dia) dia.close();
    }
    document.querySelectorAll("[id^=searchToggle]").forEach(function(b2) {
      b2.addEventListener("click", oS);
    });
    var hsi = document.getElementById("heroSearchInput");
    if (hsi) {
      hsi.addEventListener("focus", oS);
      hsi.addEventListener("click", oS);
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
    var sd = document.getElementById("searchDialog"), si = document.getElementById("searchInput"), sr = document.getElementById("searchResults"), toolCache = null;
    if (sd && si && sr) {
      sd.addEventListener("open", function() {
        if (!toolCache) {
          fetch("/api/tools/catalog").then(function(r) {
            return r.json();
          }).then(function(d) {
            toolCache = d;
            filterTools();
          }).catch(function() {
            sr.innerHTML = '<p class="text-base-content/30 text-center py-4">Could not load tools. Try again later.</p>';
          });
        }
      });
      si.addEventListener("input", function() {
        filterTools();
      });
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
//# sourceMappingURL=data:application/json;base64,ewogICJ2ZXJzaW9uIjogMywKICAic291cmNlcyI6IFsiLi4vLi4vc3JjL2pzL2FwcC5qcyJdLAogICJzb3VyY2VzQ29udGVudCI6IFsiLyogXHUyNTAwXHUyNTAwIFN0b3J5QnJhaW4gQUk6IGFwcC5qcyAoYmFzZS5qcyArIHVpLWluaXQuanMgYnVuZGxlZCkgXHUyNTAwXHUyNTAwICovXG4oZnVuY3Rpb24oKXsndXNlIHN0cmljdCc7dmFyIGh0bWw9ZG9jdW1lbnQuZG9jdW1lbnRFbGVtZW50O2Z1bmN0aW9uIHNldFRoZW1lKHQpe2h0bWwuc2V0QXR0cmlidXRlKCdkYXRhLXRoZW1lJyx0KTtsb2NhbFN0b3JhZ2Uuc2V0SXRlbSgnc2ItdGhlbWUnLHQpfVxuZG9jdW1lbnQucXVlcnlTZWxlY3RvckFsbCgnLnRoZW1lLXRvZ2dsZScpLmZvckVhY2goZnVuY3Rpb24oYil7Yi5hZGRFdmVudExpc3RlbmVyKCdjbGljaycsZnVuY3Rpb24oKXt2YXIgYz1odG1sLmdldEF0dHJpYnV0ZSgnZGF0YS10aGVtZScpfHwnbmlnaHQnO3NldFRoZW1lKGM9PT0nbmlnaHQnPydsaWdodCc6J25pZ2h0Jyl9KX0pXG53aW5kb3cubWF0Y2hNZWRpYSgnKHByZWZlcnMtY29sb3Itc2NoZW1lOiBkYXJrKScpLmFkZEV2ZW50TGlzdGVuZXIoJ2NoYW5nZScsZnVuY3Rpb24oZSl7aWYoIWxvY2FsU3RvcmFnZS5nZXRJdGVtKCdzYi10aGVtZScpKXtzZXRUaGVtZShlLm1hdGNoZXM/J25pZ2h0JzonbGlnaHQnKX19KVxudmFyIG5hdj1kb2N1bWVudC5nZXRFbGVtZW50QnlJZCgnc2l0ZU5hdmJhcicpLHNoPWRvY3VtZW50LmdldEVsZW1lbnRCeUlkKCdzaXRlSGVhZGVyJyk7ZnVuY3Rpb24gaFMoKXt2YXIgcz13aW5kb3cuc2Nyb2xsWT4yMDtpZihuYXYpbmF2LmNsYXNzTGlzdC50b2dnbGUoJ3NoYWRvdy1zbScscyk7aWYoc2gpc2guY2xhc3NMaXN0LnRvZ2dsZSgnc2Nyb2xsZWQnLHMpfVxud2luZG93LmFkZEV2ZW50TGlzdGVuZXIoJ3Njcm9sbCcsaFMse3Bhc3NpdmU6dHJ1ZX0pO2hTKClcblxuLyogXHUyNTAwXHUyNTAwIE5hdiBhY3RpdmUgc3RhdGUgZm9yIHRvb2wgcGFnZXMgXHUyNTAwXHUyNTAwICovXG5pZih3aW5kb3cubG9jYXRpb24ucGF0aG5hbWUuaW5kZXhPZignL3Rvb2wvJyk9PT0wKXtkb2N1bWVudC5xdWVyeVNlbGVjdG9yQWxsKCcubmF2LWxpbmsnKS5mb3JFYWNoKGZ1bmN0aW9uKGwpe2lmKGwuZ2V0QXR0cmlidXRlKCdocmVmJyk9PT0nL3Rvb2xzJylsLmNsYXNzTGlzdC5hZGQoJ2FjdGl2ZScpfSl9XG5cbi8qIFx1MjUwMFx1MjUwMCBUaWx0IGNhcmRzIFx1MjUwMFx1MjUwMCAqL1xuZG9jdW1lbnQucXVlcnlTZWxlY3RvckFsbCgnLnRpbHQtY2FyZFtkYXRhLXRpbHRdJykuZm9yRWFjaChmdW5jdGlvbihjKXtjLmFkZEV2ZW50TGlzdGVuZXIoJ21vdXNlbW92ZScsZnVuY3Rpb24oZSl7dmFyIHI9dGhpcy5nZXRCb3VuZGluZ0NsaWVudFJlY3QoKSx4PShlLmNsaWVudFgtci5sZWZ0KS9yLndpZHRoLTAuNSx5PShlLmNsaWVudFktci50b3ApL3IuaGVpZ2h0LTAuNTt0aGlzLnN0eWxlLnNldFByb3BlcnR5KCctLXRpbHQteCcsKC15KjEyKSsnZGVnJyk7dGhpcy5zdHlsZS5zZXRQcm9wZXJ0eSgnLS10aWx0LXknLCh4KjEyKSsnZGVnJyl9KTtjLmFkZEV2ZW50TGlzdGVuZXIoJ21vdXNlbGVhdmUnLGZ1bmN0aW9uKCl7dGhpcy5zdHlsZS5zZXRQcm9wZXJ0eSgnLS10aWx0LXgnLCcwZGVnJyk7dGhpcy5zdHlsZS5zZXRQcm9wZXJ0eSgnLS10aWx0LXknLCcwZGVnJyl9KX0pXG5cbi8qIFx1MjUwMFx1MjUwMCBCdXR0b24gcmlwcGxlIFx1MjUwMFx1MjUwMCAqL1xuZG9jdW1lbnQucXVlcnlTZWxlY3RvckFsbCgnLmJ0bi1yaXBwbGUnKS5mb3JFYWNoKGZ1bmN0aW9uKGIpe2IuYWRkRXZlbnRMaXN0ZW5lcignbW91c2Vkb3duJyxmdW5jdGlvbihlKXt2YXIgcj10aGlzLmdldEJvdW5kaW5nQ2xpZW50UmVjdCgpO3RoaXMuc3R5bGUuc2V0UHJvcGVydHkoJy0tcmlwcGxlLXgnLCgoZS5jbGllbnRYLXIubGVmdCkvci53aWR0aCoxMDApKyclJyk7dGhpcy5zdHlsZS5zZXRQcm9wZXJ0eSgnLS1yaXBwbGUteScsKChlLmNsaWVudFktci50b3ApL3IuaGVpZ2h0KjEwMCkrJyUnKX0pfSlcbnZhciBkaWE9ZG9jdW1lbnQuZ2V0RWxlbWVudEJ5SWQoJ3NlYXJjaERpYWxvZycpLHNpPWRvY3VtZW50LmdldEVsZW1lbnRCeUlkKCdzZWFyY2hJbnB1dCcpXG5mdW5jdGlvbiBvUygpe1xuICBpZighZGlhKXJldHVybjtcbiAgZGlhLnNob3dNb2RhbCgpO1xuICBpZihzaSlzaS5mb2N1cygpO1xuICAvLyBGZXRjaCB0b29sIGNhdGFsb2cgaWYgbm90IGFscmVhZHkgY2FjaGVkXG4gIGlmKCF0b29sQ2FjaGUpe1xuICAgIGZldGNoKCcvYXBpL3Rvb2xzL2NhdGFsb2cnKS50aGVuKGZ1bmN0aW9uKHIpe3JldHVybiByLmpzb24oKX0pLnRoZW4oZnVuY3Rpb24oZCl7dG9vbENhY2hlPWQ7ZmlsdGVyVG9vbHMoKX0pLmNhdGNoKGZ1bmN0aW9uKCl7aWYoc3Ipc3IuaW5uZXJIVE1MPSc8cCBjbGFzcz1cInRleHQtYmFzZS1jb250ZW50LzMwIHRleHQtY2VudGVyIHB5LTRcIj5Db3VsZCBub3QgbG9hZCB0b29scy4gVHJ5IGFnYWluIGxhdGVyLjwvcD4nfSlcbiAgfVxufVxuZnVuY3Rpb24gY1MoKXtpZihkaWEpZGlhLmNsb3NlKCl9XG5kb2N1bWVudC5xdWVyeVNlbGVjdG9yQWxsKCdbaWRePXNlYXJjaFRvZ2dsZV0nKS5mb3JFYWNoKGZ1bmN0aW9uKGIpe2IuYWRkRXZlbnRMaXN0ZW5lcignY2xpY2snLG9TKX0pXG52YXIgaHNpPWRvY3VtZW50LmdldEVsZW1lbnRCeUlkKCdoZXJvU2VhcmNoSW5wdXQnKTtpZihoc2kpe2hzaS5hZGRFdmVudExpc3RlbmVyKCdmb2N1cycsb1MpO2hzaS5hZGRFdmVudExpc3RlbmVyKCdjbGljaycsb1MpfVxudmFyIHNjPWRvY3VtZW50LmdldEVsZW1lbnRCeUlkKCdzZWFyY2hDbG9zZScpO2lmKHNjKXNjLmFkZEV2ZW50TGlzdGVuZXIoJ2NsaWNrJyxjUylcbmlmKGRpYSl7ZGlhLmFkZEV2ZW50TGlzdGVuZXIoJ2NsaWNrJyxmdW5jdGlvbihlKXtpZihlLnRhcmdldD09PWRpYSljUygpfSk7ZGlhLmFkZEV2ZW50TGlzdGVuZXIoJ2tleWRvd24nLGZ1bmN0aW9uKGUpe2lmKGUua2V5PT09J0VzY2FwZScpY1MoKX0pfVxudmFyIGViPWRvY3VtZW50LmdldEVsZW1lbnRCeUlkKCdleHBsb3JlVG9vbHNCdG4nKTtpZihlYil7ZWIuYWRkRXZlbnRMaXN0ZW5lcignY2xpY2snLGZ1bmN0aW9uKCl7dmFyIGQ9ZG9jdW1lbnQuZ2V0RWxlbWVudEJ5SWQoJ21vYmlsZURyYXdlcicpO2lmKGQpZC5jaGVja2VkPXRydWV9KX1cbmlmKCdzZXJ2aWNlV29ya2VyJ2luIG5hdmlnYXRvcil7dmFyIHN3UmVmcmVzaGluZz1mYWxzZTtuYXZpZ2F0b3Iuc2VydmljZVdvcmtlci5yZWdpc3RlcignL3N3LmpzJyx7c2NvcGU6Jy8nfSkudGhlbihmdW5jdGlvbihyZWcpe3JlZy5hZGRFdmVudExpc3RlbmVyKCd1cGRhdGVmb3VuZCcsZnVuY3Rpb24oKXt2YXIgdz1yZWcuaW5zdGFsbGluZztpZih3KXt3LmFkZEV2ZW50TGlzdGVuZXIoJ3N0YXRlY2hhbmdlJyxmdW5jdGlvbigpe2lmKHcuc3RhdGU9PT0naW5zdGFsbGVkJyYmbmF2aWdhdG9yLnNlcnZpY2VXb3JrZXIuY29udHJvbGxlcil7dmFyIG1zZz1kb2N1bWVudC5jcmVhdGVFbGVtZW50KCdkaXYnKTttc2cuY2xhc3NOYW1lPSdmaXhlZCBib3R0b20tNCByaWdodC00IHotNTAgZ2xhc3Mtc3Ryb25nIHJvdW5kZWQteGwgc2hhZG93LTJ4bCBib3JkZXIgYm9yZGVyLXByaW1hcnkvMjAgYW5pbWF0ZS1mYWRlLWluJzttc2cuc2V0QXR0cmlidXRlKCdyb2xlJywnYWxlcnQnKTt2YXIgYnRuPWRvY3VtZW50LmNyZWF0ZUVsZW1lbnQoJ2J1dHRvbicpO2J0bi5jbGFzc05hbWU9J2ZsZXggaXRlbXMtY2VudGVyIGdhcC0yIHB4LTQgcHktMyB0ZXh0LXNtIGZvbnQtYm9sZCBjdXJzb3ItcG9pbnRlciBmb2N1cy12aXNpYmxlOm91dGxpbmUtMiBmb2N1cy12aXNpYmxlOm91dGxpbmUtcHJpbWFyeSByb3VuZGVkLXhsJztidG4uaW5uZXJIVE1MPSdOZXcgdmVyc2lvbiBhdmFpbGFibGUhIDxzcGFuIGNsYXNzPVwidGV4dC1wcmltYXJ5IG1sLTFcIj5SZWZyZXNoPC9zcGFuPic7YnRuLmFkZEV2ZW50TGlzdGVuZXIoJ2NsaWNrJyxmdW5jdGlvbigpe3cucG9zdE1lc3NhZ2Uoe2FjdGlvbjonc2tpcFdhaXRpbmcnfSk7fSk7YnRuLmFkZEV2ZW50TGlzdGVuZXIoJ2tleWRvd24nLGZ1bmN0aW9uKGUpe2lmKGUua2V5PT09J0VudGVyJ3x8ZS5rZXk9PT0nICcpe2UucHJldmVudERlZmF1bHQoKTt3LnBvc3RNZXNzYWdlKHthY3Rpb246J3NraXBXYWl0aW5nJ30pfX0pO21zZy5hcHBlbmRDaGlsZChidG4pO2RvY3VtZW50LmJvZHkuYXBwZW5kQ2hpbGQobXNnKTtidG4uZm9jdXMoKTt9fSk7fX0pO30pLmNhdGNoKGZ1bmN0aW9uKCl7fSl9bmF2aWdhdG9yLnNlcnZpY2VXb3JrZXIuYWRkRXZlbnRMaXN0ZW5lcignY29udHJvbGxlcmNoYW5nZScsZnVuY3Rpb24oKXtpZihzd1JlZnJlc2hpbmcpcmV0dXJuO3N3UmVmcmVzaGluZz10cnVlO3dpbmRvdy5sb2NhdGlvbi5yZWxvYWQoKTt9KVxuXG4vKiBcdTI1MDBcdTI1MDAgRGlhbG9nICsgYWNjb3JkaW9uIFx1MjUwMFx1MjUwMCAqL1xuZG9jdW1lbnQuYWRkRXZlbnRMaXN0ZW5lcignY2xpY2snLGZ1bmN0aW9uKGUpe3ZhciB0PWUudGFyZ2V0LmNsb3Nlc3QoJ1tkYXRhLWRpYWxvZy10cmlnZ2VyXScpO2lmKHQpe3ZhciBpZD10LmRhdGFzZXQuZGlhbG9nVHJpZ2dlcixkbGc9ZG9jdW1lbnQuZ2V0RWxlbWVudEJ5SWQoaWQpO2lmKGRsZyl7aWYoZGxnLnRhZ05hbWU9PT0nRElBTE9HJylkbGcuc2hvd01vZGFsKCk7ZWxzZXtkbGcuY2xhc3NMaXN0LnJlbW92ZSgnaGlkZGVuJyk7ZGxnLmNsYXNzTGlzdC5hZGQoJ2ZsZXgnKTtkb2N1bWVudC5ib2R5LnN0eWxlLm92ZXJmbG93PSdoaWRkZW4nfX1yZXR1cm59XG52YXIgY2I9ZS50YXJnZXQuY2xvc2VzdCgnW2RhdGEtZGlhbG9nLWNsb3NlXScpO2lmKGNiKXtjRChjYi5kYXRhc2V0LmRpYWxvZ0Nsb3NlKTtyZXR1cm59XG52YXIgb3Y9ZS50YXJnZXQuY2xvc2VzdCgnW2RhdGEtZGlhbG9nLW92ZXJsYXldJyk7aWYob3Ype3ZhciBkMj1vdi5jbG9zZXN0KCdbZGF0YS1kaWFsb2ddJyk7aWYoZDIpY0QoZDIuaWQpfX0pXG5kb2N1bWVudC5hZGRFdmVudExpc3RlbmVyKCdrZXlkb3duJyxmdW5jdGlvbihlKXtpZihlLmtleT09PSdFc2NhcGUnKXtkb2N1bWVudC5xdWVyeVNlbGVjdG9yQWxsKCdbZGF0YS1kaWFsb2ddOm5vdCguaGlkZGVuKScpLmZvckVhY2goZnVuY3Rpb24oZCl7Y0QoZC5pZCl9KX19KVxuZnVuY3Rpb24gY0QoaWQpe3ZhciBkbGc9ZG9jdW1lbnQuZ2V0RWxlbWVudEJ5SWQoaWQpO2lmKGRsZyl7aWYoZGxnLnRhZ05hbWU9PT0nRElBTE9HJylkbGcuY2xvc2UoKTtlbHNle2RsZy5jbGFzc0xpc3QuYWRkKCdoaWRkZW4nKTtkbGcuY2xhc3NMaXN0LnJlbW92ZSgnZmxleCcpO2RvY3VtZW50LmJvZHkuc3R5bGUub3ZlcmZsb3c9Jyd9fX1cbmZ1bmN0aW9uIHRvZ2dsZUFjY29yZGlvbih0KXt2YXIgYWM9dC5jbG9zZXN0KCdbZGF0YS1hY2NvcmRpb25dJyk7aWYoIWFjKXJldHVybjt2YXIgaXQ9dC5jbG9zZXN0KCdbZGF0YS1hY2NvcmRpb24taXRlbV0nKSxpc09wZW49aXQ/aXQuZGF0YXNldC5vcGVuPT09J3RydWUnOmZhbHNlXG5pZihhYy5kYXRhc2V0LmFjY29yZGlvbiE9PSdtdWx0aScpe2FjLnF1ZXJ5U2VsZWN0b3JBbGwoJ1tkYXRhLWFjY29yZGlvbi1pdGVtXScpLmZvckVhY2goZnVuY3Rpb24oaSl7aS5kYXRhc2V0Lm9wZW49J2ZhbHNlJzt2YXIgYz1pLnF1ZXJ5U2VsZWN0b3IoJ1tkYXRhLWFjY29yZGlvbi1jb250ZW50XScpO2lmKGMpe2Muc3R5bGUuZGlzcGxheT0nbm9uZSc7Yy5zdHlsZS5tYXhIZWlnaHQ9JzAnfVxudmFyIGNoPWkucXVlcnlTZWxlY3RvcignW2RhdGEtYWNjb3JkaW9uLWNoZXZyb25dJyk7aWYoY2gpY2guY2xhc3NMaXN0LnJlbW92ZSgncm90YXRlLTE4MCcpO3ZhciB0cj1pLnF1ZXJ5U2VsZWN0b3IoJ1tkYXRhLWFjY29yZGlvbi10cmlnZ2VyXScpO2lmKHRyKXRyLnNldEF0dHJpYnV0ZSgnYXJpYS1leHBhbmRlZCcsJ2ZhbHNlJyl9KX1cbmlmKGl0KXt2YXIgbk89aXNPcGVuPydmYWxzZSc6J3RydWUnO2l0LmRhdGFzZXQub3Blbj1uTzt2YXIgYzI9aXQucXVlcnlTZWxlY3RvcignW2RhdGEtYWNjb3JkaW9uLWNvbnRlbnRdJyk7aWYoYzIpe2MyLnN0eWxlLmRpc3BsYXk9bk89PT0ndHJ1ZSc/J2Jsb2NrJzonbm9uZSc7YzIuc3R5bGUubWF4SGVpZ2h0PW5PPT09J3RydWUnP2MyLnNjcm9sbEhlaWdodCsncHgnOicwJ31cbnZhciBjaDI9aXQucXVlcnlTZWxlY3RvcignW2RhdGEtYWNjb3JkaW9uLWNoZXZyb25dJyk7aWYoY2gyKWNoMi5jbGFzc0xpc3QudG9nZ2xlKCdyb3RhdGUtMTgwJyxuTz09PSd0cnVlJyk7dC5zZXRBdHRyaWJ1dGUoJ2FyaWEtZXhwYW5kZWQnLG5PKX19XG5kb2N1bWVudC5hZGRFdmVudExpc3RlbmVyKCdjbGljaycsZnVuY3Rpb24oZSl7dmFyIHQ9ZS50YXJnZXQuY2xvc2VzdCgnW2RhdGEtYWNjb3JkaW9uLXRyaWdnZXJdJyk7aWYodCl7ZS5wcmV2ZW50RGVmYXVsdCgpO3RvZ2dsZUFjY29yZGlvbih0KX19KVxuZG9jdW1lbnQuYWRkRXZlbnRMaXN0ZW5lcigna2V5ZG93bicsZnVuY3Rpb24oZSl7aWYoZS5rZXkhPT0nRW50ZXInJiZlLmtleSE9PScgJylyZXR1cm47dmFyIHQ9ZS50YXJnZXQuY2xvc2VzdCgnW2RhdGEtYWNjb3JkaW9uLXRyaWdnZXJdJyk7aWYodCl7ZS5wcmV2ZW50RGVmYXVsdCgpO3RvZ2dsZUFjY29yZGlvbih0KX19KVxuZG9jdW1lbnQucXVlcnlTZWxlY3RvckFsbCgnW2RhdGEtYWNjb3JkaW9uLWl0ZW1dW2RhdGEtb3Blbj1cInRydWVcIl0nKS5mb3JFYWNoKGZ1bmN0aW9uKGl0KXt2YXIgYz1pdC5xdWVyeVNlbGVjdG9yKCdbZGF0YS1hY2NvcmRpb24tY29udGVudF0nKTtpZihjKXtjLnN0eWxlLmRpc3BsYXk9J2Jsb2NrJztjLnN0eWxlLm1heEhlaWdodD1jLnNjcm9sbEhlaWdodCsncHgnfVxudmFyIGNoPWl0LnF1ZXJ5U2VsZWN0b3IoJ1tkYXRhLWFjY29yZGlvbi1jaGV2cm9uXScpO2lmKGNoKWNoLmNsYXNzTGlzdC5hZGQoJ3JvdGF0ZS0xODAnKX0pXG5kb2N1bWVudC5xdWVyeVNlbGVjdG9yQWxsKCcuZHJvcGRvd24gYnV0dG9uW2FyaWEtaGFzcG9wdXA9XCJ0cnVlXCJdJykuZm9yRWFjaChmdW5jdGlvbihiKXtiLmFkZEV2ZW50TGlzdGVuZXIoJ2NsaWNrJyxmdW5jdGlvbigpe3ZhciBkPWIuY2xvc2VzdCgnLmRyb3Bkb3duJyksYz1kP2QucXVlcnlTZWxlY3RvcignLmRyb3Bkb3duLWNvbnRlbnQnKTpudWxsO2lmKGMpe3ZhciBvPWMuc3R5bGUuZGlzcGxheSE9PSdibG9jayc7Yy5zdHlsZS5kaXNwbGF5PW8/J2Jsb2NrJzonJztiLnNldEF0dHJpYnV0ZSgnYXJpYS1leHBhbmRlZCcsbyl9fSl9KVxuXG4vKiBcdTI1MDBcdTI1MDAgU2Nyb2xsIHJldmVhbCBJbnRlcnNlY3Rpb25PYnNlcnZlciBcdTI1MDBcdTI1MDAgKi9cbmlmKCdJbnRlcnNlY3Rpb25PYnNlcnZlcidpbiB3aW5kb3cpe3ZhciBybz1uZXcgSW50ZXJzZWN0aW9uT2JzZXJ2ZXIoZnVuY3Rpb24oZXMpe2VzLmZvckVhY2goZnVuY3Rpb24oZSl7aWYoZS5pc0ludGVyc2VjdGluZyl7ZS50YXJnZXQuY2xhc3NMaXN0LmFkZCgndmlzaWJsZScpO3JvLnVub2JzZXJ2ZShlLnRhcmdldCl9fSl9LHt0aHJlc2hvbGQ6MC4xfSlcbmRvY3VtZW50LnF1ZXJ5U2VsZWN0b3JBbGwoJy5yZXZlYWwnKS5mb3JFYWNoKGZ1bmN0aW9uKGVsKXtyby5vYnNlcnZlKGVsKX0pfVxuXG4vKiBcdTI1MDBcdTI1MDAgTGlnaHR3ZWlnaHQgYW5hbHl0aWNzIFx1MjUwMFx1MjUwMCAqL1xudmFyIGFuPWRvY3VtZW50LmdldEVsZW1lbnRCeUlkKCdhbmFseXRpY3MtdHJhY2snKTtpZihhbiYmJ3NlbmRCZWFjb24naW4gbmF2aWdhdG9yKXt2YXIgYj1uZXcgQmxvYihbSlNPTi5zdHJpbmdpZnkoe25hbWU6YW4uZGF0YXNldC50b29sfHwncGFnZScsY2F0ZWdvcnk6J3BhZ2Vfdmlldyd9KV0se3R5cGU6J2FwcGxpY2F0aW9uL2pzb24nfSk7bmF2aWdhdG9yLnNlbmRCZWFjb24oJy9hcGkvdHJhY2snLGIpfVxuXG4vKiBcdTI1MDBcdTI1MDAgU2VhcmNoIGRpYWxvZyBcdTI1MDBcdTI1MDAgKi9cbnZhciBzZD1kb2N1bWVudC5nZXRFbGVtZW50QnlJZCgnc2VhcmNoRGlhbG9nJyksc2k9ZG9jdW1lbnQuZ2V0RWxlbWVudEJ5SWQoJ3NlYXJjaElucHV0Jyksc3I9ZG9jdW1lbnQuZ2V0RWxlbWVudEJ5SWQoJ3NlYXJjaFJlc3VsdHMnKSx0b29sQ2FjaGU9bnVsbDtcbmlmKHNkJiZzaSYmc3Ipe3NkLmFkZEV2ZW50TGlzdGVuZXIoJ29wZW4nLGZ1bmN0aW9uKCl7aWYoIXRvb2xDYWNoZSl7ZmV0Y2goJy9hcGkvdG9vbHMvY2F0YWxvZycpLnRoZW4oZnVuY3Rpb24ocil7cmV0dXJuIHIuanNvbigpfSkudGhlbihmdW5jdGlvbihkKXt0b29sQ2FjaGU9ZDtmaWx0ZXJUb29scygpfSkuY2F0Y2goZnVuY3Rpb24oKXtzci5pbm5lckhUTUw9JzxwIGNsYXNzPVwidGV4dC1iYXNlLWNvbnRlbnQvMzAgdGV4dC1jZW50ZXIgcHktNFwiPkNvdWxkIG5vdCBsb2FkIHRvb2xzLiBUcnkgYWdhaW4gbGF0ZXIuPC9wPid9KX19KVxuc2kuYWRkRXZlbnRMaXN0ZW5lcignaW5wdXQnLGZ1bmN0aW9uKCl7ZmlsdGVyVG9vbHMoKX0pfVxuZnVuY3Rpb24gZmlsdGVyVG9vbHMoKXt2YXIgcT1zaS52YWx1ZS50cmltKCkudG9Mb3dlckNhc2UoKTtpZighdG9vbENhY2hlfHwhcSl7c3IuaW5uZXJIVE1MPSc8cCBjbGFzcz1cInRleHQtYmFzZS1jb250ZW50LzMwIHRleHQtY2VudGVyIHB5LTRcIj4nKyhxPydObyByZXN1bHRzIGZvdW5kJzonU3RhcnQgdHlwaW5nIHRvIGZpbmQgdG9vbHMnKSsnPC9wPic7cmV0dXJufVxudmFyIG09dG9vbENhY2hlLmZpbHRlcihmdW5jdGlvbih0KXtyZXR1cm4gdC5uYW1lLnRvTG93ZXJDYXNlKCkuaW5kZXhPZihxKT4tMXx8KHQuZGVzYyYmdC5kZXNjLnRvTG93ZXJDYXNlKCkuaW5kZXhPZihxKT4tMSl9KVxuaWYobS5sZW5ndGg9PT0wKXtzci5pbm5lckhUTUw9JzxwIGNsYXNzPVwidGV4dC1iYXNlLWNvbnRlbnQvMzAgdGV4dC1jZW50ZXIgcHktNFwiPk5vIHJlc3VsdHMgZm91bmQ8L3A+JztyZXR1cm59XG5zci5pbm5lckhUTUw9bS5zbGljZSgwLDIwKS5tYXAoZnVuY3Rpb24odCl7cmV0dXJuJzxhIGhyZWY9XCInK3QudXJsKydcIiBjbGFzcz1cImZsZXggaXRlbXMtY2VudGVyIGp1c3RpZnktYmV0d2VlbiBwLTMgcm91bmRlZC14bCBob3ZlcjpnbGFzcyB0cmFuc2l0aW9uLWFsbCBkdXJhdGlvbi0yMDBcIiBvbmNsaWNrPVwiZG9jdW1lbnQuZ2V0RWxlbWVudEJ5SWQoXFwnc2VhcmNoRGlhbG9nXFwnKS5jbG9zZSgpXCI+PGRpdj48ZGl2IGNsYXNzPVwiZm9udC1zZW1pYm9sZCB0ZXh0LXNtXCI+Jyt0Lm5hbWUrJzwvZGl2PjxkaXYgY2xhc3M9XCJ0ZXh0LXhzIHRleHQtYmFzZS1jb250ZW50LzQwXCI+Jyt0LmNhdGVnb3J5Kyc8L2Rpdj48L2Rpdj48c3ZnIGNsYXNzPVwidy00IGgtNCB0ZXh0LWJhc2UtY29udGVudC8yMFwiIHZpZXdCb3g9XCIwIDAgMjQgMjRcIiBmaWxsPVwibm9uZVwiIHN0cm9rZT1cImN1cnJlbnRDb2xvclwiIHN0cm9rZS13aWR0aD1cIjJcIj48cGF0aCBkPVwiTTUgMTJoMTRcIi8+PHBhdGggZD1cIm0xMiA1IDcgNy03IDdcIi8+PC9zdmc+PC9hPid9KS5qb2luKCcnKX1cblxuLyogXHUyNTAwXHUyNTAwIEhlcm8gbW91c2UtZm9sbG93IGdsb3cgXHUyNTAwXHUyNTAwICovXG52YXIgaHM9ZG9jdW1lbnQuZ2V0RWxlbWVudEJ5SWQoJ2hlcm9TZWN0aW9uJyk7aWYoaHMpe3ZhciBfcj1udWxsLF9yaWQ9ITE7aHMuYWRkRXZlbnRMaXN0ZW5lcignbW91c2Vtb3ZlJyxmdW5jdGlvbihlKXtpZihfcmlkKWNhbmNlbEFuaW1hdGlvbkZyYW1lKF9yKTtfcmlkPSEwO19yPXJlcXVlc3RBbmltYXRpb25GcmFtZShmdW5jdGlvbigpe3ZhciBiPWhzLmdldEJvdW5kaW5nQ2xpZW50UmVjdCgpLG14PShlLmNsaWVudFgtYi5sZWZ0KS9iLndpZHRoKjEwMCxteT0oZS5jbGllbnRZLWIudG9wKS9iLmhlaWdodCoxMDA7aHMuc3R5bGUuc2V0UHJvcGVydHkoJy0tbXgnLG14KyclJyk7aHMuc3R5bGUuc2V0UHJvcGVydHkoJy0tbXknLG15KyclJyk7X3JpZD0hMX0pfSx7cGFzc2l2ZTohMH0pfVxufSkoKTtcbiJdLAog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
