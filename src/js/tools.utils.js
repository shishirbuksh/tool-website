(function () {
  'use strict';

  /* SCHEMA localStorage keys: sb-theme ('light'|'night'), cookieConsent ('accepted'|'rejected'), sbr_tools_recent_search (JSON array) */
  const store={get(k){try{return localStorage.getItem(k)}catch{return null}},set(k,v){try{localStorage.setItem(k,v)}catch{}},del(k){try{localStorage.removeItem(k)}catch{}}};

  window.sbr = window.sbr || {};
  // Share safe storage wrapper; cookieConsent/sb-theme/sbr_tools_recent_search go through store.
  window.sbr.store = window.sbr.store || store;
  window.sbr.getConsent = function () { return store.get('cookieConsent'); };

  /* ── Clipboard ── */
  window.sbr.copyToClipboard = function (text, btnEl, successMsg) {
    if (!text) return;
    var fallback = function () {
      var ta = document.createElement('textarea');
      ta.value = text;
      ta.style.position = 'fixed'; ta.style.left = '-9999px'; ta.style.top = '-9999px';
      document.body.appendChild(ta);
      ta.select();
      try {
        document.execCommand('copy');
        if (btnEl) {
          var orig = btnEl.innerHTML;
          btnEl.innerHTML = (successMsg || 'Copied!');
          btnEl.disabled = true;
          setTimeout(function () {
            btnEl.innerHTML = orig;
            btnEl.disabled = false;
          }, 2000);
        }
      } catch (e) {
        console.warn('[sbr] Clipboard fallback also failed:', e);
      }
      document.body.removeChild(ta);
    };
    if (navigator.clipboard && navigator.clipboard.writeText) {
      navigator.clipboard.writeText(text).then(function () {
        if (!btnEl) return;
        var orig = btnEl.innerHTML;
        btnEl.innerHTML = (successMsg || 'Copied!');
        btnEl.disabled = true;
        setTimeout(function () {
          btnEl.innerHTML = orig;
          btnEl.disabled = false;
        }, 2000);
      })['catch'](function () {
        fallback();
      });
    } else {
      fallback();
    }
  };

  /* ── File size formatting ── */
  window.sbr.formatFileSize = function (bytes) {
    if (bytes < 1024) return bytes + ' B';
    if (bytes < 1048576) return (bytes / 1024).toFixed(1) + ' KB';
    if (bytes < 1073741824) return (bytes / 1048576).toFixed(2) + ' MB';
    return (bytes / 1073741824).toFixed(2) + ' GB';
  };

  /* ── Download data URL ── */
  window.sbr.downloadDataUrl = function (filename, dataUrl) {
    var link = document.createElement('a');
    link.download = filename;
    link.href = dataUrl;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
  };

  /* ── Download canvas as image ── */
  window.sbr.downloadCanvas = function (canvasId, filename) {
    var canvas = document.getElementById(canvasId);
    if (!canvas) {
      canvas = document.querySelector('#' + canvasId.replace('#', '') + ' canvas');
    }
    if (!canvas) return;
    window.sbr.downloadDataUrl(filename, canvas.toDataURL('image/png'));
  };

  /* ── Loader show/hide ── */
  window.sbr.showLoader = function (id) {
    var el = document.getElementById(id);
    if (el) {
      el.classList.remove('hidden');
      el.setAttribute('aria-hidden', 'false');
      document.body.setAttribute('aria-busy', 'true');
    }
  };
  window.sbr.hideLoader = function (id) {
    var el = document.getElementById(id);
    if (el) {
      el.classList.add('hidden');
      el.setAttribute('aria-hidden', 'true');
      document.body.removeAttribute('aria-busy');
    }
  };

  /* ── Sanitize HTML (basic XSS prevention) ── */
  window.sbr.sanitizeHtml = function (str) {
    var d = document.createElement('div');
    d.textContent = str;
    return d.innerHTML;
  };

  /* ── Format currency (locale-aware) ──
     Signature compatibility: the second argument is either a maximum
     fraction-digit count (new callers) or an ISO currency code (legacy
     callers). The active page locale decides grouping/decimal separators;
     the page currency decides the symbol. This keeps deferred loading from
     overwriting base.html's locale-aware formatter with a USD/en-US one. */
  window.sbr.formatCurrency = function (value, arg) {
    var localeMap = { hi: 'en-IN', es: 'es-ES', fr: 'fr-FR', de: 'de-DE', en: 'en-US' };
    var target = localeMap[window.sbr.locale] || 'en-US';
    var currency = window.sbr.currency || 'USD';
    var maxFrac = 0;
    if (typeof arg === 'string') {
      currency = arg;
    } else if (typeof arg === 'number') {
      maxFrac = arg;
    }
    var num = Number(value);
    if (!isFinite(num)) num = 0;
    try {
      return new Intl.NumberFormat(target, {
        style: 'currency',
        currency: currency,
        maximumFractionDigits: maxFrac
      }).format(num);
    } catch (e) {
      var symbol = window.sbr.currencySymbol || '$';
      return symbol + num.toFixed(maxFrac);
    }
  };

  /* ── Debounce ── */
  window.sbr.debounce = function (fn, ms) {
    var timer = null;
    return function () {
      var ctx = this, args = arguments;
      clearTimeout(timer);
      timer = setTimeout(function () { fn.apply(ctx, args); }, ms);
    };
  };

  /* ── Global error handler ── */
  window.sbr.initErrorHandler = function () {
    window.onerror = function (msg, url, line, col, err) {
      console.error('[sbr] Uncaught error:', msg, 'at', url, line + ':' + col);
      // Return false so the error still propagates to the browser console /
      // reporting hooks — never silently swallow uncaught errors.
      return false;
    };
    window.addEventListener('unhandledrejection', function (e) {
      console.error('[sbr] Unhandled promise rejection:', e.reason);
    });
  };
  window.sbr.initErrorHandler();

  /* ── Delegate: copy-to-clipboard buttons ── */
  document.addEventListener('click', function (e) {
    var btn = e.target.closest('[data-copy-target]');
    if (btn) {
      var targetId = btn.getAttribute('data-copy-target');
      var targetEl = document.getElementById(targetId);
      if (targetEl) {
        var text = targetEl.textContent;
        window.sbr.copyToClipboard(text, btn);
      }
    }
  });

  /* ── Lucide icon renderer (for JS templates) ── */
  var __lucideIcons = {
    "check": '<path d="M20 6 9 17l-5-5" />',
    "copy": '<rect width="14" height="14" x="8" y="8" rx="2" ry="2" /><path d="M4 16c-1.1 0-2-.9-2-2V4c0-1.1.9-2 2-2h10c1.1 0 2 .9 2 2" />',
    "check-circle-2": '<circle cx="12" cy="12" r="10" /><path d="m9 12 2 2 4-4" />',
    "layers": '<path d="M12.83 2.18a2 2 0 0 0-1.66 0L2.6 6.08a1 1 0 0 0 0 1.83l8.58 3.91a2 2 0 0 0 1.66 0l8.58-3.9a1 1 0 0 0 0-1.83z" /><path d="M2 12a1 1 0 0 0 .58.91l8.6 3.91a2 2 0 0 0 1.65 0l8.58-3.9A1 1 0 0 0 22 12" /><path d="M2 17a1 1 0 0 0 .58.91l8.6 3.91a2 2 0 0 0 1.65 0l8.58-3.9A1 1 0 0 0 22 17" />',
    "boxes": '<path d="M2.97 12.92A2 2 0 0 0 2 14.63v3.24a2 2 0 0 0 .97 1.71l3 1.8a2 2 0 0 0 2.06 0L12 19v-5.5l-5-3-4.03 2.42Z" /><path d="m7 16.5-4.74-2.85" /><path d="m7 16.5 5-3" /><path d="M7 16.5v5.17" /><path d="M12 13.5V19l3.97 2.38a2 2 0 0 0 2.06 0l3-1.8a2 2 0 0 0 .97-1.71v-3.24a2 2 0 0 0-.97-1.71L17 10.5l-5 3Z" /><path d="m17 16.5-5-3" /><path d="m17 16.5 4.74-2.85" /><path d="M17 16.5v5.17" /><path d="M7.97 4.42A2 2 0 0 0 7 6.13v4.37l5 3 5-3V6.13a2 2 0 0 0-.97-1.71l-3-1.8a2 2 0 0 0-2.06 0l-3 1.8Z" /><path d="M12 8 7.26 5.15" /><path d="m12 8 4.74-2.85" /><path d="M12 13.5V8" />',
    "zap": '<path d="M4 14a1 1 0 0 1-.78-1.63l9.9-10.2a.5.5 0 0 1 .86.46l-1.92 6.02A1 1 0 0 0 13 10h7a1 1 0 0 1 .78 1.63l-9.9 10.2a.5.5 0 0 1-.86-.46l1.92-6.02A1 1 0 0 0 11 14z" />',
    "scroll": '<path d="M19 17V5a2 2 0 0 0-2-2H4" /><path d="M8 21h12a2 2 0 0 0 2-2v-1a1 1 0 0 0-1-1H11a1 1 0 0 0-1 1v1a2 2 0 1 1-4 0V5a2 2 0 1 0-4 0v2a1 1 0 0 0 1 1h3" />',
    "git-merge": '<circle cx="18" cy="18" r="3" /><circle cx="6" cy="6" r="3" /><path d="M6 21V9a9 9 0 0 0 9 9" />',
    "shield": '<path d="M20 13c0 5-3.5 7.5-7.66 8.95a1 1 0 0 1-.67-.01C7.5 20.5 4 18 4 13V6a1 1 0 0 1 1-1c2 0 4.5-1.2 6.24-2.72a1.17 1.17 0 0 1 1.52 0C14.51 3.81 17 5 19 5a1 1 0 0 1 1 1z" />'
  };
  window.__lucide = function (name, size) {
    size = size || 24;
    var inner = __lucideIcons[name];
    if (!inner) return '';
    return '<svg class="lucide lucide-' + name + '" xmlns="http://www.w3.org/2000/svg" width="' + size + '" height="' + size + '" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">' + inner + '</svg>';
  };

  /* ── Delegate: loading buttons (restores original label after 10s failsafe) ── */
  document.addEventListener('click', function (e) {
    var btn = e.target.closest('[data-loading]');
    if (btn && btn.getAttribute('data-loading')) {
      if (btn.dataset.loadingActive === 'true') return;
      btn.dataset.loadingActive = 'true';
      if (btn.dataset.origHtml === undefined) btn.dataset.origHtml = btn.innerHTML;
      btn.innerHTML = 'Processing...';
      btn.disabled = true;
      // Failsafe: restore original label if no explicit reset happens
      // (e.g. fetch never resolves). Cleared early by resetLoadingButton().
      btn.dataset.loadingTimer = String(setTimeout(function () {
        window.sbr.resetLoadingButton(btn);
      }, 10000));
    }
  });
  window.sbr.resetLoadingButton = function (btn) {
    if (!btn) return;
    if (btn.dataset.loadingTimer) clearTimeout(Number(btn.dataset.loadingTimer));
    if (btn.dataset.origHtml !== undefined) btn.innerHTML = btn.dataset.origHtml;
    btn.disabled = false;
    delete btn.dataset.loadingActive;
  };

  /* ── Unified SEO audit helpers (single source: density 0.5–2.5%, LSI + long-tail) ──
     Unifies page-grader (1–3%) vs seo-writing-assistant (0.5–2.5%) conflict.
     Canonical ideal: 0.5–2.5% primary, entity 4–7/para. Used by
     keyword-data-analyzer, seo-writing-assistant, word-counter, page-grader. */
  window.sbr.audit = (function () {
    var IDEAL_MIN = 0.5, IDEAL_MAX = 2.5;
    function words(text) {
      var m = String(text || '').toLowerCase().match(/[a-z0-9\u00C0-\u024F\u1E00-\u1EFF\u0900-\u097F']+/g);
      return m || [];
    }
    function keywordDensity(text, keyword) {
      var toks = words(text);
      if (!toks.length || !keyword) return { count: 0, total: toks.length, density: 0 };
      var kw = String(keyword).toLowerCase().trim().split(/\s+/);
      var count = 0;
      for (var i = 0; i <= toks.length - kw.length; i++) {
        var hit = true;
        for (var j = 0; j < kw.length; j++) {
          if (toks[i + j] !== kw[j]) { hit = false; break; }
        }
        if (hit) count++;
      }
      return { count: count, total: toks.length, density: toks.length ? (count * kw.length / toks.length * 100) : 0 };
    }
    function densityStatus(d) {
      if (d < IDEAL_MIN) return { level: 'low', msg: 'Below 0.5% — add 1–2 natural mentions.' };
      if (d <= IDEAL_MAX) return { level: 'optimal', msg: 'Optimal 0.5–2.5%.' };
      if (d <= 3.5) return { level: 'high', msg: 'Above 2.5% — dilute with synonyms.' };
      return { level: 'stuffed', msg: 'Stuffing risk >3.5% — rewrite with entities.' };
    }
    function longTailExpand(seed) {
      seed = String(seed || '').trim().replace(/\s+/g, ' ');
      if (!seed) return [];
      return [
        'how to ' + seed + ' online free',
        'best ' + seed + ' guide 2026',
        seed + ' vs alternative comparison',
        seed + ' for beginners step by step',
        'free ' + seed + ' tool no signup',
        seed + ' india price calculator hindi',
        'what is ' + seed + ' and how it works',
        seed + ' common mistakes to avoid'
      ];
    }
    /* Lazy bridge to /static/data/thesaurus.json ({word: {mode: [syns]}} or
       {word: [syns]}). Fire-and-forget: sync fallback above keeps tools
       working offline; later calls pick up real synonyms once loaded. */
    function loadThesaurus() {
      if (window.__THESAURUS || window.__THESAURUS_LOADING) return;
      window.__THESAURUS_LOADING = true;
      try {
        fetch('/static/data/thesaurus.json', { credentials: 'same-origin' }).then(function (r) {
          if (!r.ok) throw new Error('thesaurus ' + r.status);
          return r.json();
        }).then(function (d) {
          var flat = {};
          Object.keys(d || {}).forEach(function (k) {
            var v = d[k];
            var arr = Array.isArray(v) ? v : Object.keys(v || {}).reduce(function (a, m) {
              return a.concat(v[m]);
            }, []);
            flat[String(k).toLowerCase()] = arr;
          });
          window.__THESAURUS = flat;
        }).catch(function () {
          window.__THESAURUS = {};
        });
      } catch (e) {
        window.__THESAURUS = {};
      }
    }
    window.sbr.loadThesaurus = loadThesaurus;
    function lsiSuggest(seed) {
      seed = String(seed || '').trim().toLowerCase();
      if (!seed) return [];
      loadThesaurus();
      var base = seed.split(/\s+/).slice(0, 3).join(' ');
      var out = ['guide', 'calculator', 'tool', 'free', 'online', '2026', 'how it works', 'examples', 'formula', 'comparison'];
      var res = [];
      for (var i = 0; i < out.length; i++) {
        var c = (base + ' ' + out[i]).trim();
        if (c !== seed) res.push(c);
      }
      try {
        var entry = window.__THESAURUS && window.__THESAURUS[seed];
        var syns = Array.isArray(entry) ? entry : (entry ? Object.keys(entry).reduce(function (a, m) {
          return a.concat(entry[m]);
        }, []) : []);
        if (syns.length) {
          res = syns.slice(0, 8).concat(res).slice(0, 10);
        }
      } catch (e) {}
      return res.slice(0, 10);
    }
    function auditText(text, keywords) {
      var rows = [];
      (keywords || []).forEach(function (kw) {
        if (!kw) return;
        var r = keywordDensity(text, kw);
        var st = densityStatus(r.density);
        rows.push({ keyword: kw, count: r.count, total: r.total, density: Math.round(r.density * 100) / 100, status: st.level, message: st.msg });
      });
      return rows;
    }
    return { IDEAL_MIN: IDEAL_MIN, IDEAL_MAX: IDEAL_MAX, words: words, keywordDensity: keywordDensity, densityStatus: densityStatus, longTailExpand: longTailExpand, lsiSuggest: lsiSuggest, auditText: auditText };
  })();
})();
